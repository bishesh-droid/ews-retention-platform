# Meridian EWS Platform - Production Dockerfile
# Multi-stage build for minimal runtime image

# ---------------------------------------------------------------------------
# Stage 1: Dependencies
# ---------------------------------------------------------------------------
FROM python:3.12.8-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with retry logic for transient network errors
COPY requirements.txt .
RUN for i in 1 2 3; do pip install --no-cache-dir --user -r requirements.txt && break || sleep 15; done

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.12.8-slim-bookworm AS runtime

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY backend/ ./backend/
COPY requirements.txt .

# Create data directory for SQLite database
RUN mkdir -p /app/backend/data && \
    chown -R appuser:appgroup /app

# Set PATH to include user-installed packages
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# IMPORTANT: Run as single uvicorn worker — asyncio.Lock() used for ingestion
# serialisation is process-local. Multi-worker deployment requires Redis
# distributed lock (see ARCH-2 in audit). Do not add -w N without that fix.
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
