#!/usr/bin/env bash
set -e

echo "======================================"
echo " Running Quality & Type Checks"
echo "======================================"

echo ""
echo "1. Running Ruff Linter (ruff check)..."
uv run ruff check .

echo ""
echo "2. Running Ruff Formatter Check (ruff format --check)..."
uv run ruff format --check .

echo ""
echo "3. Running Astral ty Type Checker (ty check)..."
uv run ty check .

echo ""
echo " All checks passed successfully!"
