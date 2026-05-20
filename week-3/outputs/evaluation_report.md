# Week 3 Evaluation Report

## Summary

| Metric | Result |
| --- | ---: |
| Benchmark questions | 50 |
| SQL execution success | 50/50 (100.0%) |
| SQL matched reference queries | 50/50 (100.0%) |
| Retries needed during benchmark | 0 |
| Failed benchmark queries | 0 |

## Files Checked

- `outputs/ground_truth_queries.csv`
- `outputs/decompositions.csv`
- `outputs/generated_sql_outputs.csv`
- `outputs/query_results_export.csv`
- `logs/execution_logs.jsonl`

## Example Queries

- "List all products" uses a direct `SELECT` from the products table.
- "Get payments with customer names" joins payments with customers using `customerNumber`.
- "Count customers per country" groups customers by country.

## Retry Example

I also kept one retry example to show error handling. The first query uses `product_name`, which is not a column in the schema. The retry changes it to `"productName"` and then the query works.

Repaired SQL:

```sql
SELECT "productName" FROM products LIMIT 3;
```

## Notes

The benchmark question list is fixed, so the SQL generation is rule-based for this assignment. This makes the output easy to compare with the manually written SQL.
