from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .database import create_database
from .executor import execute_agent


class AgentRequest(BaseModel):
    question: str = Field(..., min_length=1)


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.database = _create_app_database()
    yield


app = FastAPI(title="Week 3 Mini SQL Agent", version="1.0.0", lifespan=lifespan)


@app.post("/agent/sql")
def agent_sql(request: AgentRequest) -> dict:
    log_path = Path(os.getenv("AGENT_LOG_PATH", Path(__file__).resolve().parents[1] / "logs" / "api_execution_logs.jsonl"))
    return execute_agent(
        request.question,
        _get_app_database(),
        max_retries=3,
        log_path=log_path,
    )


def _get_app_database():
    if not hasattr(app.state, "database"):
        app.state.database = _create_app_database()
    return app.state.database


def _create_app_database():
    seed_path = Path(os.getenv("SEED_SQL_PATH", Path(__file__).resolve().parents[1] / "seed.sql"))
    return create_database(seed_path)
