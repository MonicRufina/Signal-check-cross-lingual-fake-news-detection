"""
Run inference with a fine-tuned checkpoint on new text, in any of the
languages the model was trained/transfers on.

Usage:
    python -m src.predict --checkpoint models/xlmr-fakenews --text "Your headline here"
    python -m src.predict --checkpoint models/xlmr-fakenews --file my_headlines.txt
"""

import argparse
import torch
from transformers import AutoTokenizer
from .model import load_model

from . import config

def load(checkpoint):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        tokenizer = AutoTokenizer.from_pretrained(checkpoint, fix_mistral_regex=True)
    except TypeError:
        tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    model = load_model(pretrained_path=checkpoint).to(device)
    model.eval()
    return tokenizer, model, device


import numpy as np


@torch.no_grad()
def classify(texts, tokenizer, model, device):
    enc = tokenizer(
        texts, truncation=True, padding=True,
        max_length=config.MAX_SEQ_LENGTH, return_tensors="pt",
    ).to(device)
    logits = model(**enc).logits
    probs = torch.softmax(logits, dim=-1)
    results = []
    for text, p in zip(texts, probs.cpu().tolist()):
        pred_id = int(max(range(len(p)), key=lambda i: p[i]))
        results.append({
            "text": text,
            "prediction": config.ID2LABEL[pred_id],
            "confidence": round(p[pred_id], 4),
            "probabilities": {config.ID2LABEL[i]: round(v, 4) for i, v in enumerate(p)},
        })
    return results


def explain_text(text, tokenizer, model, device):
    """
    Computes token-level saliency attribution scores for model interpretability (SHAP/Attention style).
    Returns a list of words and their normalized importance weight [0, 1].
    """
    model.eval()
    enc = tokenizer(
        text, truncation=True, max_length=config.MAX_SEQ_LENGTH, return_tensors="pt"
    ).to(device)

    input_ids = enc["input_ids"]
    attention_mask = enc["attention_mask"]
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0].cpu().tolist())

    try:
        embeds = model.transformer.get_input_embeddings()(input_ids).detach()
        embeds.requires_grad_(True)

        outputs = model.transformer(inputs_embeds=embeds, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state
        lstm_output, _ = model.lstm(sequence_output)

        input_mask_expanded = attention_mask.unsqueeze(-1).expand(lstm_output.size()).float()
        sum_embeddings = torch.sum(lstm_output * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        pooled = sum_embeddings / sum_mask

        logits = model.classifier(pooled)
        probs = torch.softmax(logits, dim=-1)
        pred_idx = torch.argmax(probs, dim=-1).item()

        target = logits[0, pred_idx]
        target.backward()

        if embeds.grad is not None:
            attribution = torch.sum(embeds.grad[0] * embeds[0], dim=-1).detach().cpu().numpy()
            scores = np.abs(attribution)
        else:
            scores = np.ones(len(tokens))
    except Exception:
        scores = np.ones(len(tokens))

    max_score = float(np.max(scores)) if len(scores) > 0 and np.max(scores) > 0 else 1.0
    norm_scores = [round(float(s) / max_score, 4) for s in scores]

    word_tokens = []
    current_word = ""
    current_score = 0.0
    current_count = 0

    for tok, sc in zip(tokens, norm_scores):
        if tok in ["<s>", "</s>", "<pad>", "<unk>"]:
            continue
        is_new_word = (
            tok.startswith(" ") or
            tok.startswith("\u2581") or
            tok.startswith("Ġ") or
            tok.startswith(" ") or
            tok.startswith("_")
        )
        clean_tok = tok.lstrip(" \u2581Ġ_ ")
        if not clean_tok:
            continue

        if is_new_word:
            if current_word:
                word_tokens.append({
                    "word": current_word,
                    "importance": round(current_score / max(current_count, 1), 3),
                })
            current_word = clean_tok
            current_score = sc
            current_count = 1
        else:
            current_word += clean_tok
            current_score += sc
            current_count += 1

    if current_word:
        word_tokens.append({
            "word": current_word,
            "importance": round(current_score / max(current_count, 1), 3),
        })

    return word_tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default=config.MODEL_OUTPUT_DIR)
    parser.add_argument("--text", help="A single piece of text to classify")
    parser.add_argument("--file", help="A text file, one item to classify per line")
    args = parser.parse_args()

    texts = []
    if args.text:
        texts.append(args.text)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            texts.extend([line.strip() for line in f if line.strip()])
    if not texts:
        parser.error("Provide --text or --file")

    tokenizer, model, device = load(args.checkpoint)
    for result in classify(texts, tokenizer, model, device):
        verdict = result["prediction"].upper()
        print(f"[{verdict:>4} | conf={result['confidence']:.2f}] {result['text']}")


if __name__ == "__main__":
    main()
