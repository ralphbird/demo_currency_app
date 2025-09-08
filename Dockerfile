# Single-service Dockerfile for Currency Conversion API
FROM python:3.12.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.1.3

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY currency_app/ ./currency_app/
COPY common/ ./common/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY README.md ./

# Install the application (including the current project)
RUN poetry install --only=main

# Create directories for data persistence
RUN mkdir -p /app/data /app/tests/databases

# Expose port (default 8000, can be overridden with API_PORT environment variable)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${API_PORT:-8000}/health || exit 1

# Run the API
CMD poetry run uvicorn currency_app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}
