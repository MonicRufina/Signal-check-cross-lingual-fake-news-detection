"""Convert the local datasets into one training CSV.

X-FACT's ``train.all.tsv`` uses ``claim`` and graded truth labels. The Excel
files use translated article text and binary labels. Ambiguous X-FACT labels
are excluded because the model expects binary labels: ``real`` and ``fake``.

Run from the project root:
  python data/prepare_data.py
"""

import os

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
XFACT_PATH = os.path.join(RAW_DIR, "train.all.tsv")
SAMPLE_PATH = os.path.join(RAW_DIR, "sample_multilingual_fakenews.csv")
OUTPUT_PATH = os.path.join(RAW_DIR, "merged_fakenews.csv")
EXCEL_FILES = [
  ("Real.xlsx", "real"),
  ("Fake.xlsx", "fake"),
  ("80.xlsx", None),
  ("20.xlsx", None),
]

LANGUAGE_MAP = {
  "arabic": "ar", "armenian": "hy", "azerbaijani": "az",
  "bulgarian": "bg", "czech": "cs", "english": "en",
  "finnish": "fi", "french": "fr", "georgian": "ka",
  "german": "de", "hungarian": "hu", "italian": "it",
  "lithuanian": "lt", "romanian": "ro", "russian": "ru",
  "slovak": "sk", "spanish": "es", "swedish": "sv",
}


# Ambiguous X-FACT labels are deliberately excluded instead of forcing them
# into the wrong binary class.
LABEL_MAP = {
  "true": "real",
  "false": "fake",
}


def convert_xfact(path: str) -> pd.DataFrame:
  df = pd.read_csv(
    path,
    sep="\t",
    usecols=["language", "claim", "label"],
    dtype=str,
    encoding="utf-8",
    keep_default_na=False,
  )
  df = df.rename(columns={"claim": "text"})
  df["label"] = df["label"].str.lower().str.strip().map(LABEL_MAP)
  df["language"] = df["language"].str.lower().str.strip()
  df["text"] = df["text"].str.strip()
  df = df.dropna(subset=["label"])
  df = df[df["text"].str.len() > 0]
  return df[["text", "label", "language"]]


def convert_excel(path: str, default_label: str | None) -> pd.DataFrame:
  df = pd.read_excel(path)
  df.columns = [str(column).lower().strip() for column in df.columns]
  text_columns = ["english translated version", "news original text", "news headline"]
  text = pd.Series("", index=df.index, dtype="string")
  for column in text_columns:
    if column in df.columns:
      text = text.mask(text.str.strip().eq(""), df[column].fillna(""))

  label = df["label"] if "label" in df.columns else pd.Series(default_label, index=df.index)
  language = df["language"].astype("string").str.lower().str.strip()
  result = pd.DataFrame({"text": text, "label": label, "language": language})
  result["label"] = result["label"].astype("string").str.lower().str.strip()
  result["label"] = result["label"].replace({"true": "real", "false": "fake"})
  result["label"] = result["label"].where(result["label"].isin(["real", "fake"]), default_label)
  result["language"] = result["language"].map(LANGUAGE_MAP).fillna(result["language"])
  result["text"] = result["text"].astype("string").str.strip()
  result = result.dropna(subset=["text", "label", "language"])
  return result[result["text"].str.len() > 0][["text", "label", "language"]]


def main():
  sample = pd.read_csv(SAMPLE_PATH, usecols=["text", "label", "language"])
  frames = [sample, convert_xfact(XFACT_PATH)]
  for filename, default_label in EXCEL_FILES:
    path = os.path.join(RAW_DIR, filename)
    if os.path.exists(path):
      frames.append(convert_excel(path, default_label))

  merged = pd.concat(frames, ignore_index=True)
  merged = merged.dropna(subset=["text", "label", "language"])
  merged["label"] = merged["label"].str.lower().str.strip()
  merged["language"] = merged["language"].str.lower().str.strip()
  merged["text"] = merged["text"].astype(str).str.strip()
  merged = merged[merged["label"].isin(["real", "fake"])]
  merged = merged.drop_duplicates(subset=["text", "language"])
  merged.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

  print(f"Saved {len(merged):,} rows to {OUTPUT_PATH}")
  print("Labels:")
  print(merged["label"].value_counts().to_string())
  print("Languages:")
  print(merged["language"].value_counts().to_string())


if __name__ == "__main__":
  main()
