"""
Classical, fully-offline baseline: character n-gram TF-IDF + Logistic
Regression. Character n-grams are language-agnostic (they work directly on
sub-word patterns), so this baseline needs no pretrained multilingual
embeddings or internet access, and it runs in seconds on CPU.

Its purpose in this project:
  1. Sanity-check the data pipeline (splits, labels, cross-lingual grouping)
     end-to-end without waiting on a transformer fine-tune.
  2. Provide a reference number the XLM-RoBERTa deep-learning model
     (src/train.py) should clearly beat -- if it doesn't, something is
     wrong with the fine-tuning setup, not the task itself.

Usage:
    python -m src.baseline
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    confusion_matrix, classification_report,
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from . import config
from .dataset import load_raw_dataframe, make_splits, save_splits


def main():
    df = load_raw_dataframe()
    splits = make_splits()
    save_splits(splits)

    train_df, val_df, test_df = splits["train"], splits["val"], splits["test"]
    # Fold val into train for this lightweight baseline (no early stopping needed)
    train_full = pd.concat([train_df, val_df], ignore_index=True)

    print(f"Train: {len(train_full)} | Test: {len(test_df)}")
    print("Languages in train:", sorted(train_full["language"].unique()))
    print("Languages in test :", sorted(test_df["language"].unique()))

    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 5),
        max_features=20000,
        sublinear_tf=True,
    )
    X_train = vectorizer.fit_transform(train_full["text"])
    X_test = vectorizer.transform(test_df["text"])
    y_train = train_full["label_id"].values
    y_test = test_df["label_id"].values

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=5.0)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    probs = clf.predict_proba(X_test)

    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="macro")
    prec = precision_score(y_test, preds, average="macro")
    rec = recall_score(y_test, preds, average="macro")

    print("\n=== Overall test metrics (char-ngram TF-IDF + LogisticRegression) ===")
    print(f"Accuracy : {acc:.4f}")
    print(f"F1 (macro): {f1:.4f}")
    print(f"Precision : {prec:.4f}")
    print(f"Recall    : {rec:.4f}")
    print()
    print(classification_report(y_test, preds, target_names=["real", "fake"]))

    cm = confusion_matrix(y_test, preds)
    print("Confusion matrix (rows=true, cols=pred, order=[real, fake]):")
    print(cm)

    # Per-language breakdown
    test_df = test_df.copy()
    test_df["pred"] = preds
    test_df["confidence"] = probs.max(axis=1)

    rows = []
    for lang, g in test_df.groupby("language"):
        rows.append({
            "language": lang,
            "n": len(g),
            "accuracy": accuracy_score(g["label_id"], g["pred"]),
            "f1_macro": f1_score(g["label_id"], g["pred"], average="macro") if g["label_id"].nunique() > 1 else float("nan"),
        })
    lang_report = pd.DataFrame(rows).sort_values("accuracy")
    print("\n=== Per-language breakdown ===")
    print(lang_report.to_string(index=False))

    os.makedirs(config.BASELINE_OUTPUT_DIR, exist_ok=True)

    # Save metrics JSON
    metrics = {
        "accuracy": acc, "f1_macro": f1, "precision_macro": prec, "recall_macro": rec,
        "n_train": len(train_full), "n_test": len(test_df),
        "languages": sorted(df["language"].unique().tolist()),
    }
    with open(os.path.join(config.BASELINE_OUTPUT_DIR, "baseline_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    lang_report.to_csv(os.path.join(config.BASELINE_OUTPUT_DIR, "baseline_per_language_metrics.csv"), index=False)
    test_df.to_csv(os.path.join(config.BASELINE_OUTPUT_DIR, "baseline_test_predictions.csv"), index=False)

    # Confusion matrix plot
    plt.figure(figsize=(4.5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["real", "fake"], yticklabels=["real", "fake"])
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title("Baseline Confusion Matrix")
    plt.tight_layout()
    plt.savefig(os.path.join(config.BASELINE_OUTPUT_DIR, "confusion_matrix.png"), dpi=150)
    plt.close()

    # Per-language accuracy bar chart
    plt.figure(figsize=(7, 4))
    sns.barplot(data=lang_report, x="language", y="accuracy", color="#4C72B0")
    plt.ylim(0, 1.05)
    plt.title("Per-language Test Accuracy (baseline)")
    plt.ylabel("Accuracy")
    plt.xlabel("Language")
    plt.tight_layout()
    plt.savefig(os.path.join(config.BASELINE_OUTPUT_DIR, "per_language_accuracy.png"), dpi=150)
    plt.close()

    print(f"\nSaved metrics + plots to {config.BASELINE_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
