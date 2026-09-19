"""
CLI script to run the from-scratch evaluation harness and save reports.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.harness import EvaluationHarness


def main():
    print("================================================================")
    print("     SHOPASSIST AI - AGENTIC EVALUATION HARNESS (WEEK 16)       ")
    print("================================================================\n")

    harness = EvaluationHarness()
    print("Executing benchmark suite across test scenarios...")
    summary = harness.run_suite()

    # Generate Markdown Report
    report_md = harness.generate_markdown_report(summary)

    # Ensure outputs directory exists
    out_dir = Path(__file__).resolve().parent.parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write Markdown report
    report_path = out_dir / "evaluation_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\n[+] Saved evaluation report to: {report_path}")

    # Write JSON results
    json_path = out_dir / "evaluation_results.json"
    json_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    print(f"[+] Saved raw JSON results to: {json_path}")

    # Print summary to stdout
    print("\n" + report_md)


if __name__ == "__main__":
    main()
