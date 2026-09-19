"""
Script to export PyTorch classification model to ONNX.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.config import settings
from src.optimization.onnx_converter import get_or_create_onnx_model
from src.optimization.onnx_infer import ONNXIntentClassifier


def main():
    print("[ONNX Export] Building and exporting PyTorch intent classifier to ONNX...")
    model, onnx_path = get_or_create_onnx_model()
    print(f"[ONNX Export] Saved ONNX model to: {onnx_path}")
    print(f"[ONNX Export] Model file size: {onnx_path.stat().st_size / 1024:.2f} KB")

    print("\n[ONNX Test] Initializing ONNX Runtime inference session...")
    classifier = ONNXIntentClassifier(model_path=onnx_path)

    test_messages = [
        "Where is my order ORD-1001?",
        "I need a refund for my damaged keyboard.",
        "Can I cancel my subscription renewal?"
    ]

    for msg in test_messages:
        res = classifier.classify_text(msg)
        print(f"Query: \"{msg}\" -> Intent: {res['intent']} (Confidence: {res['confidence']*100:.2f}%)")


if __name__ == "__main__":
    main()
