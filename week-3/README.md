# Week 3 - Text-to-SQL Assignment

This folder contains the Week 3 work for the Text-to-SQL and mini SQL agent assignment. The database is based on the provided `seed.sql` file, and the benchmark questions are kept inside the `question/` folder.

The main idea is simple: take a natural language question, understand which tables and columns are needed, generate a safe SQL query, run it, and return the result.

## What This Covers

- writing reference SQL queries for the given questions
- breaking questions into intent, tables, columns, filters, and joins
- generating SQL from the known benchmark questions
- executing only safe `SELECT` queries
- logging the query process
- handling a simple retry case when SQL execution fails
- exposing the final flow through a FastAPI endpoint

## Basic Flow

```mermaid
flowchart TD
    A["Question"] --> B["Understand tables and columns"]
    B --> C["Generate SQL"]
    C --> D["Check SELECT-only safety"]
    D --> E["Run query"]
    E --> F{"Query worked?"}
    F -- "Yes" --> G["Return result and summary"]
    F -- "No" --> H["Read error and retry"]
    H --> C
    B --> I["Write log"]
    C --> I
    E --> I
```

## Folder Structure

```text
week-3/
├── question/                   # assignment PDFs and question CSV
├── sql_agent/                  # source code for the SQL agent
├── scripts/                    # evaluation script
├── tests/                      # test cases
├── outputs/                    # generated SQL, results, and reports
├── logs/                       # execution logs
├── seed.sql                    # database schema and sample data
└── requirements.txt            # Python dependencies
```

## Important Files

| File | Description |
| --- | --- |
| `question/sql_questions_only.csv` | original benchmark questions |
| `question/Week3_Task*_Assignment.pdf` | assignment PDFs |
| `sql_agent/benchmark.py` | question mapping, SQL, and decomposition details |
| `sql_agent/sql_generator.py` | SQL generation and simple repair logic |
| `sql_agent/validator.py` | blocks non-SELECT SQL |
| `sql_agent/executor.py` | runs the full question-to-result flow |
| `sql_agent/main.py` | FastAPI endpoint |
| `outputs/ground_truth_queries.csv` | reference SQL queries |
| `outputs/decompositions.csv` | question decomposition table |
| `outputs/query_results_export.csv` | exported query results |
| `outputs/evaluation_report.md` | short evaluation result |

## How to Run

Install the dependencies:

```bash
cd week-3
python3 -m pip install -r requirements.txt
```

Run the tests:

```bash
python3 -m pytest -p no:rerunfailures tests/test_pipeline.py -q
```

Regenerate the evaluation files:

```bash
python3 scripts/run_evaluation.py
```

Run the API:

```bash
python3 -m uvicorn sql_agent.main:app --reload
```

Test the API:

```bash
curl -X POST http://127.0.0.1:8000/agent/sql \
  -H "content-type: application/json" \
  -d '{"question":"How many shipped orders are from USA customers?"}'
```

## API Endpoint

```text
POST /agent/sql
```

Request body:

```json
{
  "question": "How many shipped orders are from USA customers?"
}
```

The response includes the generated SQL, result rows, a short summary, status, retry information, and execution time.

## Database Note

The SQL follows the provided schema in `seed.sql`. If `DATABASE_URL` is set, the code can connect to PostgreSQL. If it is not set, the code loads `seed.sql` into an in-memory SQLite database so the project can still be tested locally.

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/database_name"
```

## Evaluation

The evaluation script runs the 50 benchmark questions and writes the outputs into the `outputs/` folder. The exported result file shows row counts and sample rows, so screenshots are not required unless the assignment platform specifically asks for them.
