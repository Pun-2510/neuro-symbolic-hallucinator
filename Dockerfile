# =====================================================================
# Dockerfile — FastAPI backend
# Multi-stage build: dependencies → runtime
# =====================================================================

# Stage 1: Dependencies
FROM python:3.11-slim AS deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Cài system deps cho PyMuPDF + pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmupdf-dev \
        mupdf-tools \
        curl \
        libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache layer: install deps trước
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal runtime deps (cho editable install cần compile)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libsqlite3-0 \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pytest pytest-asyncio httpx

# Tạo non-root user cho security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash appuser && \
    mkdir -p /home/appuser && chown appuser:appgroup /home/appuser

WORKDIR /app

ENV HOME=/home/appuser
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/transformers

# Copy Python deps từ stage 1
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy system libs cần thiết (libmupdf, etc.)
COPY --from=deps /usr/lib/aarch64-linux-gnu/libmupdf* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libfreetype* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libjpeg* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libopenjp2* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libtiff* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libjbig* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libjpeg62* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libharfbuzz* /usr/lib/aarch64-linux-gnu/
COPY --from=deps /usr/lib/aarch64-linux-gnu/libglib* /usr/lib/aarch64-linux-gnu/

# Copy source
COPY --chown=appuser:appgroup pyproject.toml ./
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup configs/ ./configs/

# Install package in editable mode (để import integrity_checker hoạt động)
RUN pip install --no-cache-dir -e .

# Tạo data dirs với quyền appuser
RUN mkdir -p data/essays data/ground_truth data/cache && \
    chown -R appuser:appgroup data/

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "integrity_checker.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
