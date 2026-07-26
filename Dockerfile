# =====================================================================
# Dockerfile — FastAPI backend
# Multi-stage nhỏ gọn: build deps + runtime image
# =====================================================================

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Cài system deps cho PyMuPDF + pdfplumber (cần libmupdf, freetype)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmupdf-dev \
        mupdf-tools \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache layer: install deps trước
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY pyproject.toml ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/
COPY .env.example .env

# Khởi tạo data dirs
RUN mkdir -p data/essays data/ground_truth data/cache

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "integrity_checker.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
