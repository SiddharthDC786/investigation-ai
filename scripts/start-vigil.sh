#!/usr/bin/env bash
# Start Vigil full stack: PostgreSQL (you start manually) + backend + frontend
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend-api/backend"
FRONTEND="$ROOT/frontend"

echo "=== Vigil full stack ==="
echo "1. Ensure Postgres.app is running with database: crime_network"
echo "2. Optional: cd $ROOT/backend-api && docker compose up -d neo4j"
echo "3. Backend  → http://localhost:8000"
echo "4. Frontend → http://localhost:5173"
echo ""

if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  echo "Created backend/.env — edit DATABASE_URL if needed"
fi

if [[ ! -f "$FRONTEND/.env" ]]; then
  echo 'VITE_API_BASE_URL=http://localhost:8000' > "$FRONTEND/.env"
  echo "Created frontend/.env"
fi

COMPOSE="$ROOT/backend-api/docker-compose.yml"
if command -v docker >/dev/null 2>&1 && [[ -f "$COMPOSE" ]]; then
  if docker compose -f "$COMPOSE" ps neo4j 2>/dev/null | grep -q "running"; then
    echo "Neo4j already running (graph fusion enabled)"
  else
    echo "Starting Neo4j for graph fusion (optional)..."
    docker compose -f "$COMPOSE" up -d neo4j 2>/dev/null || echo "Neo4j skip — demo works with PostgreSQL only"
  fi
fi

if [[ ! -d "$BACKEND/.venv" ]]; then
  echo "Creating backend virtualenv..."
  python3 -m venv "$BACKEND/.venv"
  "$BACKEND/.venv/bin/pip" install -q -r "$BACKEND/requirements.txt"
  "$BACKEND/.venv/bin/python" -m spacy download en_core_web_sm 2>/dev/null || true
fi

# Quick DB check
if ! "$BACKEND/.venv/bin/python" -c "
from sqlalchemy import create_engine, text
from app.config import settings
e = create_engine(settings.database_url)
with e.connect() as c:
    c.execute(text('SELECT 1'))
" 2>/dev/null; then
  echo "WARNING: Cannot connect to PostgreSQL. Start Postgres.app first."
fi

echo "Starting backend on :8000..."
cd "$BACKEND"
"$BACKEND/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 2
HEALTH=$(curl -sf http://localhost:8000/health || true)
if [[ -n "$HEALTH" ]]; then
  echo "Backend OK — $HEALTH"
else
  echo "Backend failed to start — check backend/.env DATABASE_URL"
  kill $BACKEND_PID 2>/dev/null || true
  exit 1
fi

echo "Starting frontend on :5173..."
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

cleanup() {
  echo "Stopping..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "Open http://localhost:5173"
echo "Login: INV-2847 / vigil2026  |  Supervisor: SUP-1001 / admin2026"
echo "Demo script: scripts/DEMO_TOMORROW.txt"
echo "Press Ctrl+C to stop both servers"
wait
