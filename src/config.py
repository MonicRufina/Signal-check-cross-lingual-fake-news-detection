"""
Central configuration for the Cross-Lingual Fake News Detection project.
Edit these values to point at your real dataset / change the backbone model.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_PATH = os.path.join(DATA_DIR, "raw", "merged_fakenews.csv")
XFACT_PATH = os.path.join(DATA_DIR, "raw", "train.all.tsv")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MODEL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "models", "xlmr-fakenews")
BASELINE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
# Any multilingual encoder from HuggingFace works here. Good options:
#   "xlm-roberta-base"        - 100+ languages, strong general baseline
#   "xlm-roberta-large"       - higher accuracy, needs a GPU with more VRAM
#   "bert-base-multilingual-cased" - lighter, 104 languages
#   "microsoft/mdeberta-v3-base"   - strong recent alternative
MODEL_NAME = "xlm-roberta-base"

MAX_SEQ_LENGTH = 256
NUM_LABELS = 2               # real=0, fake=1
LABEL2ID = {"real": 0, "fake": 1}
ID2LABEL = {0: "real", 1: "fake"}

# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
SEED = 42
TEST_SIZE = 0.2              # held out for evaluation
VAL_SIZE = 0.1                # held out from the training split for validation
BATCH_SIZE = 16
EVAL_BATCH_SIZE = 32
LEARNING_RATE = 2e-5
NUM_EPOCHS = 4
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
GRADIENT_ACCUMULATION_STEPS = 1

# Cross-lingual evaluation: languages to hold out entirely from training
# to measure zero-shot transfer (set to [] to disable).
ZERO_SHOT_HOLDOUT_LANGUAGES = []  # e.g. ["hi", "ar"] to test transfer to Hindi/Arabic

# Include X-FACT's unambiguous true/false claims in the training pool.
USE_XFACT = True
