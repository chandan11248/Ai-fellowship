# Week 3 SQL Agent Submission Plan

**Goal:** Build a self-contained `submission` folder for Tasks 1-4: benchmark SQL, decomposition, a Text-to-SQL pipeline, a FastAPI agent endpoint, logs, exported results, and an evaluation report.

**Architecture:** Use a deterministic rule-based pipeline for the fixed benchmark questions. Keep PostgreSQL compatibility in the SQL and provide a SQLite fallback only for local/offline verification from the provided `seed.sql`.

**Tech Stack:** Python 3.13, FastAPI, optional psycopg for PostgreSQL, standard-library sqlite3 for local evaluation.

---

## Files

- `sql_agent/benchmark.py`: benchmark questions, decomposition metadata, reference SQL, and explanations.
- `sql_agent/validator.py`: SELECT-only SQL validation.
- `sql_agent/database.py`: PostgreSQL adapter plus local SQLite seed loader.
- `sql_agent/sql_generator.py`: question normalization, SQL generation, retry repair, and answer summaries.
- `sql_agent/executor.py`: agent orchestration, execution, retries, and JSONL logging.
- `sql_agent/main.py`: FastAPI `POST /agent/sql` endpoint.
- `scripts/run_evaluation.py`: runs the benchmark and writes deliverables.
- `tests/test_pipeline.py`: behavior tests for generation, validation, execution, and retry.
- `outputs/`: generated CSV/Markdown deliverables.
- `logs/`: generated execution logs.

## Steps

- [x] Write failing tests for generation, validation, execution, and retry behavior.
- [x] Implement the benchmark catalog and SQL generator.
- [x] Implement SQL validation and database adapters.
- [x] Implement the agent executor and FastAPI endpoint.
- [x] Run tests and fix until green.
- [x] Run the benchmark evaluation script to generate required submission artifacts.
- [x] Review generated reports for completeness.
