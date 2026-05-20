# Pipeline Notes

## Approach

The benchmark questions are fixed, so I used a rule-based mapping for this assignment. Each question has its SQL query, decomposition details, and a short explanation.

## Flow

1. Receive a natural language question.
2. Normalize the question text.
3. Load the matching decomposition and SQL template.
4. Validate that SQL is a single read-only SELECT statement.
5. Execute the SQL through the database adapter.
6. If execution fails, repair known column naming mistakes and retry within the configured limit.
7. Return SQL, rows, row count, summary, status, retry metadata, and execution time.

## Database

The SQL follows the provided schema in `seed.sql`. PostgreSQL can be used through `DATABASE_URL`, but SQLite is also supported for local testing.

## Safety

The validator only allows a single `SELECT` statement and blocks queries that try to change the database.
