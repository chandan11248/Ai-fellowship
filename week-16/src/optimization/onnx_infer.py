"""
Optimized ONNX Runtime Inference Session.
Provides high-throughput, low-latency CPU/GPU execution with thread tuning,
memory arena allocation, and graph optimizations.
"""

from pathlib import Path
from typing import List, Dict, Any, Union, Tuple
import numpy as np
import onnxruntime as ort

from src.optimization.onnx_converter import ROUTING_LABELS, get_or_create_onnx_model


class ONNXIntentClassifier:
    """Production ONNX Runtime inference wrapper for Intent Classification."""

    def __init__(self, model_path: Union[str, Path] = None, num_threads: int = 4, vocab_size: int = 10000):
        if model_path is None:
            _, p = get_or_create_onnx_model()
            self.model_path = Path(p)
        else:
            self.model_path = Path(model_path)

        self.vocab_size = vocab_size

        # Configure session options for maximum throughput
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = num_threads
        opts.inter_op_num_threads = 2
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.enable_mem_pattern = True

        available_providers = ort.get_available_providers()
        providers = ["CPUExecutionProvider"]
        if "CUDAExecutionProvider" in available_providers:
            providers.insert(0, "CUDAExecutionProvider")

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=opts,
            providers=providers
        )
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.output_names = [out.name for out in self.session.get_outputs()]

    def _simple_tokenize(self, text: str, max_len: int = 64) -> Tuple[np.ndarray, np.ndarray]:
        """Simple deterministic tokenizer for inference."""
        words = text.lower().split()
        max_idx = max(self.vocab_size - 1, 1)
        ids = [(abs(hash(w)) % (max_idx - 1)) + 1 for w in words][:max_len]
        if len(ids) < max_len:
            mask = [1] * len(ids) + [0] * (max_len - len(ids))
            ids = ids + [0] * (max_len - len(ids))
        else:
            mask = [1] * max_len

        return (
            np.array([ids], dtype=np.int64),
            np.array([mask], dtype=np.int64)
        )

    def predict_batch(self, input_ids: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        """Run batch inference directly on numpy arrays."""
        ort_inputs = {
            "input_ids": input_ids.astype(np.int64),
            "attention_mask": attention_mask.astype(np.int64)
        }
        outputs = self.session.run(self.output_names, ort_inputs)
        return outputs[0]  # Logits

    def classify_text(self, text: str) -> Dict[str, Any]:
        """Classify a single text query and return top intent with probabilities."""
        input_ids, attention_mask = self._simple_tokenize(text)
        logits = self.predict_batch(input_ids, attention_mask)[0]

        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        top_idx = int(np.argmax(probs))
        top_intent = ROUTING_LABELS[top_idx] if top_idx < len(ROUTING_LABELS) else "GENERAL"

        return {
            "intent": top_intent,
            "confidence": float(probs[top_idx]),
            "probabilities": {ROUTING_LABELS[i]: float(probs[i]) for i in range(len(ROUTING_LABELS))}
        }
