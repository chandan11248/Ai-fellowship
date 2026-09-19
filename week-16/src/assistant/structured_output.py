"""
Structured output schema validation and JSON generation engine.
Ensures responses strictly conform to Pydantic models with robust parsing,
markdown fence stripping, and fallback repair mechanisms.
"""

import json
import re
from typing import Type, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError


T = TypeVar("T", bound=BaseModel)


# Structured Domain Schemas
class IntentClassification(BaseModel):
    """Routing intent classification schema."""
    intent: str = Field(
        description="One of: ACCOUNT, CANCEL, CONTACT, DELIVERY, FEEDBACK, INVOICE, ORDER, PAYMENT, REFUND, SHIPPING, SUBSCRIPTION, GENERAL"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities like order_id, email, dates")
    urgency: str = Field(default="NORMAL", description="LOW, NORMAL, HIGH, or CRITICAL")
    reasoning: str = Field(description="Brief rationale for the classification")


class ToolCallSpec(BaseModel):
    """Specification for a single tool call."""
    tool_name: str = Field(description="The unique name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool function")


class SupportResolution(BaseModel):
    """Structured resolution object for customer inquiries."""
    category: str = Field(description="Primary category of the issue")
    status: str = Field(description="RESOLVED, IN_PROGRESS, ESCALATED, or PENDING_INFO")
    summary: str = Field(description="Concise summary of resolution")
    direct_response: str = Field(description="Customer-facing answer text")
    tool_calls_executed: List[str] = Field(default_factory=list, description="Names of tools triggered")
    refund_amount: Optional[float] = Field(default=None, description="Calculated refund amount if applicable")
    action_items: List[str] = Field(default_factory=list, description="Follow-up action items")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    citations: List[str] = Field(default_factory=list, description="Referenced KB section titles or docs")


class RAGRetrievalResult(BaseModel):
    """Structured result from RAG pipeline."""
    query: str
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    latency_ms: float = Field(default=0.0)


def extract_json_block(text: str) -> str:
    """
    Extracts raw JSON substring from model output, handling:
    - Markdown fenced blocks (```json ... ``` or ``` ... ```)
    - Leading/trailing conversational text
    """
    if not text:
        return ""

    text = text.strip()

    # Match markdown code block
    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()

    # Match balanced curly braces { ... } or brackets [ ... ]
    brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if brace_match:
        return brace_match.group(1).strip()

    return text


def repair_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Attempt parsing JSON, applying standard repair heuristics if needed:
    - Stripping trailing commas
    - Fixing single quotes to double quotes for standard keys
    """
    cleaned = extract_json_block(text)

    # 1. Direct standard parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2. Heuristic repair: remove trailing commas before closing braces
    fixed = re.sub(r",\s*([\]}])", r"\1", cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 3. Heuristic repair: replace single quotes on keys and simple strings
    single_quote_fixed = re.sub(r"(?<=\{|,)\s*'([^']+)'\s*:", r'"\1":', fixed)
    try:
        return json.loads(single_quote_fixed)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON from text: {text[:100]}... Error: {exc}") from exc


def parse_structured_output(raw_text: str, schema: Type[T]) -> T:
    """
    Parse and validate raw model output against a given Pydantic schema.
    Raises ValidationError or ValueError if invalid.
    """
    data = repair_and_parse_json(raw_text)
    return schema.model_validate(data)


def generate_json_schema_prompt(schema: Type[BaseModel]) -> str:
    """Generate a prompt instruction containing the JSON schema description."""
    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    return (
        f"Respond ONLY with a valid JSON object strictly complying with this JSON Schema:\n"
        f"```json\n{schema_json}\n```\n"
        f"Do not include any conversational preamble or postscript."
    )
