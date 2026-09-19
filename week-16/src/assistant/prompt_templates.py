"""
Prompt templates and generation parameter configurations for the assistant.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class GenerationParameters:
    """Hyperparameters for LLM generation."""
    temperature: float = 0.2
    top_p: float = 0.95
    max_tokens: int = 1024
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop_sequences: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "stop": self.stop_sequences if self.stop_sequences else None,
        }


# Presets for different task requirements
PARAMETER_PRESETS: Dict[str, GenerationParameters] = {
    "deterministic_factual": GenerationParameters(temperature=0.0, top_p=0.9, max_tokens=1024),
    "balanced_assistant": GenerationParameters(temperature=0.2, top_p=0.95, max_tokens=1024),
    "creative_resolution": GenerationParameters(temperature=0.7, top_p=0.98, max_tokens=1500),
    "strict_json": GenerationParameters(temperature=0.0, top_p=0.8, max_tokens=800),
}


SYSTEM_PROMPTS = {
    "support_assistant": (
        "You are ShopAssist AI, an AI assistant capable of answering questions from uploaded reference documents "
        "(PDFs, policies, articles) as well as helping customers with order status, returns, and support queries.\n\n"
        "Instructions:\n"
        "1. When reference context is provided, ground your answer directly in the document content.\n"
        "2. If an order lookup or tracking check is needed, make the corresponding tool call.\n"
        "3. Keep your answers clear, accurate, structured, and helpful.\n"
        "4. If details like order ID are missing when requested, ask the user to provide them."
    ),
    "rag_augmented": (
        "You are an assistant answering questions using reference documents.\n"
        "Use the retrieved context below to answer the user query.\n"
        "If the answer is not in the context, say that the information is not available."
    ),
    "structured_extractor": (
        "You are a structured data extractor. "
        "Return only valid JSON matching the requested schema without any markdown formatting or extra text."
    )
}


def build_system_prompt(
    persona: str = "support_assistant",
    include_rag_instructions: bool = True,
    include_tool_instructions: bool = True,
    custom_instructions: Optional[str] = None
) -> str:
    """Combines base persona prompt with task instructions."""
    base = SYSTEM_PROMPTS.get(persona, SYSTEM_PROMPTS["support_assistant"])
    parts = [base]

    if include_rag_instructions:
        parts.append(
            "\n[Context Instructions]\n"
            "- Ground answers in the retrieved context.\n"
            "- Do not invent order numbers or policies."
        )

    if include_tool_instructions:
        parts.append(
            "\n[Tool Instructions]\n"
            "- Use registered tools for looking up orders, checking tracking, and calculating refunds."
        )

    if custom_instructions:
        parts.append(f"\n[Additional Instructions]\n{custom_instructions.strip()}")

    return "\n".join(parts)


def format_rag_prompt(query: str, retrieved_context: str) -> str:
    """Formats retrieved context into the user prompt."""
    return (
        f"Relevant Document / Knowledge Base Context:\n"
        f"\"\"\"\n{retrieved_context.strip()}\n\"\"\"\n\n"
        f"User Query:\n{query.strip()}\n\n"
        f"Please provide a comprehensive and accurate answer based on the context above:"
    )
