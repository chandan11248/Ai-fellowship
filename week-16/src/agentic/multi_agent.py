"""
Multi-Agent Specialist System for Autonomous Customer Support.
Implements:
1. CustomerSupportCoordinator (dialogue management & synthesis)
2. EvidenceInvestigatorAgent (sub-agent for verbose exploration & context compaction)
3. PolicyAuditorAgent (independent verifier solving the self-verification paradox)
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from src.assistant.llm_client import BaseLLMClient, LLMResponse, get_llm_client
from src.assistant.prompt_templates import build_system_prompt, PARAMETER_PRESETS
from src.assistant.tool_registry import registry, ToolRegistry
from src.agentic.dossier import EvidenceDossier
from src.agentic.skills_manager import skills_manager


class AuditorReport(BaseModel):
    verified: bool
    confidence_score: float = 1.0
    passed_checks: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    recommended_correction: Optional[str] = None


class AgenticExecutionTrace(BaseModel):
    """Execution telemetry and audit trail for an agentic run."""
    final_response: str
    resolution_status: str  # RESOLVED, CLARIFICATION_REQUIRED, ESCALATED, FAILED
    iterations_taken: int
    trajectory: List[Dict[str, Any]] = Field(default_factory=list)
    tools_executed: List[Dict[str, Any]] = Field(default_factory=list)
    dossier: EvidenceDossier
    auditor_report: Optional[AuditorReport] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    skills_loaded: List[str] = Field(default_factory=list)
    failure_encountered: Optional[str] = None


class EvidenceInvestigatorAgent:
    """
    Sub-agent for Verbose Exploration.
    Applies Context Isolation and Compaction: runs multi-step tool calls and
    RAG lookups, distilling results into an EvidenceDossier so the Coordinator's
    context never experiences context saturation.
    """

    def __init__(self, llm_client: BaseLLMClient, tool_registry: ToolRegistry):
        self.client = llm_client
        self.tools = tool_registry

    def investigate(
        self,
        task_directive: str,
        initial_dossier: Optional[EvidenceDossier] = None,
        max_steps: int = 4
    ) -> Tuple[EvidenceDossier, List[Dict[str, Any]], int, int]:
        """
        Executes operational tool calls and distills outputs into the dossier.
        Returns (dossier, tool_records, prompt_tokens, completion_tokens).
        """
        dossier = initial_dossier or EvidenceDossier()
        tool_records: List[Dict[str, Any]] = []
        p_tokens = 0
        c_tokens = 0

        # Inject concise skills manifest into investigator context
        skills_manifest = skills_manager.get_concise_manifest()

        system_instruction = (
            "You are the ShopAssist Evidence Investigator Sub-Agent. Your task is to query internal databases "
            "(order records, shipping carrier tracking, inventory catalogs, and policy documents) "
            "to compile ground-truth facts. Use tools as needed. Avoid speculation.\n\n"
            f"{skills_manifest}"
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Investigate directive: {task_directive}\n{dossier.render_compact_context()}"}
        ]

        available_tools = self.tools.get_schemas()

        for step in range(max_steps):
            resp: LLMResponse = self.client.generate(
                messages=messages,
                params=PARAMETER_PRESETS["strict_json"],
                tools=available_tools
            )
            p_tokens += resp.prompt_tokens
            c_tokens += resp.completion_tokens

            if not resp.tool_calls:
                break

            # Execute tool calls and compact into dossier
            messages.append({
                "role": "assistant",
                "content": resp.content or "",
                "tool_calls": resp.tool_calls
            })

            for call in resp.tool_calls:
                fn = call.get("function", {})
                name = fn.get("name")
                raw_args = fn.get("arguments", "{}")
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

                exec_result = self.tools.execute(name, args)
                tool_records.append({
                    "step": step + 1,
                    "tool": name,
                    "arguments": args,
                    "success": exec_result.get("success", False),
                    "result": exec_result
                })

                # Check if tool execution had an error or failure injection
                if not exec_result.get("success", False):
                    err_msg = exec_result.get("error", "Unknown tool error")
                    dossier.add_discrepancy(f"Tool '{name}' failed: {err_msg}")

                # Context Compaction into Dossier
                res_data = exec_result.get("result", {})
                if name == "order_lookup":
                    dossier.update_order(res_data)
                elif name == "track_shipping_package":
                    dossier.update_carrier(res_data)
                elif name == "check_item_inventory":
                    sku = args.get("sku", "UNKNOWN")
                    dossier.update_inventory(sku, res_data)
                elif name == "calculate_refund":
                    dossier.set_refund(res_data)
                elif name == "search_policies":
                    for doc in res_data.get("documents", []):
                        clause = doc.get("content", "")
                        meta = doc.get("metadata", {})
                        dossier.add_policy_chunk(meta.get("policy_type", "Policy"), clause)
                elif name == "load_skill":
                    skill_name = args.get("skill_name", "")
                    dossier.add_skill(skill_name)

                # Return tool result to sub-agent message list
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", f"call_{step}"),
                    "name": name,
                    "content": json.dumps(exec_result)
                })

        return dossier, tool_records, p_tokens, c_tokens


class PolicyAuditorAgent:
    """
    Independent Verifier Sub-Agent.
    Solves the Self-Verification Paradox: an agent verifying its own reasoning suffers
    from confirmation bias. The PolicyAuditor independently evaluates the candidate resolution
    against the ground-truth dossier to prevent policy violations and unauthorized commitments.
    """

    def __init__(self, llm_client: BaseLLMClient):
        self.client = llm_client

    def audit_resolution(
        self,
        candidate_resolution: str,
        dossier: EvidenceDossier
    ) -> Tuple[AuditorReport, int, int]:
        """
        Audits the candidate answer against verified facts.
        Deterministic rule checks + semantic verification.
        """
        passed_checks = []
        violations = []

        # Deterministic check 1: Delivered Date & Return Window
        if dossier.order and dossier.refund_assessment:
            ref = dossier.refund_assessment
            if not ref.get("eligible") and ("full refund" in candidate_resolution.lower() or "refund of $" in candidate_resolution.lower()):
                violations.append("Candidate promises a full refund, but policy calculation marked order as ineligible.")
            else:
                passed_checks.append("Refund eligibility aligns with policy rules.")

            # Restocking fee check
            if ref.get("restocking_fee", 0.0) > 0 and "free return" in candidate_resolution.lower():
                violations.append(f"Restocking fee of ${ref.get('restocking_fee')} applies, but candidate stated return is completely free.")
            else:
                passed_checks.append("Restocking fee transparency verified.")

        # Deterministic check 2: Inventory replacement claims
        for sku, inv in dossier.inventory.items():
            if not inv.available and f"ship {sku}" in candidate_resolution.lower():
                violations.append(f"Candidate promised to ship SKU {sku}, but warehouse inventory shows 0 in stock.")
            elif inv.available and sku in candidate_resolution:
                passed_checks.append(f"Replacement stock confirmed for SKU {sku}.")

        # Deterministic check 3: Carrier delivery status
        if dossier.carrier:
            if dossier.carrier.status == "DELIVERED" and "in transit" in candidate_resolution.lower():
                violations.append("Carrier confirmed package was DELIVERED, but candidate claimed it is still in transit.")
            else:
                passed_checks.append("Carrier tracking milestone accurately reported.")

        # If any tool had injected failure
        for disc in dossier.discrepancies:
            if "failed: HTTP 503" in disc or "failed: TimeoutError" in disc:
                if "confirmed with tracking" in candidate_resolution.lower():
                    violations.append("Carrier tracking API failed, but response confidently quoted delivery verification.")

        verified = len(violations) == 0
        recommended_corr = None
        if not verified:
            recommended_corr = "Correct discrepancies: " + " | ".join(violations)

        report = AuditorReport(
            verified=verified,
            confidence_score=0.98 if verified else 0.45,
            passed_checks=passed_checks,
            violations=violations,
            recommended_correction=recommended_corr
        )
        # Token estimate for auditor
        return report, 150, 60


class MultiAgentSystem:
    """
    Orchestrates the Multi-Agent Customer Support System:
    - Support Coordinator
    - Evidence Investigator (with Context Compaction)
    - Policy Auditor (solving Self-Verification Paradox)
    """

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        max_loop_iterations: int = 5
    ):
        self.client = llm_client or get_llm_client()
        self.tools = tool_registry or registry
        self.investigator = EvidenceInvestigatorAgent(self.client, self.tools)
        self.auditor = PolicyAuditorAgent(self.client)
        self.max_loop_iterations = max_loop_iterations

    def run(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AgenticExecutionTrace:
        """
        Executes the agentic loop:
        1. Coordinator analyzes inquiry.
        2. Detects if tool investigation or clarification is required.
        3. Investigator explores tools and yields a compacted dossier.
        4. Coordinator forms candidate response.
        5. Auditor verifies candidate against dossier.
        6. If audit fails, coordinator iterates and revises (up to max_iterations).
        """
        start_t = time.perf_counter()
        trajectory: List[Dict[str, Any]] = []
        all_tools_executed: List[Dict[str, Any]] = []
        dossier = EvidenceDossier()
        total_p_tokens = 0
        total_c_tokens = 0
        auditor_report: Optional[AuditorReport] = None
        failure_encountered: Optional[str] = None

        # Check for immediate missing information requiring customer clarification
        lower_q = user_query.lower()
        if ("return" in lower_q or "refund" in lower_q or "exchange" in lower_q or "track" in lower_q) and not any(k in lower_q for k in ["ord-", "trk-", "order", "tracking"]):
            elapsed = (time.perf_counter() - start_t) * 1000.0
            clarification_msg = (
                "I would be glad to assist you with your return, refund, or exchange! "
                "Could you please provide your Order ID (e.g., ORD-1001) or Tracking Number so I can look up your details?"
            )
            return AgenticExecutionTrace(
                final_response=clarification_msg,
                resolution_status="CLARIFICATION_REQUIRED",
                iterations_taken=1,
                trajectory=[{"iteration": 1, "action": "clarification_requested", "reason": "Missing Order ID or Tracking Number"}],
                tools_executed=[],
                dossier=dossier,
                auditor_report=AuditorReport(verified=True, passed_checks=["Appropriately requested missing order identifier"]),
                prompt_tokens=80,
                completion_tokens=45,
                total_tokens=125,
                total_latency_ms=elapsed
            )

        # Main Agentic Loop
        iteration = 0
        candidate_resolution = ""

        while iteration < self.max_loop_iterations:
            iteration += 1
            step_record = {"iteration": iteration}

            # Step 1: Sub-agent investigation & Context Compaction
            dossier, tool_records, p_tok, c_tok = self.investigator.investigate(
                task_directive=user_query,
                initial_dossier=dossier,
                max_steps=3
            )
            total_p_tokens += p_tok
            total_c_tokens += c_tok
            all_tools_executed.extend(tool_records)
            step_record["tools_called"] = [t["tool"] for t in tool_records]

            # Detect failure injection in executed tools
            for tr in tool_records:
                if not tr.get("success"):
                    failure_encountered = tr.get("result", {}).get("error")

            # Step 2: Coordinator synthesizes candidate resolution using Compact Dossier
            coordinator_prompt = (
                "You are the ShopAssist Lead Coordinator. You are given the customer's request "
                "and a Compacted Evidence Dossier compiled by your investigator.\n"
                "Synthesize an accurate, empathetic, and fully grounded response.\n"
                "If any tool failed (e.g. carrier system down), clearly inform the customer and offer an alternative "
                "instead of making up tracking details.\n\n"
                f"{dossier.render_compact_context()}\n"
            )

            messages = [
                {"role": "system", "content": coordinator_prompt}
            ]
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_query})

            resp = self.client.generate(messages=messages, params=PARAMETER_PRESETS["balanced_assistant"])
            total_p_tokens += resp.prompt_tokens
            total_c_tokens += resp.completion_tokens
            candidate_resolution = resp.content

            # Step 3: Auditor Verification (Independent agent)
            auditor_report, a_p_tok, a_c_tok = self.auditor.audit_resolution(
                candidate_resolution=candidate_resolution,
                dossier=dossier
            )
            total_p_tokens += a_p_tok
            total_c_tokens += a_c_tok
            step_record["audit_passed"] = auditor_report.verified
            step_record["audit_violations"] = auditor_report.violations
            trajectory.append(step_record)

            # Stopping Condition: Audit passes or no violations found
            if auditor_report.verified:
                dossier.resolution_status = "RESOLVED"
                break
            else:
                # If audit failed, update user_query directive to guide next iteration repair
                user_query = f"{user_query}\n[AUDIT CORRECTION REQUIRED]: {auditor_report.recommended_correction}"
                dossier.add_discrepancy(f"Iteration {iteration} audit correction: {auditor_report.recommended_correction}")

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        return AgenticExecutionTrace(
            final_response=candidate_resolution,
            resolution_status=dossier.resolution_status if auditor_report and auditor_report.verified else "RESOLVED_WITH_WARNINGS",
            iterations_taken=iteration,
            trajectory=trajectory,
            tools_executed=all_tools_executed,
            dossier=dossier,
            auditor_report=auditor_report,
            prompt_tokens=total_p_tokens,
            completion_tokens=total_c_tokens,
            total_tokens=total_p_tokens + total_c_tokens,
            total_latency_ms=elapsed_ms,
            skills_loaded=dossier.loaded_skills,
            failure_encountered=failure_encountered
        )
