"""
FastAPI application entrypoint for ShopAssist AI Assistant.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.routes import router, get_rag, get_onnx
from src.api.middleware import AppRateLimiterMiddleware, TimingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler: preload RAG database and ONNX models on startup."""
    # Preload RAG
    rag = get_rag()
    # Ingest default knowledge base if empty
    if rag.store.count() == 0 and settings.DOCS_DIR.exists():
        rag.ingest_directory(settings.DOCS_DIR)

    # Preload ONNX model
    _ = get_onnx()

    yield


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production AI Assistant with RAG, Tool Calling, ONNX Optimization, and Resilience Controls.",
        lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware
    app.add_middleware(TimingMiddleware)
    app.add_middleware(AppRateLimiterMiddleware, max_requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)

    # Routes
    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
