#!/bin/sh
set -eu
uv run --frozen --no-dev python -m scripts.migrate
if [ "${DEMO_MODE:-false}" = "true" ]; then
    uv run --frozen --no-dev python -m scripts.demo
fi
exec uv run --frozen --no-dev uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
