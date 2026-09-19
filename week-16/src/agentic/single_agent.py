"""
Single-Agent Loop Baseline.
Monolithic loop where a single agent conducts reasoning, tool calling, and response synthesis
within a single context window, without sub-agent context isolation or independent verification.
Serves as the empirical baseline for Token and Cost Accounting in the evaluation harness.
"""

import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.assistant.llm_client import BaseLLMClient, LLMResponse, get_llm_client
from src.assistant.prompt_templates import build_system_prompt, PARAMETER_PRESETS
from src.assistant.tool_registry import registry, ToolRegistry


class SingleAgentExecutionTrace(BaseModel):
    final_response: str
    iterations_taken: int
    tools_executed: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    failure_encountered: Optional[str] = None


class SingleAgentLoop:
    """
    Monolithic single-agent baseline.
    Executes tools directly in its conversational context until it produces a final answer.
    """

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        max_iterations: int = 5
    ):
        self.client = llm_client or get_llm_client()
        self.tools = tool_registry or registry
        self.max_iterations = max_iterations
        self.system_prompt = build_system_prompt(persona="support_assistant")

    def run(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> SingleAgentExecutionTrace:
        start_t = time.perf_counter()
        tools_executed: List[Dict[str, Any]] = []
        total_p_tokens = 0
        total_c_tokens = 0
        failure_encountered = None

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_query})

        available_tools = self.tools.get_schemas()
        iterations = 0

        for _ in range(self.max_iterations):
            iterations += 1
            resp: LLMResponse = self.client.generate(
                messages=messages,
                params=PARAMETER_PRESETS["balanced_assistant"],
                tools=available_tools
            )
            total_p_tokens += resp.prompt_tokens
            total_c_tokens += resp.completion_tokens

            if not resp.tool_calls:
                elapsed_ms = (time.perf_counter() - start_t) * 1000.0
                return SingleAgentExecutionTrace(
                    final_response=resp.content,
                    iterations_taken=iterations,
                    tools_executed=tools_executed,
                    prompt_tokens=total_p_tokens,
                    completion_tokens=total_c_tokens,
                    total_tokens=total_p_tokens + total_c_tokens,
                    total_latency_ms=elapsed_ms,
                    failure_encountered=failure_encountered
                )

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
                tools_executed.append({
                    "iteration": iterations,
                    "tool": name,
                    "arguments": args,
                    "result": exec_result
                })

                if not exec_result.get("success", False):
                    failure_encountered = exec_result.get("error")

                # Single agent stores the entire raw JSON payload in its context!
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", f"single_{iterations}"),
                    "name": name,
                    "content": json.dumps(exec_result)
                })

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        return SingleAgentExecutionTrace(
            final_response=messages[-1].get("content", "Completed processing."),
            iterations_taken=iterations,
            tools_executed=tools_executed,
            prompt_tokens=total_p_tokens,
            completion_tokens=total_c_tokens,
            total_tokens=total_p_tokens + total_c_tokens,
            total_latency_ms=elapsed_ms,
            failure_encountered=failure_encountered
        )
