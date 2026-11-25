# Multi-stage Dockerfile for FastAPI Backend

# Stage 1: Build virtual environment and install dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Production runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create unprivileged system group & user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Create persistent data directory for SQLite with proper ownership
RUN mkdir -p /data /app && chown -R appuser:appgroup /data /app

# Copy virtualenv from builder
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv

# Copy backend application code
COPY --chown=appuser:appgroup app ./app

# Switch to unprivileged user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
