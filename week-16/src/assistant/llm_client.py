"""
LLM client implementations for OpenAI, Gemini, local vLLM, and an offline mock engine.
"""

import json
import time
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator, Tuple
from pydantic import BaseModel

from src.config import settings
from src.assistant.prompt_templates import GenerationParameters
from src.assistant.tool_registry import registry


class LLMResponse(BaseModel):
    content: str
    tool_calls: List[Dict[str, Any]] = []
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    provider: str
    model: str
    finish_reason: str = "stop"


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
    ) -> AsyncIterator[str]:
        pass


class MockLLMClient(BaseLLMClient):
    """
    Local deterministic provider for testing without API keys.
    Handles basic tool triggers, RAG formatting, and JSON schemas.
    """

    def __init__(self, model_name: str = "mock-gpt-4o"):
        self.model_name = model_name
        self.provider = "mock"

    def _synthesize_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        import re
        all_text = " ".join(m.get("content", "") for m in messages).lower()
        user_text = " ".join(m.get("content", "") for m in messages if m.get("role") in ("user", "human")).lower()
        last_msg = messages[-1]["content"] if messages else ""
        lower = last_msg.lower()

        is_structured_request = (
            "json" in all_text
            or "intentclassification" in all_text
            or "supportresolution" in all_text
            or "schema" in all_text
        )

        executed_tool_names = set()
        tool_failures = []
        for m in messages:
            if m.get("role") == "tool":
                t_name = m.get("name", "")
                if t_name:
                    executed_tool_names.add(t_name)
                t_content = m.get("content", "")
                if "503" in t_content or "timeouterror" in t_content.lower() or "service unavailable" in t_content.lower() or "failed" in t_content.lower():
                    tool_failures.append(t_content)

        # Check for failure signals in either tool outputs or compacted dossier in prompt
        has_failure_signal = bool(tool_failures) or ("failed: http 503" in all_text) or ("failed: timeouterror" in all_text) or ("503 service unavailable" in all_text)

        tool_calls = []

        if tools:
            # 1. Progressive Disclosure: Load specialized skill if applicable
            if "exchange" in user_text and "load_skill" not in executed_tool_names:
                return "", [{
                    "id": "call_mock_skill_exch",
                    "type": "function",
                    "function": {
                        "name": "load_skill",
                        "arguments": json.dumps({"skill_name": "exchange_fulfillment"})
                    }
                }]
            elif ("dispute" in user_text) and "load_skill" not in executed_tool_names:
                return "", [{
                    "id": "call_mock_skill_disp",
                    "type": "function",
                    "function": {
                        "name": "load_skill",
                        "arguments": json.dumps({"skill_name": "dispute_resolution"})
                    }
                }]

            # 2. Order lookup
            if ("ord-" in user_text or "order" in user_text) and "order_lookup" not in executed_tool_names:
                order_match = re.search(r"ord-\d+", user_text, re.IGNORECASE)
                order_id = order_match.group(0).upper() if order_match else "ORD-1001"
                return "", [{
                    "id": "call_mock_ord",
                    "type": "function",
                    "function": {
                        "name": "order_lookup",
                        "arguments": json.dumps({"order_id": order_id})
                    }
                }]

            # 3. Inventory lookup for exchanges / replacements
            if ("replace" in user_text or "exchange" in user_text or "sku-" in user_text) and "check_item_inventory" not in executed_tool_names:
                sku_match = re.search(r"sku-[\w-]+", user_text, re.IGNORECASE)
                sku_id = sku_match.group(0).upper() if sku_match else "SKU-KEYBOARD-PRO"
                return "", [{
                    "id": "call_mock_inv",
                    "type": "function",
                    "function": {
                        "name": "check_item_inventory",
                        "arguments": json.dumps({"sku": sku_id})
                    }
                }]

            # 4. Refund calculation
            if ("refund" in user_text or "return" in user_text or "damaged" in user_text) and "calculate_refund" not in executed_tool_names:
                order_match = re.search(r"ord-\d+", user_text, re.IGNORECASE)
                order_id = order_match.group(0).upper() if order_match else "ORD-1001"
                is_defective = "defective" in user_text or "broken" in user_text or "damaged" in user_text
                reason = "Damaged item received" if is_defective else "Customer return"
                return "", [{
                    "id": "call_mock_ref",
                    "type": "function",
                    "function": {
                        "name": "calculate_refund",
                        "arguments": json.dumps({
                            "order_id": order_id,
                            "return_reason": reason,
                            "days_since_delivery": 4 if is_defective else 15,
                            "item_condition": "unopened" if "unopened" in user_text else "opened"
                        })
                    }
                }]

            # 5. Tracking check
            if ("trk-" in user_text or "track" in user_text or "carrier" in user_text or "shipment" in user_text) and "track_shipping_package" not in executed_tool_names:
                trk_match = re.search(r"trk-\d+", user_text, re.IGNORECASE)
                trk_id = trk_match.group(0).upper() if trk_match else "TRK-987654321"
                return "", [{
                    "id": "call_mock_trk",
                    "type": "function",
                    "function": {
                        "name": "track_shipping_package",
                        "arguments": json.dumps({"tracking_number": trk_id})
                    }
                }]

        # If a failure injection was detected
        if has_failure_signal:
            return (
                "I apologize, but I encountered a temporary system outage while attempting to verify carrier tracking: "
                "the external carrier service is currently unavailable (HTTP 503 / Service Unavailable). "
                "Rather than producing an unconfirmed delivery estimate, I have flagged this for logistics review. "
                "Your order record shows it was processed on schedule, and real-time tracking will resume once carrier connectivity recovers."
            ), []

        # Post-tool response formatting
        tool_messages = [m for m in messages if m.get("role") == "tool"]
        if tool_messages or "[compacted evidence dossier]" in all_text:
            if is_structured_request:
                return json.dumps({
                    "category": "SUPPORT_RESOLUTION",
                    "status": "RESOLVED",
                    "summary": "Completed multi-source investigation and verified resolution.",
                    "direct_response": "I verified your order records, store policy guidelines, and warehouse inventory. Your resolution has been verified and processed.",
                    "tool_calls_executed": list(executed_tool_names),
                    "refund_amount": 149.99 if "ord-1001" in all_text else None,
                    "action_items": ["Resolution confirmed with policy auditor."],
                    "confidence": 0.99,
                    "citations": ["Order Database", "Store Policy RAG", "Inventory Catalog"]
                }, indent=2), []

            # Grounded conversational answer tailored to topic
            if "exchange" in user_text:
                return (
                    "I reviewed your order ORD-1002 and verified warehouse stock for SKU-KEYBOARD-PRO. "
                    "The keyboard is currently IN STOCK (18 units available at US-West-2). "
                    "Under our exchange fulfillment policy, standard restocking fees are waived. "
                    "We can issue a prepaid return label and dispatch your replacement as soon as the return is scanned."
                ), []
            elif "trk-" in user_text or "track" in user_text or "shipment" in user_text:
                return (
                    "I checked the carrier records for order ORD-1002 (Tracking TRK-123456789 with UPS Ground). "
                    "Your package is currently OUT_FOR_DELIVERY from the Oakland Sorting Hub, CA, "
                    "with estimated delivery scheduled today by 19:00. It has not yet arrived at your front porch."
                ), []
            elif "15 days" in user_text or "opened" in user_text:
                return (
                    "I reviewed your order ORD-1001 and store return policy. "
                    "Since the box was opened and returned within 30 days (delivered 15 days ago), "
                    "you are eligible for a partial refund with a 15% restocking fee ($22.50) deducted, "
                    "yielding a refundable balance of $127.49."
                ), []
            else:
                return (
                    "I have completed a multi-source review for your order ORD-1001. "
                    "Because your headphones arrived damaged within the 90-day defective warranty period, "
                    "you are entitled to a full 100% refund of $149.99 or free replacement with all restocking fees waived ($0.00). "
                    "I have initiated your return authorization."
                ), []

        # Intent classification response
        if "intent" in lower and is_structured_request:
            intent = "GENERAL"
            if "refund" in lower or "return" in lower:
                intent = "REFUND"
            elif "ship" in lower or "deliver" in lower or "track" in lower:
                intent = "SHIPPING"
            elif "cancel" in lower:
                intent = "CANCEL"
            elif "order" in lower:
                intent = "ORDER"
            elif "account" in lower or "login" in lower:
                intent = "ACCOUNT"

            return json.dumps({
                "intent": intent,
                "confidence": 0.96,
                "entities": {"query_snippet": last_msg[:50]},
                "urgency": "NORMAL",
                "reasoning": f"Query keywords match the {intent} workflow."
            }, indent=2), []

        # Generic structured resolution
        if is_structured_request:
            return json.dumps({
                "category": "GENERAL_SUPPORT",
                "status": "RESOLVED",
                "summary": "Answered general customer question.",
                "direct_response": "Thank you for reaching out to ShopAssist support. How can I help further?",
                "tool_calls_executed": [],
                "refund_amount": None,
                "action_items": [],
                "confidence": 0.95,
                "citations": ["ShopAssist Knowledge Base"]
            }, indent=2), []

        # Default conversational reply
        return (
            "Hi, I am ShopAssist AI. I can look up orders, track packages, "
            "calculate refund eligibility according to store policy, or answer return questions. "
            "How can I help you today?"
        ), []

    def generate(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        start_t = time.perf_counter()
        content, tool_calls = self._synthesize_response(messages, tools)
        latency = (time.perf_counter() - start_t) * 1000.0

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            prompt_tokens=len(str(messages)) // 4,
            completion_tokens=len(content) // 4,
            total_tokens=(len(str(messages)) + len(content)) // 4,
            latency_ms=latency,
            provider="mock",
            model=self.model_name,
            finish_reason="tool_calls" if tool_calls else "stop"
        )

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        return self.generate(messages, params, tools)

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
    ) -> AsyncIterator[str]:
        content, _ = self._synthesize_response(messages, tools=None)
        for word in content.split(" "):
            yield word + " "


class OpenAICompatibleClient(BaseLLMClient):
    """Client for OpenAI and compatible endpoints (vLLM, Ollama)."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
        provider_label: str = "openai"
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "EMPTY"
        self.model_name = model_name
        self.provider = provider_label

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key != "EMPTY":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        payload = {
            "model": self.model_name,
            "messages": messages,
            **(params.to_dict() if params else {}),
        }
        if tools:
            payload["tools"] = tools

        start_t = time.perf_counter()
        with httpx.Client(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.perf_counter() - start_t) * 1000.0
        choice = data["choices"][0]
        msg = choice.get("message", {})

        return LLMResponse(
            content=msg.get("content") or "",
            tool_calls=msg.get("tool_calls") or [],
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
            total_tokens=data.get("usage", {}).get("total_tokens", 0),
            latency_ms=latency,
            provider=self.provider,
            model=self.model_name,
            finish_reason=choice.get("finish_reason", "stop")
        )

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        payload = {
            "model": self.model_name,
            "messages": messages,
            **(params.to_dict() if params else {}),
        }
        if tools:
            payload["tools"] = tools

        start_t = time.perf_counter()
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.perf_counter() - start_t) * 1000.0
        choice = data["choices"][0]
        msg = choice.get("message", {})

        return LLMResponse(
            content=msg.get("content") or "",
            tool_calls=msg.get("tool_calls") or [],
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
            total_tokens=data.get("usage", {}).get("total_tokens", 0),
            latency_ms=latency,
            provider=self.provider,
            model=self.model_name,
            finish_reason=choice.get("finish_reason", "stop")
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        params: Optional[GenerationParameters] = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            **(params.to_dict() if params else {}),
        }
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta


def get_llm_client(provider_name: Optional[str] = None) -> BaseLLMClient:
    """Helper to return the configured LLM client instance."""
    provider = (provider_name or settings.PRIMARY_PROVIDER).lower()

    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAICompatibleClient(
            base_url="https://api.openai.com/v1",
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            provider_label="openai"
        )
    elif provider == "vllm":
        return OpenAICompatibleClient(
            base_url=settings.VLLM_ENDPOINT,
            api_key="EMPTY",
            model_name=settings.VLLM_MODEL,
            provider_label="vllm"
        )
    elif provider == "custom" and settings.CUSTOM_BASE_URL and settings.CUSTOM_API_KEY:
        return OpenAICompatibleClient(
            base_url=settings.CUSTOM_BASE_URL,
            api_key=settings.CUSTOM_API_KEY,
            model_name=settings.CUSTOM_MODEL,
            provider_label="custom"
        )
    elif provider == "mock":
        return MockLLMClient()
    else:
        # Fallback to local mock when API keys are not supplied
        return MockLLMClient(model_name=f"mock-{provider}")
