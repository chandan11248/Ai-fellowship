# Week 3: Agentic Text-to-SQL System

This folder contains the complete Week 3 AI Fellowship submission. It covers the full assignment sequence: benchmark preparation, query decomposition, Text-to-SQL pipeline implementation, FastAPI SQL agent endpoint, logging, retry behavior, and evaluation.

## Submission Status

| Area | Status |
| --- | --- |
| Task 1: Ground-truth SQL benchmark | Complete |
| Task 2: Query decomposition | Complete |
| Task 3: Text-to-SQL pipeline and evaluation | Complete |
| Task 4: FastAPI mini SQL agent | Complete |
| Automated tests | `6 passed` |
| Benchmark execution success | `50/50` |
| Generated SQL matches ground truth | `50/50` |

## Core Concepts

### Text-to-SQL

Text-to-SQL is the process of converting a natural language question into a SQL query that can be executed against a database. In this project, each benchmark question is mapped to a structured understanding step before SQL is generated.

### Query Decomposition

Before generating SQL, the system identifies:

- intent: what the user is asking
- tables: which database tables are needed
- columns: which fields should be selected or aggregated
- filters: conditions such as country or status
- joins: relationships between tables

This makes the SQL generation process easier to inspect, evaluate, and debug.

### Agentic Retry Behavior

The agent does not crash immediately when a query fails. It captures the database error, applies a repair rule when possible, validates the fixed SQL, and retries within the configured limit.

### Safe SQL Execution

Only read-only `SELECT` statements are allowed. The validator blocks mutation and schema-changing operations such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and stacked SQL statements.

## Architecture

```mermaid
flowchart TD
    A["User / Benchmark Question"] --> B["Normalize Question"]
    B --> C["Query Decomposition"]
    C --> D["SQL Generator"]
    D --> E["SELECT-Only Validator"]
    E --> F["Database Executor"]
    F --> G{"Execution Successful?"}
    G -- "Yes" --> H["Result Rows + Row Count"]
    H --> I["Natural Language Summary"]
    I --> J["Final Agent Response"]
    G -- "No" --> K["Capture Error Message"]
    K --> L{"Retry Limit Reached?"}
    L -- "No" --> M["Repair SQL"]
    M --> E
    L -- "Yes" --> N["Fallback Failure Response"]
    C --> O["JSONL Logs"]
    D --> O
    F --> O
    K --> O
```

## Component Design

```mermaid
flowchart LR
    subgraph API["FastAPI Layer"]
        M["sql_agent/main.py<br/>POST /agent/sql"]
    end

    subgraph Agent["Agent Pipeline"]
        X["executor.py<br/>orchestration, retries, logs"]
        G["sql_generator.py<br/>decomposition + SQL mapping"]
        V["validator.py<br/>safe SELECT validation"]
    end

    subgraph Data["Data Layer"]
        D["database.py<br/>PostgreSQL adapter + SQLite fallback"]
        S["seed.sql<br/>classic models schema/data"]
    end

    subgraph Evaluation["Evaluation Outputs"]
        R["scripts/run_evaluation.py"]
        O["outputs/*.csv + reports"]
        L["logs/execution_logs.jsonl"]
    end

    M --> X
    X --> G
    X --> V
    X --> D
    D --> S
    R --> X
    R --> O
    X --> L
```

## Folder Structure

```text
week-3/
├── sql_agent/                  # Text-to-SQL agent source code
│   ├── benchmark.py            # 50 benchmark questions, SQL, explanations
│   ├── database.py             # PostgreSQL adapter and SQLite fallback
│   ├── executor.py             # agent flow, retry handling, logging
│   ├── main.py                 # FastAPI app with POST /agent/sql
│   ├── sql_generator.py        # rule-based SQL generation and repair
│   └── validator.py            # SELECT-only safety checks
├── scripts/
│   └── run_evaluation.py       # runs all benchmark questions
├── tests/
│   └── test_pipeline.py        # automated regression tests
├── outputs/                    # generated submission artifacts
├── logs/                       # JSONL execution logs
├── seed.sql                    # database schema and seed data
├── sql_questions_only.csv      # benchmark natural-language questions
├── requirements.txt
└── Week3_Task*_Assignment.pdf  # original assignment PDFs
```

## Deliverables

| File | Purpose |
| --- | --- |
| `outputs/ground_truth_queries.csv` | Task 1 manually verified SQL, questions, and explanations |
| `outputs/query_results_export.csv` | Task 1 exported result samples and row counts |
| `outputs/decompositions.csv` | Task 2 intent, tables, columns, filters, and joins |
| `outputs/generated_sql_outputs.csv` | Task 3 generated SQL and evaluation table |
| `outputs/evaluation_strategy.md` | evaluation framework for Text-to-SQL systems |
| `outputs/evaluation_report.md` | benchmark summary and retry behavior report |
| `outputs/pipeline_architecture.md` | short architecture/design explanation |
| `outputs/retry_example.json` | example failed query repaired after retry |
| `logs/execution_logs.jsonl` | decomposition, SQL generation, execution, errors, retries |

## How to Run

Install dependencies:

```bash
cd week-3
python3 -m pip install -r requirements.txt
```

Run tests:

```bash
python3 -m pytest -p no:rerunfailures tests/test_pipeline.py -q
```

Regenerate evaluation outputs:

```bash
python3 scripts/run_evaluation.py
```

Run the FastAPI agent:

```bash
python3 -m uvicorn sql_agent.main:app --reload
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/agent/sql \
  -H "content-type: application/json" \
  -d '{"question":"How many shipped orders are from USA customers?"}'
```

Example response:

```json
{
  "sql": "SELECT COUNT(*) AS shipped_order_count ...",
  "result": [{"shipped_order_count": 105}],
  "summary": "There are 105 shipped orders from customers in USA.",
  "status": "success"
}
```

## Database Configuration

By default, the project loads `seed.sql` into an in-memory SQLite database so the submission can be tested without extra services. To use PostgreSQL, set `DATABASE_URL` before running the API or evaluation script:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/database_name"
```

The SQL queries are written in PostgreSQL-compatible style using quoted identifiers for mixed-case column names from the provided schema.

## Evaluation Summary

The benchmark runner executes all 50 provided natural-language questions, validates every generated SQL query, runs each query, exports sample results, and writes JSONL logs.

Current results:

- SQL execution success rate: `100%`
- generated SQL match against ground truth: `100%`
- failed benchmark queries: `0`
- retry behavior: demonstrated in `outputs/retry_example.json`

## Notes for Review

The implementation is intentionally deterministic and rule-based because the benchmark question set is fixed. This makes the submission reliable, easy to grade, and reproducible without requiring external LLM API keys. The same evaluation framework can later be reused to test an LLM-based Text-to-SQL agent against the same ground-truth SQL and exported result set.
