#!/usr/bin/env bash
# Start Neo4j for Vigil graph fusion (requires Docker Desktop)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="$ROOT/backend-api/docker-compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed."
  echo ""
  echo "1. Download Docker Desktop for Mac:"
  echo "   https://www.docker.com/products/docker-desktop/"
  echo "2. Open Docker Desktop and wait until it says \"Running\""
  echo "3. Run this script again:"
  echo "   ./scripts/setup-neo4j.sh"
  exit 1
fi

echo "Starting Neo4j..."
docker compose -f "$COMPOSE" up -d neo4j

echo "Waiting for Neo4j (up to 60s)..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:7474 >/dev/null 2>&1; then
    echo ""
    echo "Neo4j is online."
    echo "  Browser: http://localhost:7474"
    echo "  Login:   neo4j / vigilneo4j2026"
    echo ""
    echo "Restart backend so the badge shows Neo4j fusion:"
    echo "  cd backend-api/backend && source .venv/bin/activate"
    echo "  uvicorn app.main:app --reload --port 8000"
    exit 0
  fi
  sleep 2
done

echo "Neo4j container started but not ready yet — wait 30s and refresh the website."
docker compose -f "$COMPOSE" ps neo4j
