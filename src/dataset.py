"""
Data loading, cleaning, and splitting for cross-lingual fake news detection.

Expects a CSV with columns: text, label, language
  - text     : the news headline/article/snippet
  - label    : "real" or "fake"
  - language : ISO 639-1 code, e.g. "en", "es", "fr", "hi", "ar", "de", "pt"

To plug in a real dataset, either:
  1. Reformat it to this schema and point config.RAW_DATA_PATH at it, or
  2. Combine multiple public datasets with scripts/merge_datasets.py (see README)
     -- e.g. FakeNewsNet (en), LIAR (en), IFND (hi), AFND (ar), FakeCovid (multi),
        MM-COVID (multi), Constraint@AAAI2021 (en/hi).
"""

import os
import pandas as pd
from sklearn.model_selection import train_test_split

from . import config

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Rename columns flexibly
    df.columns = df.columns.astype(str).str.lower().str.strip()
    
    # Resolve text column from common variations or combinations
    if "text" not in df.columns:
        if "news headline" in df.columns and "news original text" in df.columns:
            h = df["news headline"].fillna("").astype(str).str.strip()
            b = df["news original text"].fillna("").astype(str).str.strip()
            # Combine headline and text when both present, otherwise fallback
            combined = h + " - " + b
            df["text"] = combined.str.strip(" -")
            df["text"] = df["text"].replace("", pd.NA)
            # Fill any remaining empty from individual columns
            df["text"] = df["text"].fillna(b).fillna(h)
        else:
            text_candidates = [
                "news original text",
                "news_original_text",
                "original text",
                "news headline",
                "news_headline",
                "headline",
                "title",
                "content",
                "article",
                "news",
                "english translated version",
                "english translation",
                "translated_text",
                "statement",
                "claim",
            ]
            for col in text_candidates:
                if col in df.columns:
                    df["text"] = df[col]
                    break

    # If no label column is found, attempt common variants
    if "label" not in df.columns:
        for col in ["class", "category", "target", "verdict", "ground_truth", "status"]:
            if col in df.columns:
                df = df.rename(columns={col: "label"})
                break
                
    if "language" not in df.columns:
        df["language"] = "en"
        
    required = {"text", "label", "language"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}. Found: {df.columns.tolist()}")

    df = df.dropna(subset=["text", "label", "language"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0]

    # Map labels safely
    def map_label(lbl):
        if pd.isna(lbl):
            return -1
        if isinstance(lbl, (int, float)):
            val = int(lbl)
            if val in (0, 1):
                return val
            return -1
        if isinstance(lbl, str):
            lbl_clean = lbl.lower().strip()
            if lbl_clean in ["real", "true", "t", "0", "0.0", "genuine", "authentic", "reliable", "accurate"]:
                return config.LABEL2ID["real"]
            if lbl_clean in ["fake", "false", "f", "1", "1.0", "misinformation", "rumor", "unreliable", "bogus"]:
                return config.LABEL2ID["fake"]
        return -1

    df["label_id"] = df["label"].apply(map_label)
    df = df[df["label_id"] != -1]
    
    df["language"] = df["language"].astype(str).str.lower().str.strip()
    df = df.drop_duplicates(subset=["text", "language"]).reset_index(drop=True)
    return df

def load_excel_dataset(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    return process_dataframe(df)

def load_xfact_dataset(path: str = None) -> pd.DataFrame:
    path = path or config.XFACT_PATH
    df = pd.read_csv(
        path,
        sep="\t",
        usecols=["language", "claim", "label"],
        dtype=str,
        encoding="utf-8",
        keep_default_na=False,
    ).rename(columns={"claim": "text"})
    return process_dataframe(df)

def load_raw_dataframe(path: str = None) -> pd.DataFrame:
    path = path or config.RAW_DATA_PATH
    df = pd.read_csv(path)
    return process_dataframe(df)

def make_splits():
    """
    Load predefined splits: 80.xlsx for train/val, 20.xlsx for test.
    """
    train_path = os.path.join(config.DATA_DIR, "raw", "80.xlsx")
    test_path = os.path.join(config.DATA_DIR, "raw", "20.xlsx")
    
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        print(f"Warning: {train_path} or {test_path} not found, falling back to config.RAW_DATA_PATH")
        df = load_raw_dataframe()
        return make_splits_from_df(df)
        
    print(f"Loading train/val split from {train_path}...")
    train_val_df = load_excel_dataset(train_path)

    if config.USE_XFACT and os.path.exists(config.XFACT_PATH):
        print(f"Loading X-FACT training data from {config.XFACT_PATH}...")
        xfact_df = load_xfact_dataset()
        train_val_df = pd.concat([train_val_df, xfact_df], ignore_index=True)
        train_val_df = train_val_df.drop_duplicates(
            subset=["text", "language"]
        ).reset_index(drop=True)
        print(f"Added {len(xfact_df):,} binary-labeled X-FACT examples.")
    
    print(f"Loading test split from {test_path}...")
    test_df = load_excel_dataset(test_path)
    
    # Split train_val into train and val
    train_df, val_df = train_test_split(
        train_val_df,
        test_size=config.VAL_SIZE,
        stratify=train_val_df["label_id"],
        random_state=config.SEED,
    )
    
    return {
        "train": train_df.reset_index(drop=True),
        "val": val_df.reset_index(drop=True),
        "test": test_df.reset_index(drop=True),
    }

def make_splits_from_df(df: pd.DataFrame):
    """Fallback if excel files are not present."""
    train_val_df, test_df = train_test_split(
        df, test_size=config.TEST_SIZE, stratify=df["label_id"], random_state=config.SEED
    )
    train_df, val_df = train_test_split(
        train_val_df, test_size=config.VAL_SIZE, stratify=train_val_df["label_id"], random_state=config.SEED
    )
    return {
        "train": train_df.reset_index(drop=True),
        "val": val_df.reset_index(drop=True),
        "test": test_df.reset_index(drop=True),
    }

def save_splits(splits: dict, out_dir: str = None):
    out_dir = out_dir or config.PROCESSED_DIR
    os.makedirs(out_dir, exist_ok=True)
    for name, split_df in splits.items():
        if len(split_df):
            split_df.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False)
    return out_dir

def build_hf_datasets(splits: dict):
    from datasets import Dataset, DatasetDict
    dd = {}
    for name, split_df in splits.items():
        if len(split_df) == 0:
            continue
        dd[name] = Dataset.from_pandas(
            split_df[["text", "label_id", "language"]].rename(columns={"label_id": "labels"}),
            preserve_index=False,
        )
    return DatasetDict(dd)

if __name__ == "__main__":
    splits = make_splits()
    save_splits(splits)
    for name, split_df in splits.items():
        print(f"{name}: {len(split_df)} rows")

