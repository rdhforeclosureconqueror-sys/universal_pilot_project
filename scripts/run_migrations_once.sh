#!/usr/bin/env bash
set -euo pipefail

cd /app

current_rev=$(alembic current 2>/dev/null | awk '{print $1}' | head -n1)
head_rev=$(alembic heads 2>/dev/null | awk '{print $1}' | head -n1)

if [ -z "$head_rev" ]; then
  echo "[migrations] No Alembic heads found; skipping."
  exit 0
fi

if [ "$current_rev" = "$head_rev" ]; then
  echo "[migrations] Database already at head (${head_rev}); skipping."
  exit 0
fi

echo "[migrations] Applying migrations: ${current_rev:-none} -> ${head_rev}"
alembic upgrade head
