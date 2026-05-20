from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sqlite3
import threading
import time
from typing import Any, Protocol


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    execution_time_ms: float


class Database(Protocol):
    def execute(self, sql: str) -> QueryResult:
        ...


class SQLiteDatabase:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()

    @classmethod
    def from_seed(cls, seed_path: str | Path) -> "SQLiteDatabase":
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        database = cls(connection)
        database.load_seed(seed_path)
        return database

    def load_seed(self, seed_path: str | Path) -> None:
        seed_sql = Path(seed_path).read_text(encoding="utf-8")
        sqlite_sql = seed_sql.replace(" CASCADE", "")
        with self._lock:
            self.connection.executescript(sqlite_sql)
            self.connection.commit()

    def execute(self, sql: str) -> QueryResult:
        started = time.perf_counter()
        with self._lock:
            cursor = self.connection.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            columns = [description[0] for description in cursor.description or []]
        elapsed = (time.perf_counter() - started) * 1000
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=elapsed,
        )


class PostgresDatabase:
    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is required for PostgreSQL. Install dependencies with "
                "`python3 -m pip install -r requirements.txt`."
            ) from exc

        self._dict_row = dict_row
        self.connection = psycopg.connect(database_url)

    def execute(self, sql: str) -> QueryResult:
        started = time.perf_counter()
        with self.connection.cursor(row_factory=self._dict_row) as cursor:
            cursor.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            columns = [description.name for description in cursor.description or []]
        elapsed = (time.perf_counter() - started) * 1000
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=elapsed,
        )


def create_database(seed_path: str | Path | None = None) -> Database:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return PostgresDatabase(database_url)

    if seed_path is None:
        seed_path = Path(__file__).resolve().parents[1] / "seed.sql"
    return SQLiteDatabase.from_seed(seed_path)
