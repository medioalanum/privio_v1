#!/bin/sh
set -eu
uv run --frozen python -m scripts.migrate
exec uv run --frozen uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
