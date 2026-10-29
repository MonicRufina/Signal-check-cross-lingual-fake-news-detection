"""
Model + tokenizer construction for cross-lingual fake news classification.

Backbone: a multilingual transformer encoder (default XLM-RoBERTa-base) with
a sequence classification head (2 classes: real / fake). Fine-tuning the full
encoder gives the model shared cross-lingual representations, so it can
generalize to languages that are under-represented (or entirely absent) in
the fine-tuning data ("zero-shot cross-lingual transfer").
"""

import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer,
    AutoModel,
    AutoConfig,
    PreTrainedModel
)
from transformers.modeling_outputs import SequenceClassifierOutput

from . import config

def load_tokenizer(pretrained_path=None):
    path = pretrained_path or config.MODEL_NAME
    try:
        return AutoTokenizer.from_pretrained(path, fix_mistral_regex=True)
    except TypeError:
        return AutoTokenizer.from_pretrained(path)

class HybridFakeNewsModel(PreTrainedModel):
    def __init__(self, model_config):
        super().__init__(model_config)
        self.num_labels = model_config.num_labels
        self.transformer = AutoModel.from_pretrained(model_config._name_or_path, config=model_config)
        
        self.hidden_dim = 256
        self.lstm = nn.LSTM(
            input_size=model_config.hidden_size,
            hidden_size=self.hidden_dim,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )
        self.dropout = nn.Dropout(0.2)
        self.classifier = nn.Linear(self.hidden_dim * 2, model_config.num_labels)
        
    def forward(self, input_ids=None, attention_mask=None, token_type_ids=None, labels=None, **kwargs):
        outputs = self.transformer(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        sequence_output = outputs.last_hidden_state
        
        # BiLSTM
        lstm_output, _ = self.lstm(sequence_output)
        
        # Masked Mean Pooling: zero out padding tokens and average the rest
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(lstm_output.size()).float()
        sum_embeddings = torch.sum(lstm_output * input_mask_expanded, 1)
        sum_mask = input_mask_expanded.sum(1)
        sum_mask = torch.clamp(sum_mask, min=1e-9)
        pooled_output = sum_embeddings / sum_mask
        
        x = self.dropout(pooled_output)
        logits = self.classifier(x)
        
        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
            
        return SequenceClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

def load_model(pretrained_path=None):
    model_config = AutoConfig.from_pretrained(
        config.MODEL_NAME, 
        num_labels=config.NUM_LABELS,
        id2label=config.ID2LABEL,
        label2id=config.LABEL2ID
    )
    model = HybridFakeNewsModel(model_config)
    if pretrained_path is not None:
        import os
        pt_path = os.path.join(pretrained_path, "pytorch_model.bin")
        st_path = os.path.join(pretrained_path, "model.safetensors")
        if os.path.exists(st_path):
            from safetensors.torch import load_file
            model.load_state_dict(load_file(st_path))
        elif os.path.exists(pt_path):
            model.load_state_dict(torch.load(pt_path, map_location="cpu"))
    return model

def tokenize_batch(examples, tokenizer):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=config.MAX_SEQ_LENGTH,
        padding="max_length",
    )
