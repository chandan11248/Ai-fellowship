"""
Script to execute latency and throughput benchmark (PyTorch vs ONNX Runtime).
Saves benchmark_results.json and generates benchmark_comparison.png.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import json
from src.config import settings
from src.optimization.benchmark import run_latency_benchmark, plot_benchmark_results


def main():
    print("=" * 60)
    print("Running Performance Benchmark: PyTorch Baseline vs ONNX Runtime")
    print("=" * 60)

    output_dir = settings.BASE_DIR / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark_results.json"
    plot_path = output_dir / "benchmark_comparison.png"

    results = run_latency_benchmark(num_iterations=100, batch_sizes=[1, 4, 16, 32])

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[Saved JSON] Benchmark metrics saved to: {json_path}")

    plot_benchmark_results(results, plot_path)
    print(f"[Saved Plot] Comparison graph saved to: {plot_path}")

    print("\nBenchmark Summary Table:")
    print("-" * 75)
    print(f"{'Batch Size':<12} | {'PyTorch P50':<14} | {'ONNX P50':<12} | {'Speedup':<10} | {'Throughput Gain':<15}")
    print("-" * 75)
    for bsz_key, data in results["batch_benchmarks"].items():
        bsz = data["batch_size"]
        pt_p50 = f"{data['pytorch']['p50_ms']} ms"
        ort_p50 = f"{data['onnx_runtime']['p50_ms']} ms"
        speedup = f"{data['speedup_ratio']}x"
        tp_gain = f"{data['onnx_runtime']['throughput_samples_per_sec']} qps"
        print(f"{bsz:<12} | {pt_p50:<14} | {ort_p50:<12} | {speedup:<10} | {tp_gain:<15}")
    print("-" * 75)


if __name__ == "__main__":
    main()
