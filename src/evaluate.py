"""
Evaluate a fine-tuned checkpoint on the test set, with a per-language
breakdown (this is the key diagnostic for cross-lingual generalization:
a model that is strong on English but weak on Hindi/Arabic reveals
transfer gaps that overall accuracy alone would hide).

Usage:
    python -m src.evaluate --checkpoint models/xlmr-fakenews
"""

import argparse
import os
import pandas as pd
import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
)
from transformers import AutoTokenizer
from .model import load_model

from . import config


@torch.no_grad()
def predict(texts, tokenizer, model, device, batch_size=32):
    model.eval()
    all_preds, all_probs = [], []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        enc = tokenizer(
            batch, truncation=True, padding=True,
            max_length=config.MAX_SEQ_LENGTH, return_tensors="pt",
        ).to(device)
        logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1)
        preds = torch.argmax(probs, dim=-1)
        all_preds.extend(preds.cpu().tolist())
        all_probs.extend(probs.cpu().tolist())
    return all_preds, all_probs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default=config.MODEL_OUTPUT_DIR)
    parser.add_argument("--test-csv", default=os.path.join(config.PROCESSED_DIR, "test.csv"))
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, fix_mistral_regex=True)
    except TypeError:
        tokenizer = AutoTokenizer.from_pretrained(args.checkpoint)
    model = load_model(pretrained_path=args.checkpoint).to(device)

    df = pd.read_csv(args.test_csv)
    preds, probs = predict(df["text"].tolist(), tokenizer, model, device)
    df["pred"] = preds
    df["pred_label"] = df["pred"].map(config.ID2LABEL)
    df["confidence"] = [max(p) for p in probs]

    print("\n=== Overall metrics ===")
    print(f"Accuracy : {accuracy_score(df['label_id'], df['pred']):.4f}")
    print(f"F1 (macro): {f1_score(df['label_id'], df['pred'], average='macro'):.4f}")
    print(f"Precision : {precision_score(df['label_id'], df['pred'], average='macro'):.4f}")
    print(f"Recall    : {recall_score(df['label_id'], df['pred'], average='macro'):.4f}")
    print("\nConfusion matrix (rows=true, cols=pred, order=[real, fake]):")
    print(confusion_matrix(df["label_id"], df["pred"]))
    print("\n" + classification_report(df["label_id"], df["pred"], target_names=["real", "fake"]))

    print("\n=== Per-language breakdown ===")
    rows = []
    for lang, g in df.groupby("language"):
        rows.append({
            "language": lang,
            "n": len(g),
            "accuracy": accuracy_score(g["label_id"], g["pred"]),
            "f1_macro": f1_score(g["label_id"], g["pred"], average="macro"),
        })
    lang_report = pd.DataFrame(rows).sort_values("accuracy")
    print(lang_report.to_string(index=False))

    os.makedirs(config.BASELINE_OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(config.BASELINE_OUTPUT_DIR, "per_language_metrics.csv")
    lang_report.to_csv(out_path, index=False)
    print(f"\nSaved per-language metrics to {out_path}")


if __name__ == "__main__":
    main()
