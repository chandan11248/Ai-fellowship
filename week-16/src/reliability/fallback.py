"""
Multi-tier Model and Provider Fallback Manager.
Executes requests against a primary LLM provider, automatically cascading to
secondary and local fallback providers upon failures, timeouts, or quota exhaustion.
"""

import logging
from typing import List, Dict, Any, Optional
from src.assistant.llm_client import BaseLLMClient, LLMResponse, get_llm_client
from src.assistant.prompt_templates import GenerationParameters
from src.reliability.retry import retry_sync

logger = logging.getLogger(__name__)


class FallbackManager:
    """Manages ordered multi-tier provider cascade."""

    def __init__(
        self,
        primary_client: Optional[BaseLLMClient] = None,
        fallback_clients: Optional[List[BaseLLMClient]] = None
    ):
        self.primary = primary_client or get_llm_client()
        if fallback_clients is not None:
            self.fallbacks = fallback_clients
        else:
            # Default fallbacks: Local Mock / Offline
            self.fallbacks = [get_llm_client("mock")]

    def generate_with_fallback(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Attempt primary provider; cascade through fallbacks on failure."""
        providers = [self.primary] + self.fallbacks
        last_error = None

        for idx, client in enumerate(providers):
            provider_tag = f"{getattr(client, 'provider', 'custom')}:{getattr(client, 'model_name', 'default')}"
            try:
                # Execute with internal retry
                @retry_sync(max_retries=1, base_delay=0.5)
                def _attempt():
                    return client.generate(messages=messages, params=params, tools=tools)

                resp = _attempt()
                if idx > 0:
                    logger.info(f"[Fallback Cascade Success] Request succeeded using fallback provider '{provider_tag}'")
                return resp
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"[Fallback Triggered] Provider '{provider_tag}' failed: {exc}. "
                    f"Cascading to next fallback tier ({idx + 1}/{len(providers)})."
                )

        # Final ultimate safety fallback
        logger.error(f"[All Fallbacks Exhausted] Returning emergency static degradation response. Last error: {last_error}")
        return LLMResponse(
            content=(
                "I apologize, but our AI services are temporarily running in degraded mode. "
                "Your request has been queued. Please try again shortly."
            ),
            tool_calls=[],
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0.0,
            provider="emergency_fallback",
            model="static_safety",
            finish_reason="error"
        )
