# Text-to-SQL Evaluation Notes

## Purpose

The goal of the evaluation is to check whether each natural language question is converted into the correct SQL and whether that SQL gives the expected result from the database.

## Reference Dataset

- Natural language questions: `question/sql_questions_only.csv`
- Ground truth SQL: `outputs/ground_truth_queries.csv`
- Exported query results: `outputs/query_results_export.csv`

## Metrics Used

| Metric | What It Checks |
| --- | --- |
| SQL generated | A SQL query was created for the question. |
| Safe query | The SQL was a read-only `SELECT` query. |
| Execution success | The SQL ran without a database error. |
| Reference match | The generated SQL matched the manually checked SQL. |
| Result check | The result rows looked correct for the question. |
| Tables and joins | The query used the right tables and join conditions. |
| Retry handling | A failed query could be fixed and retried. |

## Process

1. Decompose each question into intent, tables, columns, filters, and joins.
2. Generate SQL from the decomposition.
3. Validate that the query is a single SELECT statement.
4. Execute the query against the database.
5. Compare generated SQL with the ground truth SQL.
6. Export row count and sample rows for result inspection.
7. Log decomposition, SQL generation, execution time, errors, and retries.

## Ambiguous Questions

If a question has more than one possible meaning, I used the schema and the other benchmark questions to choose one meaning. For example, "Average product price" is treated as average `buyPrice` because there is a separate question for average MSRP.
