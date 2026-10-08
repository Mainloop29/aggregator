#!/usr/bin/env bash
set -euo pipefail

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

wait $API_PID