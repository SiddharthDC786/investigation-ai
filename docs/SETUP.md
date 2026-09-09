# Vigil — Reproducible Setup (Hackathon Demo)

**Problem statement:** README and codebase use **SIH PS 26189**. If your college brief says PS 28189, verify with organisers — do not assume without confirmation.

## Prerequisites

- Python 3.12+, Node.js 22+, PostgreSQL 16
- Optional: Docker (Neo4j)

## 1. Database

```bash
cd backend-api
psql -U postgres -c "CREATE DATABASE crime_network;"
psql -U postgres -d crime_network -f dataset/schema.sql
cd dataset && python import_to_db.py
psql -U postgres -d crime_network -f seed_demo_rahuls.sql   # optional disambiguation demo
```

## 2. Backend

```bash
cd backend-api/backend
cp .env.example .env
# Edit DATABASE_URL if needed
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload --port 8000
```

## 3. Frontend

```bash
cd frontend   # or backend-api/frontend after sync
cp .env.example .env
echo "VITE_API_BASE_URL=http://localhost:8000" >> .env
npm install
npm run dev
```

Open http://localhost:5173

## Demo accounts (server-enforced when `AUTH_ENABLED=true`)

| Badge | Password | Role | Case access |
|-------|----------|------|-------------|
| INV-2847 | vigil2026 | Investigator | CASE0001 |
| SUP-1001 | admin2026 | Supervisor | All cases |

## Verify

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"badge_id":"INV-2847","password":"vigil2026"}'
cd backend-api/backend && pytest -q
cd frontend && npm run build
```
