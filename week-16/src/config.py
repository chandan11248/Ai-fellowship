"""
Configuration management for Week 15 AI Assistant.
Centralizes environment variables, model parameters, reliability policies,
and vector database paths with Pydantic settings.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings and runtime parameters."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Config
    BASE_DIR: Path = BASE_DIR
    APP_NAME: str = "ShopAssist AI Assistant"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    UI_PORT: int = 8501

    # LLM Provider Configuration
    # Supported: "mock", "openai", "gemini", "anthropic", "vllm", "ollama", "custom"
    PRIMARY_PROVIDER: str = "mock"
    FALLBACK_PROVIDERS: List[str] = ["mock"]

    # API Keys & Endpoints
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"

    VLLM_ENDPOINT: str = "http://localhost:8000/v1"
    VLLM_MODEL: str = "meta-llama/Meta-Llama-3-8B-Instruct"

    # Custom OpenAI-compatible provider (any base URL + key)
    CUSTOM_BASE_URL: Optional[str] = None
    CUSTOM_API_KEY: Optional[str] = None
    CUSTOM_MODEL: str = "gpt-4o-mini"

    # Hyperparameters & Generation Tuning
    DEFAULT_TEMPERATURE: float = Field(default=0.2, ge=0.0, le=2.0)
    DEFAULT_TOP_P: float = Field(default=0.95, ge=0.0, le=1.0)
    DEFAULT_MAX_TOKENS: int = Field(default=1024, ge=1, le=8192)
    REQUEST_TIMEOUT_SECONDS: float = 15.0

    # RAG Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 3
    SIMILARITY_THRESHOLD: float = 0.35
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    DATA_DIR: Path = BASE_DIR / "data"
    DOCS_DIR: Path = BASE_DIR / "data" / "knowledge_base"
    VECTOR_STORE_PATH: Path = BASE_DIR / "data" / "vector_store"

    # Reliability & Production Controls
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    CIRCUIT_BREAKER_RECOVERY_TIME: float = 30.0

    # Caching
    ENABLE_RESPONSE_CACHE: bool = True
    CACHE_TTL_SECONDS: int = 300
    MAX_CACHE_ENTRIES: int = 1000

    # ONNX Optimization
    ONNX_MODEL_DIR: Path = BASE_DIR / "outputs" / "onnx_models"


settings = Settings()
