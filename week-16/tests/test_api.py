"""
Tests for FastAPI endpoints and middleware.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "circuit_breaker_state" in data


def test_chat_endpoint_basic():
    payload = {
        "message": "Hello, can you help me with an order?",
        "use_rag": False,
        "use_tools": False
    }
    response = client.post("/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["latency_ms"] >= 0


def test_chat_endpoint_tool_calling():
    payload = {
        "message": "Check the status of order ORD-1001",
        "use_rag": True,
        "use_tools": True
    }
    response = client.post("/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["tool_calls_executed"]) > 0


def test_chat_endpoint_structured_json():
    payload = {
        "message": "Customer wants to return order ORD-1001 because it was broken.",
        "enforce_json": True,
        "structured_schema_type": "SupportResolution"
    }
    response = client.post("/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["structured_data"] is not None
    assert "category" in data["structured_data"]


def test_tool_execute_endpoint():
    payload = {
        "tool_name": "order_lookup",
        "arguments": {"order_id": "ORD-1001"}
    }
    response = client.post("/v1/tools/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"]["found"] is True


def test_rag_ingest_and_query_endpoints():
    ingest_payload = {
        "doc_id": "api_test_doc",
        "content": "Special VIP customers receive express 1-day delivery for free.",
        "metadata": {"source": "vip_policy"}
    }
    r_ingest = client.post("/v1/rag/ingest", json=ingest_payload)
    assert r_ingest.status_code == 200
    assert r_ingest.json()["success"] is True

    query_payload = {
        "query": "VIP free express delivery",
        "top_k": 2
    }
    r_query = client.post("/v1/rag/query", json=query_payload)
    assert r_query.status_code == 200
    results = r_query.json()["results"]
    assert len(results) >= 1
    assert "VIP" in results[0]["content"]


def test_onnx_classify_endpoint():
    payload = {"text": "I need a refund for my order."}
    response = client.post("/v1/classify/intent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert data["engine"] == "onnx_runtime"


def test_agentic_chat_endpoint():
    payload = {
        "message": "I received order ORD-1001 four days ago, but the headphones arrived damaged. Can I get a refund?"
    }
    response = client.post("/v1/agentic/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["resolution_status"] == "RESOLVED"
    assert "compacted_dossier" in data
    assert data["auditor_verified"] is True
    assert len(data["tools_executed"]) > 0

