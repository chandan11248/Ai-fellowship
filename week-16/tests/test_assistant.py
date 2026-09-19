"""
Tests for LLM Client, Prompt Templates, and Agent Loop.
"""

import pytest
from src.assistant.prompt_templates import (
    GenerationParameters,
    PARAMETER_PRESETS,
    build_system_prompt,
    format_rag_prompt
)
from src.assistant.llm_client import MockLLMClient, get_llm_client
from src.assistant.agent import AIAssistantAgent


def test_generation_parameters():
    params = GenerationParameters(temperature=0.7, top_p=0.9, max_tokens=500)
    p_dict = params.to_dict()
    assert p_dict["temperature"] == 0.7
    assert p_dict["top_p"] == 0.9
    assert p_dict["max_tokens"] == 500


def test_parameter_presets():
    assert "strict_json" in PARAMETER_PRESETS
    assert PARAMETER_PRESETS["strict_json"].temperature == 0.0
    assert "creative_resolution" in PARAMETER_PRESETS
    assert PARAMETER_PRESETS["creative_resolution"].temperature > 0.5


def test_build_system_prompt():
    prompt = build_system_prompt(persona="support_assistant", custom_instructions="Test Instruction")
    assert "ShopAssist AI" in prompt
    assert "Test Instruction" in prompt
    assert "[Context Instructions]" in prompt


def test_mock_llm_client():
    client = MockLLMClient()
    messages = [{"role": "user", "content": "Hello"}]
    resp = client.generate(messages)
    assert resp.content is not None
    assert len(resp.content) > 0
    assert resp.provider == "mock"


def test_mock_llm_client_streaming():
    import asyncio
    client = MockLLMClient()
    messages = [{"role": "user", "content": "Hello"}]

    async def _test():
        tokens = []
        async for token in client.generate_stream(messages):
            tokens.append(token)
        return "".join(tokens)

    output = asyncio.run(_test())
    assert len(output) > 0
    assert "ShopAssist" in output


def test_agent_basic_run():
    agent = AIAssistantAgent()
    result = agent.run("Hello there!")
    assert result.response is not None
    assert result.total_latency_ms >= 0.0
    assert result.provider_used in ["mock", "custom", "openai", "gemini", "vllm"]
