# Multi-Stage Dockerfile for ShopAssist AI Assistant
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    UI_PORT=8501

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application source code and data
COPY src/ ./src/
COPY data/ ./data/
COPY scripts/ ./scripts/

# Pre-seed RAG knowledge base and export ONNX models
RUN python scripts/seed_rag.py && \
    python scripts/export_onnx.py

EXPOSE 8000 8501

# Default startup command: FastAPI backend
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
