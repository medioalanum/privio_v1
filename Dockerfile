# Production Dockerfile for Privio Commitments Application
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation and copy mode for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

# Copy dependency definition files first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy application codebase
COPY app/ ./app/
COPY README.md ./

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default environment variables
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

# Run FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
