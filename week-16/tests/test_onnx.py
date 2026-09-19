"""
Tests for ONNX Model Conversion and Inference.
"""

import pytest
import numpy as np
import torch
from pathlib import Path

from src.optimization.onnx_converter import SupportIntentClassifier, export_to_onnx, ROUTING_LABELS
from src.optimization.onnx_infer import ONNXIntentClassifier


def test_pytorch_model_forward():
    model = SupportIntentClassifier(vocab_size=1000, embed_dim=32, hidden_dim=32, num_classes=11)
    model.eval()

    dummy_input = torch.randint(1, 1000, (2, 16))
    dummy_mask = torch.ones((2, 16))

    with torch.no_grad():
        out = model(dummy_input, dummy_mask)

    assert out.shape == (2, 11)


def test_onnx_export_and_inference(tmp_path):
    model = SupportIntentClassifier(vocab_size=1000, embed_dim=32, hidden_dim=32, num_classes=11)
    onnx_file = tmp_path / "test_model.onnx"

    export_to_onnx(model, onnx_file, vocab_size=1000, seq_len=16)
    assert onnx_file.exists()

    classifier = ONNXIntentClassifier(model_path=onnx_file, vocab_size=1000)
    res = classifier.classify_text("Where is my order ORD-1001?")

    assert "intent" in res
    assert res["intent"] in ROUTING_LABELS
    assert 0.0 <= res["confidence"] <= 1.0
    assert len(res["probabilities"]) == 11
