#!/bin/sh
set -eu
uv run --frozen --no-dev python -m scripts.migrate
exec uv run --frozen --no-dev uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
