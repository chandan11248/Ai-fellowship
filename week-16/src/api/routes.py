"""
FastAPI route definitions for ShopAssist AI Assistant API.
"""

import time
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from src.config import settings
from src.assistant.agent import AIAssistantAgent
from src.assistant.prompt_templates import GenerationParameters
from src.assistant.tool_registry import registry
from src.assistant.structured_output import SupportResolution, IntentClassification
from src.rag.pipeline import RAGPipeline
from src.optimization.onnx_infer import ONNXIntentClassifier
from src.reliability.circuit_breaker import CircuitBreaker
from src.api.schemas import (
    ChatRequest, ChatResponse,
    RAGQueryRequest, RAGQueryResponse,
    RAGIngestRequest, RAGIngestResponse,
    ToolExecuteRequest, ToolExecuteResponse,
    IntentClassifyRequest, IntentClassifyResponse,
    HealthResponse, MetricsResponse
)
from src.api.middleware import response_cache

router = APIRouter()

# Service Singletons
_rag_pipeline: RAGPipeline = None
_onnx_classifier: ONNXIntentClassifier = None
_circuit_breaker = CircuitBreaker(
    name="api_llm_gateway",
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIME
)
_start_time = time.monotonic()
_total_requests = 0
_latencies = []


def get_rag() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline


def get_onnx() -> ONNXIntentClassifier:
    global _onnx_classifier
    if _onnx_classifier is None:
        _onnx_classifier = ONNXIntentClassifier()
    return _onnx_classifier


@router.post("/v1/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, rag: RAGPipeline = Depends(get_rag)):
    """
    Main conversational endpoint.
    Performs RAG context augmentation, executes tools if needed,
    enforces structured output if requested, with caching & reliability.
    """
    global _total_requests
    _total_requests += 1
    t0 = time.perf_counter()

    # Check cache if enabled
    cache_config = {
        "temperature": req.temperature,
        "use_rag": req.use_rag,
        "use_tools": req.use_tools,
        "enforce_json": req.enforce_json
    }
    if settings.ENABLE_RESPONSE_CACHE and not req.conversation_history:
        cached_val = response_cache.get(req.message, cache_config)
        if cached_val:
            cached_val["cached"] = True
            return ChatResponse(**cached_val)

    agent = AIAssistantAgent(rag_pipeline=rag if req.use_rag else None)

    gen_params = GenerationParameters(
        temperature=req.temperature if req.temperature is not None else settings.DEFAULT_TEMPERATURE,
        top_p=req.top_p if req.top_p is not None else settings.DEFAULT_TOP_P,
        max_tokens=req.max_tokens if req.max_tokens is not None else settings.DEFAULT_MAX_TOKENS,
    )

    try:
        if req.enforce_json:
            schema_cls = IntentClassification if req.structured_schema_type == "IntentClassification" else SupportResolution
            obj, result = agent.run_structured(
                user_query=req.message,
                schema=schema_cls,
                conversation_history=req.conversation_history,
                use_rag=req.use_rag
            )
            response_dict = {
                "response": result.response,
                "tool_calls_executed": result.tool_calls_executed,
                "rag_sources": result.rag_sources,
                "latency_ms": round(result.total_latency_ms, 2),
                "provider_used": result.provider_used,
                "tokens": {"prompt": result.prompt_tokens, "completion": result.completion_tokens},
                "structured_data": result.structured_data,
                "cached": False
            }
        else:
            result = agent.run(
                user_query=req.message,
                conversation_history=req.conversation_history,
                params=gen_params,
                use_rag=req.use_rag,
                use_tools=req.use_tools
            )
            response_dict = {
                "response": result.response,
                "tool_calls_executed": result.tool_calls_executed,
                "rag_sources": result.rag_sources,
                "latency_ms": round(result.total_latency_ms, 2),
                "provider_used": result.provider_used,
                "tokens": {"prompt": result.prompt_tokens, "completion": result.completion_tokens},
                "structured_data": None,
                "cached": False
            }

        _latencies.append(response_dict["latency_ms"])
        _circuit_breaker.record_success()

        # Cache response
        if settings.ENABLE_RESPONSE_CACHE and not req.conversation_history:
            response_cache.set(req.message, cache_config, response_dict)

        return ChatResponse(**response_dict)

    except Exception as exc:
        _circuit_breaker.record_failure()
        raise HTTPException(status_code=500, detail=f"Assistant execution error: {str(exc)}")


@router.post("/v1/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """Server-Sent Events (SSE) token streaming endpoint."""
    agent = AIAssistantAgent()
    gen_params = GenerationParameters(
        temperature=req.temperature if req.temperature is not None else settings.DEFAULT_TEMPERATURE,
        top_p=req.top_p if req.top_p is not None else settings.DEFAULT_TOP_P,
    )

    async def event_generator():
        try:
            async for token in agent.run_stream(req.message, req.conversation_history, gen_params):
                data = json.dumps({"token": token})
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/v1/rag/query", response_model=RAGQueryResponse)
async def rag_query_endpoint(req: RAGQueryRequest, rag: RAGPipeline = Depends(get_rag)):
    """Search knowledge base vector store directly."""
    results = rag.retrieve(
        query=req.query,
        top_k=req.top_k,
        similarity_threshold=req.similarity_threshold,
        metadata_filter=req.filter_metadata
    )
    return RAGQueryResponse(
        query=req.query,
        results=results,
        total_retrieved=len(results)
    )


@router.post("/v1/rag/ingest", response_model=RAGIngestResponse)
async def rag_ingest_endpoint(req: RAGIngestRequest, rag: RAGPipeline = Depends(get_rag)):
    """Ingest and vectorize a new document into knowledge base."""
    count = rag.ingest_text(doc_id=req.doc_id, content=req.content, metadata=req.metadata)
    return RAGIngestResponse(
        success=True,
        doc_id=req.doc_id,
        chunks_created=count,
        message=f"Successfully indexed document '{req.doc_id}' into {count} chunk(s)."
    )


@router.post("/v1/rag/clear")
async def rag_clear_endpoint(rag: RAGPipeline = Depends(get_rag)):
    """Clear all documents and vectors from knowledge base."""
    rag.clear()
    return {"success": True, "message": "Knowledge base cleared successfully."}


@router.get("/v1/rag/summary")
async def rag_summary_endpoint(rag: RAGPipeline = Depends(get_rag)):
    """Get list of indexed documents and chunk statistics."""
    return rag.get_stats()


@router.post("/v1/tools/execute", response_model=ToolExecuteResponse)
async def tool_execute_endpoint(req: ToolExecuteRequest):
    """Directly execute a registered backend tool."""
    res = registry.execute(req.tool_name, req.arguments)
    return ToolExecuteResponse(
        success=res.get("success", False),
        tool_name=req.tool_name,
        result=res.get("result"),
        error=res.get("error"),
        timestamp=res.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%SZ"))
    )


@router.post("/v1/classify/intent", response_model=IntentClassifyResponse)
async def classify_intent_endpoint(req: IntentClassifyRequest, onnx: ONNXIntentClassifier = Depends(get_onnx)):
    """Fast ONNX-accelerated customer support intent routing."""
    res = onnx.classify_text(req.text)
    return IntentClassifyResponse(
        text=req.text,
        intent=res["intent"],
        confidence=round(res["confidence"], 4),
        probabilities={k: round(v, 4) for k, v in res["probabilities"].items()},
        engine="onnx_runtime"
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(rag: RAGPipeline = Depends(get_rag)):
    """Service health inspection."""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        primary_provider=settings.PRIMARY_PROVIDER,
        indexed_chunks=rag.get_stats()["total_chunks_indexed"],
        onnx_loaded=True
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics_endpoint():
    """Operational and performance telemetry metrics."""
    uptime = time.monotonic() - _start_time
    cache_data = response_cache.stats()
    avg_lat = float(sum(_latencies) / len(_latencies)) if _latencies else 0.0

    return MetricsResponse(
        uptime_seconds=round(uptime, 1),
        total_requests=_total_requests,
        cache_hits=cache_data["hits"],
        cache_misses=cache_data["misses"],
        cache_hit_ratio_pct=cache_data["hit_ratio_pct"],
        avg_latency_ms=round(avg_lat, 2),
        circuit_breaker_state=_circuit_breaker.state.value
    )


# =========================================================================
# Week 16: Agentic Multi-Specialist Endpoint
# =========================================================================

from pydantic import BaseModel, Field
from typing import List, Optional


class AgenticChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None


class AgenticChatResponse(BaseModel):
    response: str
    resolution_status: str
    iterations_taken: int
    tools_executed: List[Dict[str, Any]]
    compacted_dossier: str
    auditor_verified: bool
    total_tokens: int
    latency_ms: float


@router.post("/v1/agentic/chat", response_model=AgenticChatResponse)
async def agentic_chat_endpoint(req: AgenticChatRequest):
    """
    Week 16 Autonomous Multi-Agent Specialist endpoint:
    Coordinator -> Evidence Investigator -> Compact Dossier -> Policy Auditor.
    """
    from src.agentic.multi_agent import MultiAgentSystem
    agent_sys = MultiAgentSystem()
    trace = agent_sys.run(req.message, req.conversation_history)
    return AgenticChatResponse(
        response=trace.final_response,
        resolution_status=trace.resolution_status,
        iterations_taken=trace.iterations_taken,
        tools_executed=trace.tools_executed,
        compacted_dossier=trace.dossier.render_compact_context(),
        auditor_verified=trace.auditor_report.verified if trace.auditor_report else True,
        total_tokens=trace.total_tokens,
        latency_ms=round(trace.total_latency_ms, 2)
    )

