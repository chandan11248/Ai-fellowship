"""
Main Assistant Agent orchestrator.
Coordinates user requests, RAG retrieval context injection, multi-step tool execution loops,
parameter configurations, and structured output formatting.
"""

import json
import time
from typing import List, Dict, Any, Optional, Type, TypeVar, AsyncIterator, Tuple
from pydantic import BaseModel

from src.assistant.llm_client import BaseLLMClient, LLMResponse, get_llm_client
from src.assistant.prompt_templates import (
    GenerationParameters,
    PARAMETER_PRESETS,
    build_system_prompt,
    format_rag_prompt
)
from src.assistant.tool_registry import registry, ToolRegistry
from src.assistant.structured_output import parse_structured_output, generate_json_schema_prompt

T = TypeVar("T", bound=BaseModel)


class AgentExecutionResult(BaseModel):
    """Execution telemetry and final result from the assistant agent."""
    response: str
    tool_calls_executed: List[Dict[str, Any]] = []
    rag_sources: List[Dict[str, Any]] = []
    total_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    provider_used: str = "unknown"
    structured_data: Optional[Dict[str, Any]] = None


class AIAssistantAgent:
    """Enterprise AI Assistant with RAG and Tool-Calling capabilities."""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        rag_pipeline: Optional[Any] = None,
        system_persona: str = "support_assistant"
    ):
        self.client = llm_client or get_llm_client()
        self.tools = tool_registry or registry
        self.rag = rag_pipeline
        self.system_prompt = build_system_prompt(persona=system_persona)

    def run(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        params: Optional[GenerationParameters] = None,
        use_rag: bool = True,
        use_tools: bool = True,
        max_tool_iterations: int = 5,
    ) -> AgentExecutionResult:
        """
        Execute user query through the reasoning loop:
        1. Context enrichment via RAG (if enabled & available).
        2. Iterative tool execution loop.
        3. Synthesis of final grounded response.
        """
        start_t = time.perf_counter()
        tool_executions: List[Dict[str, Any]] = []
        rag_sources: List[Dict[str, Any]] = []
        gen_params = params or PARAMETER_PRESETS["balanced_assistant"]

        # Step 1: RAG context retrieval
        formatted_query = user_query
        if use_rag and self.rag:
            rag_docs = self.rag.retrieve(user_query)
            if rag_docs:
                rag_sources = [doc.to_dict() if hasattr(doc, "to_dict") else doc for doc in rag_docs]
                context_str = "\n---\n".join(d.get("content", str(d)) for d in rag_sources)
                formatted_query = format_rag_prompt(user_query, context_str)

        # Build initial messages
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": formatted_query})

        available_tools = self.tools.get_schemas() if use_tools else None
        llm_total_latency = 0.0
        prompt_tokens = 0
        completion_tokens = 0

        # Step 2: Multi-turn tool execution loop
        for _ in range(max_tool_iterations):
            resp: LLMResponse = self.client.generate(
                messages=messages,
                params=gen_params,
                tools=available_tools
            )
            llm_total_latency += resp.latency_ms
            prompt_tokens += resp.prompt_tokens
            completion_tokens += resp.completion_tokens

            # If no tool calls requested, we have our final text answer
            if not resp.tool_calls:
                total_latency = (time.perf_counter() - start_t) * 1000.0
                return AgentExecutionResult(
                    response=resp.content,
                    tool_calls_executed=tool_executions,
                    rag_sources=rag_sources,
                    total_latency_ms=total_latency,
                    llm_latency_ms=llm_total_latency,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    provider_used=resp.provider
                )

            # Record assistant tool call message
            messages.append({
                "role": "assistant",
                "content": resp.content or "",
                "tool_calls": resp.tool_calls
            })

            # Execute tool calls
            for call in resp.tool_calls:
                fn = call.get("function", {})
                tool_name = fn.get("name")
                raw_args = fn.get("arguments", "{}")
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

                result = self.tools.execute(tool_name, args)
                tool_executions.append({
                    "call_id": call.get("id"),
                    "tool": tool_name,
                    "arguments": args,
                    "result": result
                })

                # Append tool response message
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", "tool_1"),
                    "name": tool_name,
                    "content": json.dumps(result)
                })

        # Final fallback response if loop exhausts iterations
        total_latency = (time.perf_counter() - start_t) * 1000.0
        return AgentExecutionResult(
            response=messages[-1].get("content", "Completed processing."),
            tool_calls_executed=tool_executions,
            rag_sources=rag_sources,
            total_latency_ms=total_latency,
            llm_latency_ms=llm_total_latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            provider_used=self.client.provider
        )

    def run_structured(
        self,
        user_query: str,
        schema: Type[T],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_rag: bool = True,
    ) -> Tuple[T, AgentExecutionResult]:
        """
        Execute query and enforce valid structured JSON output matching a Pydantic schema.
        """
        schema_prompt = generate_json_schema_prompt(schema)
        augmented_query = f"{user_query}\n\n{schema_prompt}"

        # Use deterministic parameters for JSON mode
        strict_params = PARAMETER_PRESETS["strict_json"]
        result = self.run(
            user_query=augmented_query,
            conversation_history=conversation_history,
            params=strict_params,
            use_rag=use_rag,
            use_tools=True
        )

        structured_obj = parse_structured_output(result.response, schema)
        result.structured_data = structured_obj.model_dump()
        return structured_obj, result

    async def run_stream(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        params: Optional[GenerationParameters] = None,
    ) -> AsyncIterator[str]:
        """Stream token responses asynchronously."""
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_query})

        gen_params = params or PARAMETER_PRESETS["balanced_assistant"]
        async for token in self.client.generate_stream(messages, gen_params):
            yield token
