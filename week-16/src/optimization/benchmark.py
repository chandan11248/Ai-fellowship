"""
Performance Benchmarking Engine.
Compares PyTorch CPU/GPU baseline against ONNX Runtime optimized execution
across batch sizes (1, 4, 16, 32) measuring p50/p95/p99 latency and throughput.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import torch
import matplotlib.pyplot as plt

from src.optimization.onnx_converter import SupportIntentClassifier, get_or_create_onnx_model
from src.optimization.onnx_infer import ONNXIntentClassifier


def run_latency_benchmark(
    num_iterations: int = 100,
    warmup: int = 10,
    batch_sizes: List[int] = [1, 4, 16, 32],
    seq_len: int = 64
) -> Dict[str, Any]:
    """Execute comparative benchmark between PyTorch and ONNX Runtime."""
    pytorch_model, onnx_path = get_or_create_onnx_model()
    pytorch_model.eval()

    onnx_classifier = ONNXIntentClassifier(model_path=onnx_path)

    results: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "iterations": num_iterations,
        "seq_len": seq_len,
        "batch_benchmarks": {}
    }

    for bsz in batch_sizes:
        # Generate dummy input batches
        input_ids_np = np.random.randint(1, 9999, size=(bsz, seq_len), dtype=np.int64)
        attention_mask_np = np.ones((bsz, seq_len), dtype=np.int64)

        input_ids_torch = torch.from_numpy(input_ids_np)
        attention_mask_torch = torch.from_numpy(attention_mask_np)

        # -------------------------------------------------------------
        # 1. Benchmark PyTorch
        # -------------------------------------------------------------
        with torch.no_grad():
            for _ in range(warmup):
                _ = pytorch_model(input_ids_torch, attention_mask_torch)

            pt_latencies = []
            for _ in range(num_iterations):
                t0 = time.perf_counter()
                _ = pytorch_model(input_ids_torch, attention_mask_torch)
                pt_latencies.append((time.perf_counter() - t0) * 1000.0)

        # -------------------------------------------------------------
        # 2. Benchmark ONNX Runtime
        # -------------------------------------------------------------
        for _ in range(warmup):
            _ = onnx_classifier.predict_batch(input_ids_np, attention_mask_np)

        ort_latencies = []
        for _ in range(num_iterations):
            t0 = time.perf_counter()
            _ = onnx_classifier.predict_batch(input_ids_np, attention_mask_np)
            ort_latencies.append((time.perf_counter() - t0) * 1000.0)

        # Compute Statistics
        pt_p50 = float(np.percentile(pt_latencies, 50))
        pt_p95 = float(np.percentile(pt_latencies, 95))
        pt_p99 = float(np.percentile(pt_latencies, 99))
        pt_mean = float(np.mean(pt_latencies))
        pt_throughput = (bsz * num_iterations) / (sum(pt_latencies) / 1000.0)

        ort_p50 = float(np.percentile(ort_latencies, 50))
        ort_p95 = float(np.percentile(ort_latencies, 95))
        ort_p99 = float(np.percentile(ort_latencies, 99))
        ort_mean = float(np.mean(ort_latencies))
        ort_throughput = (bsz * num_iterations) / (sum(ort_latencies) / 1000.0)

        speedup = pt_mean / max(ort_mean, 1e-6)

        results["batch_benchmarks"][f"batch_{bsz}"] = {
            "batch_size": bsz,
            "pytorch": {
                "p50_ms": round(pt_p50, 3),
                "p95_ms": round(pt_p95, 3),
                "p99_ms": round(pt_p99, 3),
                "mean_ms": round(pt_mean, 3),
                "throughput_samples_per_sec": round(pt_throughput, 1)
            },
            "onnx_runtime": {
                "p50_ms": round(ort_p50, 3),
                "p95_ms": round(ort_p95, 3),
                "p99_ms": round(ort_p99, 3),
                "mean_ms": round(ort_mean, 3),
                "throughput_samples_per_sec": round(ort_throughput, 1)
            },
            "latency_reduction_pct": round(((pt_mean - ort_mean) / pt_mean) * 100, 2),
            "speedup_ratio": round(speedup, 2)
        }

    return results


def plot_benchmark_results(benchmark_data: Dict[str, Any], output_path: Path) -> None:
    """Generate professional comparative plots."""
    batches = []
    pt_p50 = []
    ort_p50 = []
    pt_p95 = []
    ort_p95 = []
    pt_throughput = []
    ort_throughput = []

    for bsz_key, data in benchmark_data["batch_benchmarks"].items():
        bsz = data["batch_size"]
        batches.append(f"Batch {bsz}")
        pt_p50.append(data["pytorch"]["p50_ms"])
        ort_p50.append(data["onnx_runtime"]["p50_ms"])
        pt_p95.append(data["pytorch"]["p95_ms"])
        ort_p95.append(data["onnx_runtime"]["p95_ms"])
        pt_throughput.append(data["pytorch"]["throughput_samples_per_sec"])
        ort_throughput.append(data["onnx_runtime"]["throughput_samples_per_sec"])

    x = np.arange(len(batches))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=150)
    fig.patch.set_facecolor("#FAFAFA")

    # Plot 1: P50 & P95 Latency Comparison
    rects1 = ax1.bar(x - width/2, pt_p50, width, label="PyTorch P50", color="#E53935", alpha=0.85)
    rects2 = ax1.bar(x + width/2, ort_p50, width, label="ONNX Runtime P50", color="#1E88E5", alpha=0.85)

    ax1.plot(x - width/2, pt_p95, "r--o", label="PyTorch P95", alpha=0.7)
    ax1.plot(x + width/2, ort_p95, "b--o", label="ONNX P95", alpha=0.7)

    ax1.set_ylabel("Latency (ms) [Lower is Better]", fontsize=11, fontweight="bold")
    ax1.set_title("Inference Latency: PyTorch vs ONNX Runtime", fontsize=12, fontweight="bold", pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(batches)
    ax1.legend(loc="upper left")
    ax1.grid(axis="y", linestyle="--", alpha=0.4)

    # Plot 2: Throughput Comparison
    ax2.bar(x - width/2, pt_throughput, width, label="PyTorch Baseline", color="#EF5350", alpha=0.85)
    ax2.bar(x + width/2, ort_throughput, width, label="ONNX Runtime Optimized", color="#29B6F6", alpha=0.85)

    ax2.set_ylabel("Throughput (Samples / sec) [Higher is Better]", fontsize=11, fontweight="bold")
    ax2.set_title("Throughput Scaling: PyTorch vs ONNX Runtime", fontsize=12, fontweight="bold", pad=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(batches)
    ax2.legend(loc="upper left")
    ax2.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
