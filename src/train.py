"""
Fine-tune a multilingual transformer (default: XLM-RoBERTa-base) for
cross-lingual fake news detection.

Usage:
    python -m src.train

Requires internet access to download the pretrained backbone from the
HuggingFace Hub the first time it runs, and a GPU is strongly recommended
(CPU fine-tuning of xlm-roberta-base on a few thousand examples is possible
but slow).
"""

import argparse
import os
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformers import (
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
)
from transformers.trainer_utils import get_last_checkpoint

from . import config
from .dataset import load_raw_dataframe, make_splits, save_splits, build_hf_datasets
from .model import load_tokenizer, load_model, tokenize_batch


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": float(accuracy_score(labels, preds)),
        "f1": float(f1_score(labels, preds, average="macro", zero_division=0)),
        "precision": float(precision_score(labels, preds, average="macro", zero_division=0)),
        "recall": float(recall_score(labels, preds, average="macro", zero_division=0)),
    }


def main():
    parser = argparse.ArgumentParser(description="Fine-tune or resume cross-lingual model")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from the latest checkpoint found in output directory",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Path to a specific checkpoint folder to resume from (e.g. models/xlmr-fakenews/checkpoint-414)",
    )
    cli_args, _ = parser.parse_known_args()

    splits = make_splits()
    save_splits(splits)
    print({k: len(v) for k, v in splits.items()})

    dataset_dict = build_hf_datasets(splits)

    print(f"Loading tokenizer + model: {config.MODEL_NAME} ...")
    tokenizer = load_tokenizer()
    model = load_model()

    tokenized = dataset_dict.map(
        lambda batch: tokenize_batch(batch, tokenizer),
        batched=True,
        remove_columns=["text", "language"],
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    args = TrainingArguments(
        output_dir=config.MODEL_OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=config.LEARNING_RATE,
        per_device_train_batch_size=config.BATCH_SIZE,
        per_device_eval_batch_size=config.EVAL_BATCH_SIZE,
        num_train_epochs=config.NUM_EPOCHS,
        weight_decay=config.WEIGHT_DECAY,
        warmup_ratio=config.WARMUP_RATIO,
        gradient_accumulation_steps=config.GRADIENT_ACCUMULATION_STEPS,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_steps=20,
        report_to=[],
        seed=config.SEED,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["val"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    resume_from_checkpoint = None
    if cli_args.checkpoint:
        resume_from_checkpoint = cli_args.checkpoint
        print(f"Resuming training from specified checkpoint: {resume_from_checkpoint}")
    elif cli_args.resume:
        last_ckpt = get_last_checkpoint(config.MODEL_OUTPUT_DIR) if os.path.isdir(config.MODEL_OUTPUT_DIR) else None
        if last_ckpt:
            resume_from_checkpoint = last_ckpt
            print(f"Resuming training from latest checkpoint: {resume_from_checkpoint}")
        else:
            print(f"No checkpoint found in {config.MODEL_OUTPUT_DIR}. Starting from scratch.")
    else:
        last_ckpt = get_last_checkpoint(config.MODEL_OUTPUT_DIR) if os.path.isdir(config.MODEL_OUTPUT_DIR) else None
        if last_ckpt:
            print(f"Notice: Found existing checkpoint '{last_ckpt}'. Run with --resume to continue from where it left off.")

    trainer.train(resume_from_checkpoint=resume_from_checkpoint)

    print("Evaluating on held-out test set ...")
    test_metrics = trainer.evaluate(tokenized["test"])
    print(test_metrics)

    if "zero_shot" in tokenized:
        print("Evaluating zero-shot cross-lingual transfer ...")
        zs_metrics = trainer.evaluate(tokenized["zero_shot"])
        print(zs_metrics)

    trainer.save_model(config.MODEL_OUTPUT_DIR)
    tokenizer.save_pretrained(config.MODEL_OUTPUT_DIR)
    print(f"Model saved to {config.MODEL_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
