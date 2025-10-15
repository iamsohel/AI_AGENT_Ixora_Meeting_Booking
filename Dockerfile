# Backend Dockerfile - Production Grade
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# Copy dependency files from backend
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code from backend
COPY --chown=appuser:appuser backend/agent/ ./agent/
COPY --chown=appuser:appuser backend/rag/ ./rag/
COPY --chown=appuser:appuser backend/database/ ./database/
COPY --chown=appuser:appuser backend/admin/ ./admin/
COPY --chown=appuser:appuser backend/utils/ ./utils/
COPY --chown=appuser:appuser backend/api.py backend/admin_api.py ./

# Install Playwright dependencies for browser automation
RUN uv run playwright install --with-deps chromium

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
