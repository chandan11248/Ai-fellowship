"""
CLI demonstration script showing full assistant capabilities:
Tool calling, RAG knowledge retrieval, Structured JSON output, and Fallback resilience.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import json
from src.config import settings
from src.assistant.agent import AIAssistantAgent
from src.assistant.structured_output import SupportResolution, IntentClassification
from src.rag.pipeline import RAGPipeline
from src.reliability.circuit_breaker import CircuitBreaker


def run_full_demo():
    print("=" * 70)
    print("      ShopAssist AI Assistant - End-to-End Execution Demo")
    print("=" * 70)

    # Initialize RAG Pipeline
    rag = RAGPipeline()
    if rag.store.count() == 0 and settings.DOCS_DIR.exists():
        rag.ingest_directory(settings.DOCS_DIR)

    agent = AIAssistantAgent(rag_pipeline=rag)
    outputs_log = []

    # -------------------------------------------------------------
    # Scenario 1: Tool Calling (Order Status Lookup)
    # -------------------------------------------------------------
    print("\n[Scenario 1: Tool Calling - Order Status Lookup]")
    q1 = "Hello, can you check the status and tracking for order ORD-1001?"
    print(f"User: \"{q1}\"")
    res1 = agent.run(q1, use_tools=True, use_rag=True)
    print(f"Assistant: {res1.response}")
    print(f"Tools Executed: {[t['tool'] for t in res1.tool_calls_executed]}")
    print(f"Latency: {res1.total_latency_ms:.2f} ms | Provider: {res1.provider_used}")
    outputs_log.append({
        "scenario": "Tool Calling - Order Lookup",
        "query": q1,
        "response": res1.response,
        "tools_executed": res1.tool_calls_executed,
        "latency_ms": res1.total_latency_ms
    })

    # -------------------------------------------------------------
    # Scenario 2: RAG Grounded Retrieval (Store Policy)
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("[Scenario 2: RAG Retrieval - Knowledge Base Policy Grounding]")
    q2 = "What happens if I return an opened item after 20 days?"
    print(f"User: \"{q2}\"")
    res2 = agent.run(q2, use_tools=False, use_rag=True)
    print(f"Assistant: {res2.response}")
    print(f"RAG Chunks Retrieved: {len(res2.rag_sources)}")
    for s in res2.rag_sources:
        print(f"  - Source: {s.get('chunk_id')} (score: {s.get('score', 0):.4f})")
    print(f"Latency: {res2.total_latency_ms:.2f} ms")
    outputs_log.append({
        "scenario": "RAG Retrieval - Store Policy",
        "query": q2,
        "response": res2.response,
        "rag_sources": res2.rag_sources,
        "latency_ms": res2.total_latency_ms
    })

    # -------------------------------------------------------------
    # Scenario 3: Structured JSON Output Enforcement
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("[Scenario 3: Structured Output Enforcement - Pydantic JSON Mode]")
    q3 = "Customer wants to return order ORD-1001 because the sound cuts out."
    print(f"User: \"{q3}\"")
    struct_obj, res3 = agent.run_structured(q3, schema=SupportResolution, use_rag=True)
    print(f"Parsed Pydantic JSON Output:\n{json.dumps(struct_obj.model_dump(), indent=2)}")
    print(f"Category: {struct_obj.category} | Confidence: {struct_obj.confidence}")
    outputs_log.append({
        "scenario": "Structured JSON Resolution",
        "query": q3,
        "parsed_json": struct_obj.model_dump(),
        "latency_ms": res3.total_latency_ms
    })

    # -------------------------------------------------------------
    # Scenario 4: Circuit Breaker & Graceful Degradation
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("[Scenario 4: Reliability - Circuit Breaker Tripping & Degradation]")
    cb = CircuitBreaker(name="demo_circuit", failure_threshold=2, recovery_timeout=2.0)

    def failing_upstream_service():
        raise ConnectionError("Upstream LLM API timed out (HTTP 504 Gateway Timeout)")

    # Trigger failures to trip circuit breaker
    print("Simulating consecutive upstream service failures...")
    for i in range(3):
        out = cb.call(failing_upstream_service)
        print(f"  Call {i+1} result: \"{out[:80]}...\" (Circuit State: {cb.state.value})")

    outputs_log.append({
        "scenario": "Circuit Breaker Tripping",
        "circuit_state": cb.state.value,
        "degradation_response": cb.default_degradation_response()
    })

    # Save to outputs
    out_file = settings.BASE_DIR / "outputs" / "sample_run_outputs.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(outputs_log, f, indent=2)
    print(f"\n[Saved Output] Full execution log saved to: {out_file}")
    print("=" * 70)


if __name__ == "__main__":
    run_full_demo()
