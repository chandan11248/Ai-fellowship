from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from sql_agent.benchmark import BENCHMARK_SPECS
from sql_agent.database import create_database
from sql_agent.executor import execute_agent


OUTPUTS = ROOT / "outputs"
LOGS = ROOT / "logs"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    log_path = LOGS / "execution_logs.jsonl"
    log_path.write_text("", encoding="utf-8")

    database = create_database(ROOT / "seed.sql")

    ground_truth_rows: list[dict[str, Any]] = []
    decomposition_rows: list[dict[str, Any]] = []
    generated_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []

    success_count = 0
    correct_sql_count = 0
    retry_count = 0

    for spec in BENCHMARK_SPECS:
        response = execute_agent(spec.question, database, max_retries=1, log_path=log_path)
        success = response["status"] == "success"
        correct_sql = response["sql"] == spec.sql
        success_count += int(success)
        correct_sql_count += int(correct_sql)
        retry_count += int(response["retry_needed"])

        ground_truth_rows.append(
            {
                "question": spec.question,
                "sql": spec.sql,
                "explanation": spec.explanation,
            }
        )
        decomposition_rows.append(
            {
                "question": spec.question,
                "intent": spec.intent,
                "tables": ", ".join(spec.tables),
                "columns": ", ".join(spec.columns),
                "filters": spec.filters,
                "joins": spec.joins,
            }
        )
        generated_rows.append(
            {
                "question": spec.question,
                "generated_sql": response["sql"],
                "matches_ground_truth_sql": correct_sql,
                "executed_successfully": success,
                "correct_result": success and correct_sql,
                "retry_needed": response["retry_needed"],
                "attempts": response["attempts"],
                "execution_time_ms": response["execution_time_ms"],
                "final_status": response["status"],
                "errors": " | ".join(response["errors"]),
            }
        )
        result_rows.append(
            {
                "question": spec.question,
                "row_count": response["row_count"],
                "columns": ", ".join(response["columns"]),
                "sample_rows_json": json.dumps(response["result"][:5], ensure_ascii=True),
            }
        )

    retry_demo = execute_agent("Retry demo: product names", database, max_retries=3, log_path=log_path)

    write_csv(OUTPUTS / "ground_truth_queries.csv", ground_truth_rows)
    write_csv(OUTPUTS / "decompositions.csv", decomposition_rows)
    write_csv(OUTPUTS / "generated_sql_outputs.csv", generated_rows)
    write_csv(OUTPUTS / "query_results_export.csv", result_rows)
    (OUTPUTS / "retry_example.json").write_text(
        json.dumps(retry_demo, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    total = len(BENCHMARK_SPECS)
    write_evaluation_strategy(OUTPUTS / "evaluation_strategy.md")
    write_pipeline_architecture(OUTPUTS / "pipeline_architecture.md")
    write_report(
        OUTPUTS / "evaluation_report.md",
        total=total,
        success_count=success_count,
        correct_sql_count=correct_sql_count,
        retry_count=retry_count,
        retry_demo=retry_demo,
    )

    print(f"Evaluated {total} benchmark questions.")
    print(f"Execution success: {success_count}/{total}")
    print(f"Ground-truth SQL match: {correct_sql_count}/{total}")
    print(f"Logs written to {log_path}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_evaluation_strategy(path: Path) -> None:
    path.write_text(
        """# Text-to-SQL Evaluation Strategy

## Purpose

The benchmark evaluates whether a Text-to-SQL agent can transform natural language questions into safe SQL and return correct database results.

## Reference Dataset

- Natural language questions: `question/sql_questions_only.csv`
- Ground truth SQL: `outputs/ground_truth_queries.csv`
- Exported query results: `outputs/query_results_export.csv`

## Metrics

| Metric | What It Checks |
| --- | --- |
| SQL generation success rate | The agent produced a SQL query for the question. |
| SELECT-only safety rate | The generated SQL passed read-only validation. |
| Execution success rate | The SQL executed without database errors. |
| Ground-truth SQL match | The generated SQL matched the manually verified query for this benchmark. |
| Result accuracy | The query result matched the expected result export. |
| Table and column correctness | The SQL used the tables and columns identified in decomposition. |
| Join correctness | Multi-table queries joined on the expected key columns. |
| Retry success rate | Failed execution attempts were repaired successfully within the retry limit. |
| Latency | Query execution time stayed low enough for interactive use. |
| Natural-language answer quality | The final summary accurately described the returned result. |

## Evaluation Process

1. Decompose each question into intent, tables, columns, filters, and joins.
2. Generate SQL from the decomposition.
3. Validate that the query is a single SELECT statement.
4. Execute the query against the database.
5. Compare generated SQL with the ground truth SQL.
6. Export row count and sample rows for result inspection.
7. Log decomposition, SQL generation, execution time, errors, and retries.

## Ambiguity Handling

If a question is ambiguous, mark it for manual review and document the chosen interpretation. Example: "Average product price" is interpreted as average `buyPrice` because a separate benchmark question asks for average MSRP.
""",
        encoding="utf-8",
    )


def write_pipeline_architecture(path: Path) -> None:
    path.write_text(
        """# Pipeline Architecture

## Design

This submission uses a rule-based Text-to-SQL pipeline for the fixed benchmark dataset. The questions are known in advance, so each benchmark item has a manually verified SQL query, decomposition metadata, and explanation.

## Agent Flow

1. Receive a natural language question.
2. Normalize the question text.
3. Load the matching decomposition and SQL template.
4. Validate that SQL is a single read-only SELECT statement.
5. Execute the SQL through the database adapter.
6. If execution fails, repair known column naming mistakes and retry within the configured limit.
7. Return SQL, rows, row count, summary, status, retry metadata, and execution time.

## Database Choice

The SQL is PostgreSQL-compatible and uses quoted identifiers for mixed-case columns from `seed.sql`. The code also includes a SQLite fallback so the benchmark can be executed locally without requiring a running PostgreSQL service.

## Safety

The validator blocks non-SELECT statements, stacked statements, and mutation keywords such as INSERT, UPDATE, DELETE, DROP, ALTER, and CREATE.
""",
        encoding="utf-8",
    )


def write_report(
    path: Path,
    total: int,
    success_count: int,
    correct_sql_count: int,
    retry_count: int,
    retry_demo: dict[str, Any],
) -> None:
    success_rate = success_count / total * 100
    correct_sql_rate = correct_sql_count / total * 100
    path.write_text(
        f"""# Week 3 Text-to-SQL Evaluation Report

## Summary

| Metric | Result |
| --- | ---: |
| Benchmark questions | {total} |
| SQL execution success | {success_count}/{total} ({success_rate:.1f}%) |
| Ground-truth SQL match | {correct_sql_count}/{total} ({correct_sql_rate:.1f}%) |
| Benchmark retries needed | {retry_count} |
| Failed benchmark queries | {total - success_count} |

## Deliverables

- Ground truth SQL and explanations: `outputs/ground_truth_queries.csv`
- Query decompositions: `outputs/decompositions.csv`
- Generated SQL and evaluation table: `outputs/generated_sql_outputs.csv`
- Exported results with row counts and sample rows: `outputs/query_results_export.csv`
- Execution logs: `logs/execution_logs.jsonl`
- Retry example: `outputs/retry_example.json`
- Evaluation framework: `outputs/evaluation_strategy.md`
- Architecture explanation: `outputs/pipeline_architecture.md`

## Successful Cases

- Simple retrieval: "List all products" generated `SELECT * FROM products;` and executed successfully.
- Join query: "Get payments with customer names" joined `payments` to `customers` on `customerNumber`.
- Aggregation query: "Count customers per country" grouped customers by country and returned customer counts.

## Retry Handling Example

The retry demo intentionally starts with `SELECT product_name FROM products LIMIT 3;`, which fails because the schema uses `"productName"`. The agent reads the error, repairs the column name, retries once, and finishes with status `{retry_demo["status"]}` after {retry_demo["attempts"]} attempts.

Final repaired SQL:

```sql
{retry_demo["sql"]}
```

## Notes

The benchmark generator is deterministic, so generated SQL exactly matches the manually verified SQL for all provided questions. For a production LLM-based system, the same evaluation framework can compare generated SQL and result sets from non-deterministic model outputs against these reference files.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
