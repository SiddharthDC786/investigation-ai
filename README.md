# investigation-ai

AI-Powered Criminal Network Analysis System (SIH PS 26189 — Vigil)

## Repository layout

| Folder | Contents |
|--------|----------|
| `backend/` | FastAPI API — search, graph, cases (PostgreSQL) |
| `frontend/` | React + Vite Vigil UI (Cytoscape graph, i18n) |
| `dataset/` | Schema, CSV data, `generate_dataset.py`, `import_to_db.py` |
| `docs/` | Solo setup notes |
| `ai/` | NLP / entity resolution (future) |

## Quick start (solo)

See `docs/SOLO_CONNECTED.txt`.

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Tech Stack

Frontend:
React + Vite + Tailwind + Cytoscape.js

Backend:
Python + FastAPI

Relational Database:
PostgreSQL

Graph Database:
Neo4j

AI/NLP:
Python + spaCy + Regex + RapidFuzz

Deployment/Integration:
Docker Compose
