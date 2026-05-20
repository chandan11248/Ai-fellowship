from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .database import Database
from .sql_generator import decompose_question, generate_sql, repair_sql, summarize_result
from .validator import validate_select_only


def execute_agent(
    question: str,
    database: Database,
    max_retries: int = 3,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        decomposition = decompose_question(question)
        _write_log(log_path, "decomposition", {"question": question, "decomposition": decomposition})
        sql = generate_sql(question)
        _write_log(log_path, "sql_generation", {"question": question, "sql": sql})
    except Exception as exc:
        return _failure_response(question, "", [], str(exc), 0, False, log_path)

    attempts = 0
    errors: list[str] = []
    current_sql = sql
    retry_needed = False

    while attempts <= max_retries:
        attempts += 1
        try:
            validate_select_only(current_sql)
            result = database.execute(current_sql)
            safe_rows = _json_safe(result.rows)
            response = {
                "question": question,
                "decomposition": decomposition,
                "sql": current_sql,
                "result": safe_rows,
                "row_count": result.row_count,
                "columns": result.columns,
                "summary": summarize_result(question, safe_rows),
                "status": "success",
                "attempts": attempts,
                "retry_needed": retry_needed,
                "errors": errors,
                "execution_time_ms": round(result.execution_time_ms, 3),
            }
            _write_log(
                log_path,
                "execution_success",
                {
                    "question": question,
                    "attempt": attempts,
                    "execution_time_ms": response["execution_time_ms"],
                    "row_count": result.row_count,
                },
            )
            return response
        except Exception as exc:
            error_message = str(exc)
            errors.append(error_message)
            _write_log(
                log_path,
                "execution_error",
                {"question": question, "attempt": attempts, "sql": current_sql, "error": error_message},
            )
            if attempts > max_retries:
                return _failure_response(
                    question,
                    current_sql,
                    errors,
                    "All retry attempts failed.",
                    attempts,
                    retry_needed,
                    log_path,
                    decomposition,
                )

            repaired = repair_sql(current_sql, error_message)
            if repaired == current_sql:
                return _failure_response(
                    question,
                    current_sql,
                    errors,
                    "No automatic repair rule matched the database error.",
                    attempts,
                    retry_needed,
                    log_path,
                    decomposition,
                )
            current_sql = repaired
            retry_needed = True
            _write_log(log_path, "sql_retry", {"question": question, "attempt": attempts + 1, "sql": current_sql})

    return _failure_response(question, current_sql, errors, "Unexpected retry loop exit.", attempts, retry_needed, log_path)


def _failure_response(
    question: str,
    sql: str,
    errors: list[str],
    message: str,
    attempts: int,
    retry_needed: bool,
    log_path: str | Path | None,
    decomposition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "question": question,
        "decomposition": decomposition or {},
        "sql": sql,
        "result": [],
        "row_count": 0,
        "columns": [],
        "summary": "I could not produce a safe successful SQL answer for this question.",
        "status": "failed",
        "attempts": attempts,
        "retry_needed": retry_needed,
        "errors": errors + [message],
        "execution_time_ms": 0,
    }
    _write_log(log_path, "agent_failed", response)
    return response


def _write_log(log_path: str | Path | None, event: str, payload: dict[str, Any]) -> None:
    if log_path is None:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(UTC).isoformat(timespec="seconds"), "event": event, **payload}
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(_json_safe(record), ensure_ascii=True) + "\n")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value
