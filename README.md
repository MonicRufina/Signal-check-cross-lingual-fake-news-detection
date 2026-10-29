# Cross-Lingual Fake News Detection with Multilingual Transformers

Deep learning project that fine-tunes a hybrid multilingual model
(**XLM-RoBERTa + bidirectional LSTM**, default) to classify news text as **real** or **fake**
across multiple languages at once, and measures how well it transfers to
languages it has seen little or none of during fine-tuning ("zero-shot
cross-lingual transfer").

## Why this approach

Fake news detectors trained only on English data fail on other languages
because they never learn language-agnostic signals — they overfit to
English-specific wording. Multilingual transformers like XLM-RoBERTa are
pretrained on 100+ languages with a **shared subword vocabulary and shared
embedding space**, so a classification head fine-tuned on top of it learns
representations that transfer across languages, even ones barely present in
the fine-tuning set. This is the core idea the project demonstrates and
measures.

## Project structure

```
cross-lingual-fake-news-detection/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/sample_multilingual_fakenews.csv   # sample dataset (7 languages)
│   ├── prepare_data.py                        # template to merge real datasets
│   └── processed/                             # generated: train/val/test/zero_shot splits
├── src/
│   ├── config.py       # all hyperparameters & paths in one place
│   ├── dataset.py       # loading, cleaning, stratified splitting
│   ├── model.py         # tokenizer + XLM-R classification head
│   ├── train.py         # fine-tuning loop (HuggingFace Trainer)
│   ├── evaluate.py       # test-set + per-language evaluation
│   ├── predict.py        # CLI inference on new text
│   └── baseline.py       # offline TF-IDF + LogisticRegression reference model
├── models/               # generated: saved fine-tuned checkpoints
└── outputs/              # generated: metrics, confusion matrix, plots
```

## Dataset

Ships with `data/raw/sample_multilingual_fakenews.csv` — 54 hand-written
real/fake news examples spanning **7 languages** (English, Spanish, French,
German, Hindi, Arabic, Portuguese), so the whole pipeline runs immediately
with no downloads. This is a **demo-scale** dataset meant to prove the
pipeline works end-to-end, not to produce a production-grade model.

For real training, see `data/prepare_data.py` for a template and a list of
public multilingual fake-news datasets (LIAR, FakeNewsNet, IFND, AFND,
FakeCovid, X-FACT, etc.) to merge into the same `text,label,language` schema.
Swap in a real merged CSV and everything downstream — splitting, tokenizing,
training, evaluation — works unchanged.

The current training pipeline also loads `data/raw/train.all.tsv` (X-FACT)
automatically. Only X-FACT's unambiguous `true` and `false` labels are used;
`partly true/misleading` examples are excluded. X-FACT claims are added to the
training/validation pool, while `data/raw/20.xlsx` remains the held-out test
set. Set `USE_XFACT = False` in `src/config.py` to disable this.

## The two models in this project

| Model | File | Runs where | Purpose |
|---|---|---|---|
| **XLM-RoBERTa + BiLSTM hybrid** (the actual deep learning model) | `src/train.py`, `src/model.py` | Needs internet (to download pretrained weights) + ideally a GPU | The real deliverable — transformer representations refined by a bidirectional sequence model |
| **TF-IDF char n-gram + Logistic Regression** | `src/baseline.py` | Fully offline, CPU, seconds | Reference baseline so you can confirm the deep model is actually adding value, and to sanity-check the data pipeline instantly |

I ran the baseline in this sandbox to validate the full pipeline
(load → clean → stratified split → train → evaluate → per-language
breakdown → plots) end-to-end on the sample dataset — see **Results**
below. Downloading XLM-RoBERTa's pretrained weights requires reaching
huggingface.co, which this sandbox doesn't have network access to, so
`src/train.py` is fully written and ready to run, but needs to be executed
in your own environment (Colab, local machine, or a server) where that
download is possible. Instructions are below.

## Setup

```bash
cd cross-lingual-fake-news-detection
python -m venv venv && source venv/bin/activate    # optional but recommended
pip install -r requirements.txt
```

## Running it

**1. Fine-tune XLM-RoBERTa (the deep learning model):**
```bash
python -m src.train
```
To resume training from the latest saved epoch checkpoint instead of restarting from scratch:
```bash
python -m src.train --resume
```
Or resume from a specific checkpoint folder:
```bash
python -m src.train --checkpoint models/xlmr-fakenews/checkpoint-414
```
This loads the Excel data plus the binary-labeled X-FACT claims, creates a
stratified train/validation split, fine-tunes the hybrid
`xlm-roberta-base` + BiLSTM model for 4 epochs, evaluates on the held-out test
set, and saves the checkpoint to `models/xlmr-fakenews/`. Swap the backbone
in `src/config.py` (`MODEL_NAME`) to `xlm-roberta-large` or
`microsoft/mdeberta-v3-base` for a stronger/weaker trade-off.

**2. Evaluate a checkpoint, with per-language breakdown:**
```bash
python -m src.evaluate --checkpoint models/xlmr-fakenews
```

**3. Classify new text:**
```bash
python -m src.predict --checkpoint models/xlmr-fakenews --text "Drinking hot water cures every disease, doctors warn."
```

**4. Run the offline baseline (works right now, no setup needed beyond `pandas`/`scikit-learn`):**
```bash
python -m src.baseline
```

## Measuring cross-lingual transfer

Set `ZERO_SHOT_HOLDOUT_LANGUAGES` in `src/config.py` (e.g. `["hi", "ar"]`)
to exclude those languages entirely from fine-tuning, then check the
`zero_shot` metrics that `src/train.py` prints — this tells you how well the
model generalizes to a language it never saw labeled examples for, which is
the central research question in cross-lingual fake news detection.

## Results (baseline, sample dataset)

Run in this sandbox on the 54-example sample dataset (41 train / 11 test):

| Metric | Score |
|---|---|
| Accuracy | 0.909 |
| F1 (macro) | 0.909 |
| Precision (macro) | 0.917 |
| Recall (macro) | 0.917 |

Per-language and confusion-matrix plots are in `outputs/`
(`confusion_matrix.png`, `per_language_accuracy.png`,
`baseline_per_language_metrics.csv`). These numbers are on a tiny sample and
mainly validate the pipeline — accuracy will look different (and more
meaningful) once a real dataset of thousands of examples per language is
substituted in.

**Note:** these baseline numbers are on a *held-out* test set drawn from the
same 54-example sample, so treat them as a pipeline sanity check, not a
generalization claim — with real data volume, run the XLM-R fine-tune for
numbers that actually reflect cross-lingual transformer performance.

## Extending this project

- **Add languages**: append rows to the CSV with any new `language` code;
  no code changes needed.
- **Explainability**: add SHAP or LIME on top of `src/predict.py` to
  highlight which tokens drove a "fake" verdict.
- **Deploy**: wrap `src/predict.py`'s `classify()` function in a small
  FastAPI/Flask endpoint for a demo UI.
- **Stronger backbone**: try `xlm-roberta-large` or `microsoft/mdeberta-v3-base`
  in `src/config.py` for a few points of accuracy at the cost of compute.
- **Data augmentation**: back-translation between languages is a common way
  to expand low-resource language coverage for this task.
