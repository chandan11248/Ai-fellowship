"""
ONNX Model Converter.
Converts PyTorch intent classification and embedding models to ONNX
with dynamic batch axes and graph optimization.
"""

import os
from pathlib import Path
from typing import Tuple, Dict, Any
import torch
import torch.nn as nn
import onnx

from src.config import settings

ROUTING_LABELS = [
    "ACCOUNT", "CANCEL", "CONTACT", "DELIVERY", "FEEDBACK",
    "INVOICE", "ORDER", "PAYMENT", "REFUND", "SHIPPING", "SUBSCRIPTION"
]


class SupportIntentClassifier(nn.Module):
    """
    Neural Sequence Classifier for customer support routing (matching Week 14 domain).
    Maps token IDs to 11 support intent categories using embedding + feedforward + pooling.
    """

    def __init__(self, vocab_size: int = 10000, embed_dim: int = 128, hidden_dim: int = 128, num_classes: int = 11):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.dense1 = nn.Linear(embed_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.dense2 = nn.Linear(hidden_dim, hidden_dim)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        # input_ids: [batch_size, seq_len]
        embeds = self.embedding(input_ids)
        x = self.relu(self.dense1(embeds))
        x = self.layer_norm(self.dense2(x))

        # Mean pooling over active tokens
        if attention_mask is not None:
            mask_expanded = attention_mask.unsqueeze(-1).float()
            sum_embeddings = torch.sum(x * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            pooled = sum_embeddings / sum_mask
        else:
            pooled = torch.mean(x, dim=1)

        pooled = self.dropout(pooled)
        logits = self.classifier(pooled)
        return logits


def export_to_onnx(
    model: nn.Module,
    output_path: Path,
    vocab_size: int = 10000,
    seq_len: int = 64
) -> Path:
    """
    Exports PyTorch model to ONNX with dynamic batch and sequence dimensions.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model.eval()
    dummy_input_ids = torch.randint(0, vocab_size, (1, seq_len), dtype=torch.long)
    dummy_attention_mask = torch.ones((1, seq_len), dtype=torch.long)

    # Dynamic axes configuration for production variable batching
    dynamic_axes = {
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "logits": {0: "batch_size"}
    }

    try:
        torch.onnx.export(
            model,
            (dummy_input_ids, dummy_attention_mask),
            str(output_path),
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes=dynamic_axes,
            dynamo=False
        )
    except TypeError:
        torch.onnx.export(
            model,
            (dummy_input_ids, dummy_attention_mask),
            str(output_path),
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes=dynamic_axes
        )

    # Validate exported ONNX model
    onnx_model = onnx.load(str(output_path))
    onnx.checker.check_model(onnx_model)

    return output_path


def get_or_create_onnx_model() -> Tuple[nn.Module, Path]:
    """Ensure baseline PyTorch and ONNX models exist on disk."""
    onnx_dir = settings.ONNX_MODEL_DIR
    onnx_path = onnx_dir / "support_intent_classifier.onnx"

    model = SupportIntentClassifier()
    if not onnx_path.exists():
        export_to_onnx(model, onnx_path)

    return model, onnx_path
