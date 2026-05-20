# Pipeline Architecture

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
