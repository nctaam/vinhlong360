FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY agent/ ./agent/
COPY web/ ./web/

# Data directory for logs, memory, analytics
RUN mkdir -p agent/data data/memory

# Environment
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

EXPOSE 8360 8361

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8360/health || exit 1

# Default: run knowledge agent
CMD ["python", "agent/server.py"]
