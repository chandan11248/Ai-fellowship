"""
Pydantic API Request & Response Schemas for FastAPI endpoints.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'system', 'user', 'assistant', or 'tool'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or prompt")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Previous turns in conversation")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)
    use_rag: bool = Field(default=True, description="Whether to query RAG vector store for context")
    use_tools: bool = Field(default=True, description="Whether to allow function calling")
    enforce_json: bool = Field(default=False, description="Whether to enforce structured JSON output")
    structured_schema_type: Optional[str] = Field(default=None, description="'SupportResolution' or 'IntentClassification'")


class ChatResponse(BaseModel):
    response: str
    tool_calls_executed: List[Dict[str, Any]] = []
    rag_sources: List[Dict[str, Any]] = []
    latency_ms: float
    provider_used: str
    tokens: Dict[str, int] = {}
    structured_data: Optional[Dict[str, Any]] = None
    cached: bool = False


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=10)
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    filter_metadata: Optional[Dict[str, Any]] = None


class RAGQueryResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_retrieved: int


class RAGIngestRequest(BaseModel):
    doc_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGIngestResponse(BaseModel):
    success: bool
    doc_id: str
    chunks_created: int
    message: str


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    success: bool
    tool_name: str
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str


class IntentClassifyRequest(BaseModel):
    text: str


class IntentClassifyResponse(BaseModel):
    text: str
    intent: str
    confidence: float
    probabilities: Dict[str, float]
    engine: str = "onnx_runtime"


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    primary_provider: str
    indexed_chunks: int
    onnx_loaded: bool


class MetricsResponse(BaseModel):
    uptime_seconds: float
    total_requests: int
    cache_hits: int
    cache_misses: int
    cache_hit_ratio_pct: float
    avg_latency_ms: float
    circuit_breaker_state: str
