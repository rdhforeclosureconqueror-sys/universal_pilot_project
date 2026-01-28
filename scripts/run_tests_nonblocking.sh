#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[tests] Running pytest inside Docker (non-blocking)..."
if pytest; then
  echo "[tests] Pytest completed successfully."
else
  status=$?
  echo "[tests] Pytest failed with status ${status}. Service will continue to run." >&2
  exit 0
fi
