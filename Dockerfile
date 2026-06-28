# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps into a virtual env for clean copy
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runner ──────────────────────────────────────────
FROM python:3.12-slim AS runner

LABEL maintainer="vinhlong360 <loyennhi7723@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/vinhlong360/vl360-session-content"
LABEL org.opencontainers.image.description="vinhlong360 Knowledge Agent"

ARG BUILD_VERSION=dev
ARG BUILD_SHA=unknown
LABEL org.opencontainers.image.version="${BUILD_VERSION}"
LABEL org.opencontainers.image.revision="${BUILD_SHA}"

WORKDIR /app

# Runtime system deps only (no compiler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source
COPY agent/ ./agent/
COPY web/ ./web/

# Data directory for logs, memory, analytics
RUN mkdir -p agent/data data/memory

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/sh appuser && \
    chown -R appuser:appuser /app

USER appuser

# Environment
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

EXPOSE 8360 8361

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8360/health || exit 1

# Default: run knowledge agent
CMD ["python", "agent/server.py"]
