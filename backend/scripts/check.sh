#!/usr/bin/env bash
# One-stop quality gate for the backend: ruff (lint + format), pyright (types), pytest.
#
#   bash scripts/check.sh              # everything
#   bash scripts/check.sh --no-tests   # skip pytest (lint + types only, no Docker needed)
#
# Tests need Postgres + Redis; this brings them up via docker compose (host ports 5433/6379),
# applies migrations, then runs pytest against them.
set -euo pipefail

cd "$(dirname "$0")/.."            # -> backend/
ROOT="$(cd .. && pwd)"            # repo root (docker-compose.yml lives here)
VENV="$(pwd)/.venv/bin"

run_tests=1
[[ "${1:-}" == "--no-tests" ]] && run_tests=0

echo "▶ ruff (auto-fix + format)"
"$VENV/ruff" check --fix .
"$VENV/ruff" format .

echo "▶ pyright"
"$VENV/pyright"

if [[ "$run_tests" == "1" ]]; then
  echo "▶ pytest (bringing up Postgres + Redis)"
  docker compose -f "$ROOT/docker-compose.yml" up -d --wait postgres redis
  export DATABASE_URL="postgresql+asyncpg://parlaypal:parlaypal@localhost:5433/parlaypal"
  export REDIS_URL="redis://localhost:6379"
  "$VENV/alembic" upgrade head
  "$VENV/pytest" -q
else
  echo "▷ skipping pytest (--no-tests)"
fi

echo "✓ all checks passed"
