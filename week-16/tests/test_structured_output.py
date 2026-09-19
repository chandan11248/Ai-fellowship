"""
Tests for Structured Output and JSON Validation.
"""

import pytest
from src.assistant.structured_output import (
    SupportResolution,
    IntentClassification,
    extract_json_block,
    repair_and_parse_json,
    parse_structured_output,
    generate_json_schema_prompt
)


def test_extract_json_block_fenced():
    raw = "Here is the response:\n```json\n{\"category\": \"ORDER\", \"confidence\": 0.9}\n```\nHope that helps!"
    extracted = extract_json_block(raw)
    assert extracted == '{"category": "ORDER", "confidence": 0.9}'


def test_repair_trailing_commas():
    malformed = '{"category": "ORDER", "confidence": 0.9,}'
    parsed = repair_and_parse_json(malformed)
    assert parsed["category"] == "ORDER"
    assert parsed["confidence"] == 0.9


def test_parse_structured_output_support_resolution():
    raw_json = """
    {
        "category": "REFUND",
        "status": "RESOLVED",
        "summary": "Customer approved for return.",
        "direct_response": "We have processed your request.",
        "tool_calls_executed": ["calculate_refund"],
        "refund_amount": 149.99,
        "action_items": ["Send return label"],
        "confidence": 0.95,
        "citations": ["Return Policy"]
    }
    """
    obj = parse_structured_output(raw_json, SupportResolution)
    assert isinstance(obj, SupportResolution)
    assert obj.category == "REFUND"
    assert obj.refund_amount == 149.99
    assert obj.confidence == 0.95


def test_parse_structured_output_intent_classification():
    raw_json = """
    {
        "intent": "SHIPPING",
        "confidence": 0.99,
        "entities": {"tracking_num": "TRK-123"},
        "urgency": "HIGH",
        "reasoning": "User inquired about carrier delivery delay."
    }
    """
    obj = parse_structured_output(raw_json, IntentClassification)
    assert isinstance(obj, IntentClassification)
    assert obj.intent == "SHIPPING"
    assert obj.urgency == "HIGH"


def test_generate_json_schema_prompt():
    prompt = generate_json_schema_prompt(SupportResolution)
    assert "JSON Schema" in prompt
    assert "SupportResolution" in prompt or "direct_response" in prompt
