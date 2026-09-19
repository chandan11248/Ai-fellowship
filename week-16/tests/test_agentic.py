"""
Comprehensive pytest test suite for Week 16 Agentic System.
Tests:
1. Evidence Dossier Context Compaction
2. Progressive Skills Disclosure
3. Multi-Agent Reasoning & Stopping Conditions
4. Independent Policy Auditor Checks
5. Failure Injection Resilience
6. Single-Agent Baseline
7. Built-From-Scratch Evaluation Harness
"""

import pytest
from src.agentic.dossier import EvidenceDossier
from src.agentic.skills_manager import skills_manager
from src.agentic.multi_agent import MultiAgentSystem, PolicyAuditorAgent
from src.agentic.single_agent import SingleAgentLoop
from src.assistant.tool_registry import registry
from src.assistant.llm_client import MockLLMClient
from src.evaluation.harness import EvaluationHarness, TestCase, BENCHMARK_CASES


@pytest.fixture
def mock_client():
    return MockLLMClient()


def test_evidence_dossier_compaction():
    dossier = EvidenceDossier()
    raw_order_data = {
        "found": True,
        "order": {
            "order_id": "ORD-1001",
            "customer_name": "Alice Johnson",
            "status": "DELIVERED",
            "order_date": "2026-08-20",
            "delivered_date": "2026-08-24",
            "items": [{"name": "Wireless Noise Cancelling Headphones", "qty": 1}],
            "total_amount": 149.99,
            "tracking_number": "TRK-987654321"
        }
    }
    dossier.update_order(raw_order_data)
    dossier.update_inventory("SKU-KEYBOARD-PRO", {"name": "Gaming Keyboard", "in_stock": 18, "available": True, "warehouse": "US-West-2"})
    dossier.set_refund({"eligible": True, "refund_type": "FULL_REFUND", "refund_amount": 149.99, "restocking_fee": 0.0})

    compact_str = dossier.render_compact_context()
    assert "[COMPACTED EVIDENCE DOSSIER]" in compact_str
    assert "ORD-1001" in compact_str
    assert "$149.99" in compact_str
    assert "SKU-KEYBOARD-PRO: IN STOCK" in compact_str
    assert "FULL_REFUND" in compact_str


def test_progressive_skills_disclosure():
    manifest = skills_manager.get_concise_manifest()
    assert "AVAILABLE PROCEDURAL SKILLS" in manifest
    assert "exchange_fulfillment" in manifest
    assert "dispute_resolution" in manifest

    # Load full instructions on demand
    loaded = skills_manager.load_skill("exchange_fulfillment")
    assert loaded["success"] is True
    assert "Exchange Fulfillment Procedure" in loaded["instructions"]
    assert "Inventory Verification" in loaded["instructions"]


def test_multi_agent_resolution_claim(mock_client):
    agent_system = MultiAgentSystem(llm_client=mock_client)
    query = "I received order ORD-1001 four days ago, but the headphones arrived damaged and broken. Can I get a full refund?"
    trace = agent_system.run(query)

    assert trace.resolution_status == "RESOLVED"
    assert trace.iterations_taken <= 5
    assert len(trace.tools_executed) >= 1
    assert trace.auditor_report is not None
    assert trace.auditor_report.verified is True
    assert trace.total_tokens > 0


def test_multi_agent_clarification_on_ambiguous_query(mock_client):
    agent_system = MultiAgentSystem(llm_client=mock_client)
    ambiguous_query = "I need to return my item for a refund immediately, please process it."
    trace = agent_system.run(ambiguous_query)

    assert trace.resolution_status == "CLARIFICATION_REQUIRED"
    assert "order id" in trace.final_response.lower() or "tracking" in trace.final_response.lower()
    assert len(trace.tools_executed) == 0


def test_policy_auditor_catches_violation(mock_client):
    auditor = PolicyAuditorAgent(llm_client=mock_client)
    dossier = EvidenceDossier()
    # Mock an ineligible refund assessment
    dossier.set_refund({
        "eligible": False,
        "refund_type": "NON_REFUNDABLE",
        "refund_amount": 0.0,
        "policy_note": "Return window exceeded 45 days."
    })
    raw_order_data = {
        "found": True,
        "order": {
            "order_id": "ORD-1001",
            "customer_name": "Test User",
            "status": "DELIVERED",
            "total_amount": 100.0,
            "items": []
        }
    }
    dossier.update_order(raw_order_data)

    # Erroneous candidate promising full refund
    flawed_candidate = "I have approved your request and issued a full refund of $100.00."
    report, p_tok, c_tok = auditor.audit_resolution(flawed_candidate, dossier)

    assert report.verified is False
    assert len(report.violations) > 0
    assert "ineligible" in report.violations[0].lower()


def test_failure_injection_resilience(mock_client):
    agent_system = MultiAgentSystem(llm_client=mock_client)
    registry.inject_failure("track_shipping_package", "unavailable")

    try:
        query = "Please check live carrier tracking for my order ORD-1001 with tracking TRK-987654321 right now."
        trace = agent_system.run(query)

        assert trace.resolution_status in ("RESOLVED", "RESOLVED_WITH_WARNINGS")
        # System recognizes failure and responds transparently
        assert any(term in trace.final_response.lower() for term in ["unavailable", "503", "outage", "logistics review", "cannot confirm", "temporary"])
    finally:
        registry.clear_failures()


def test_single_agent_loop_baseline(mock_client):
    single_loop = SingleAgentLoop(llm_client=mock_client, max_iterations=4)
    query = "Check the status of order ORD-1001 and calculate refund for opened item delivered 15 days ago."
    trace = single_loop.run(query)

    assert trace.final_response != ""
    assert trace.iterations_taken <= 4
    assert trace.total_tokens > 0


def test_evaluation_harness_suite(mock_client):
    harness = EvaluationHarness(llm_client=mock_client)
    # Run a 3-case subset for fast test execution
    subset = BENCHMARK_CASES[:3]
    summary = harness.run_suite(subset)

    assert summary.total_cases == 3
    assert summary.completed_cases == 3
    assert summary.completion_rate_pct == 100.0
    assert summary.failure_counts["hard_failure"] == 0
