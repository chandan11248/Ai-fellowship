from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sql_agent.benchmark import BENCHMARK_SPECS, find_spec
from sql_agent.database import SQLiteDatabase
from sql_agent.executor import execute_agent
from sql_agent.main import app
from sql_agent.sql_generator import generate_sql
from sql_agent.validator import UnsafeSQLError, validate_select_only


ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_contains_all_provided_questions():
    assert len(BENCHMARK_SPECS) == 50
    assert find_spec("List all products").sql == 'SELECT * FROM products;'


def test_generate_sql_for_join_question_matches_reference():
    sql = generate_sql("Get payments with customer names")

    assert sql == (
        'SELECT p."checkNumber", p."paymentDate", p."amount", c."customerName"\n'
        "FROM payments p\n"
        'JOIN customers c ON c."customerNumber" = p."customerNumber"\n'
        'ORDER BY p."paymentDate", p."checkNumber";'
    )


def test_validator_blocks_non_select_statements():
    with pytest.raises(UnsafeSQLError):
        validate_select_only('SELECT * FROM customers; DROP TABLE customers;')

    with pytest.raises(UnsafeSQLError):
        validate_select_only('UPDATE customers SET "country" = \'USA\';')


def test_agent_executes_known_question_against_seed_database():
    db = SQLiteDatabase.from_seed(ROOT / "seed.sql")

    response = execute_agent(
        "Total number of customers",
        db,
        max_retries=1,
        log_path=None,
    )

    assert response["status"] == "success"
    assert response["row_count"] == 1
    assert response["result"][0]["total_customers"] > 0
    assert response["retry_needed"] is False


def test_agent_repairs_common_column_name_error_on_retry():
    db = SQLiteDatabase.from_seed(ROOT / "seed.sql")

    response = execute_agent(
        "Retry demo: product names",
        db,
        max_retries=3,
        log_path=None,
    )

    assert response["status"] == "success"
    assert response["retry_needed"] is True
    assert response["attempts"] == 2
    assert '"productName"' in response["sql"]
    assert response["row_count"] > 0


def test_fastapi_endpoint_returns_agent_response(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_LOG_PATH", str(tmp_path / "api_logs.jsonl"))
    client = TestClient(app)

    response = client.post(
        "/agent/sql",
        json={"question": "How many shipped orders are from USA customers?"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["row_count"] == 1
    assert "shipped orders" in payload["summary"]
