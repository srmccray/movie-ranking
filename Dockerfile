# =============================================================================
# Movie Ranking API - Dockerfile
# Multi-stage build for Python FastAPI application
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# Install dependencies in a separate stage to leverage layer caching
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies (only needed for compiling some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
# Dependencies are reinstalled only when requirements.txt changes
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# Minimal image with only runtime dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Install runtime dependencies only (libpq for psycopg/asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup alembic/ alembic/
COPY --chown=appuser:appgroup app/ app/

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check - verify the API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command: run uvicorn
# Use 0.0.0.0 to bind to all interfaces (required for Docker networking)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
