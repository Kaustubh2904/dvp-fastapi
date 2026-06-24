# ---------------------------------------------------------------------------
# Stage 1 — Builder
# Install dependencies and sync the virtual environment with uv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./

# Copy the full source so uv can install the project itself
COPY . .

# Install all production dependencies (no dev extras) into .venv
RUN uv sync --no-dev --frozen

# ---------------------------------------------------------------------------
# Stage 2 — Runtime
# Minimal image: only the venv, app code, and alembic artefacts
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Runtime system libraries required by psycopg (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --from=builder /app/app /app/app

# Copy Alembic migration artefacts
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

# Copy project metadata (used by some tooling)
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Expose the API port
EXPOSE 8000

# Environment — activate the venv and configure Python
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Default command: run the API server.
# docker-compose overrides this per-service (migrate, worker).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]