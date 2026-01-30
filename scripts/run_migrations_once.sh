#!/usr/bin/env bash
set -u

cd /app

current_rev=$(alembic current 2>/dev/null | awk '{print $1}' | head -n1 || true)
head_rev=$(alembic heads 2>/dev/null | awk '{print $1}' | head -n1 || true)

if [ -z "$head_rev" ]; then
  echo "[migrations] Unable to determine Alembic head; skipping migrations."
  exit 0
fi

if [ "$current_rev" = "$head_rev" ]; then
  echo "[migrations] Database already at head (${head_rev}); skipping."
  exit 0
fi

echo "[migrations] Applying migrations: ${current_rev:-none} -> ${head_rev}"
if ! alembic upgrade head; then
  echo "[migrations] Migration failed; continuing to start app." >&2
fi
