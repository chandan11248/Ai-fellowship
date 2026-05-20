# Text-to-SQL Evaluation Strategy

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
