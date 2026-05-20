# Week 3 Text-to-SQL Evaluation Report

## Summary

| Metric | Result |
| --- | ---: |
| Benchmark questions | 50 |
| SQL execution success | 50/50 (100.0%) |
| Ground-truth SQL match | 50/50 (100.0%) |
| Benchmark retries needed | 0 |
| Failed benchmark queries | 0 |

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

The retry demo intentionally starts with `SELECT product_name FROM products LIMIT 3;`, which fails because the schema uses `"productName"`. The agent reads the error, repairs the column name, retries once, and finishes with status `success` after 2 attempts.

Final repaired SQL:

```sql
SELECT "productName" FROM products LIMIT 3;
```

## Notes

The benchmark generator is deterministic, so generated SQL exactly matches the manually verified SQL for all provided questions. For a production LLM-based system, the same evaluation framework can compare generated SQL and result sets from non-deterministic model outputs against these reference files.
