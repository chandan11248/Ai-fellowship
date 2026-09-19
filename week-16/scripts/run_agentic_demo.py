"""
Interactive & Scripted CLI Demo for ShopAssist AI Agentic Loop.
Demonstrates:
1. Multi-source resolution (order lookup + warranty policy + inventory verification).
2. Progressive disclosure of procedural skills on demand.
3. Compacted external notes (Evidence Dossier).
4. Independent Policy Auditor validation.
5. Injected failure handling resilience.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agentic.multi_agent import MultiAgentSystem
from src.assistant.tool_registry import registry


def run_demo():
    print("================================================================")
    print("      SHOPASSIST AI: AGENTIC MULTI-SPECIALIST DEMO (WEEK 16)    ")
    print("================================================================\n")

    agent_system = MultiAgentSystem()

    queries = [
        (
            "Scenario 1: Cross-Source Warranty Verification & Full Refund",
            "I received order ORD-1001 four days ago, but the headphones arrived damaged and broken. Can I get a full refund?"
        ),
        (
            "Scenario 2: Cross-SKU Exchange with Warehouse Stock Verification",
            "I want to exchange my order ORD-1002 for SKU-KEYBOARD-PRO. Is it available in your warehouse and how does the exchange work?"
        ),
        (
            "Scenario 3: Ambiguous Inquiry Prompting User Clarification",
            "I need to return my item for a refund immediately, please process the return label."
        ),
        (
            "Scenario 4: Carrier API Outage (Failure Injection Resilience)",
            "Please check live carrier tracking for my order ORD-1001 with tracking TRK-987654321 right now."
        )
    ]

    for title, query in queries:
        print(f"\n----------------------------------------------------------------")
        print(f"[*] {title}")
        print(f"[*] Customer Query: \"{query}\"")
        print(f"----------------------------------------------------------------")

        if "Failure Injection" in title:
            print("[!] Injecting HTTP 503 Outage into carrier tracking tool...")
            registry.inject_failure("track_shipping_package", "unavailable")
        else:
            registry.clear_failures()

        trace = agent_system.run(query)

        # Clear injected failure
        registry.clear_failures()

        print(f"[>] Status: {trace.resolution_status}")
        print(f"[>] Iterations Taken: {trace.iterations_taken}")
        print(f"[>] Tools Called: {[t['tool'] for t in trace.tools_executed]}")
        print(f"[>] Skills Loaded: {trace.skills_loaded}")
        print(f"[>] Total Tokens: {trace.total_tokens} (Prompt: {trace.prompt_tokens}, Completion: {trace.completion_tokens})")
        if trace.auditor_report:
            print(f"[>] Auditor Verification: {'PASSED' if trace.auditor_report.verified else 'FAILED'} (Confidence: {trace.auditor_report.confidence_score})")
            if trace.auditor_report.passed_checks:
                print(f"    Checks Passed: {trace.auditor_report.passed_checks}")

        print(f"\n[>] Compacted Evidence Dossier Injected into Coordinator Context:")
        print(trace.dossier.render_compact_context())

        print(f"\n[>] Final Customer-Facing Response:")
        print(trace.final_response)


if __name__ == "__main__":
    run_demo()
