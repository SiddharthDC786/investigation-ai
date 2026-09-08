# Vigil — Smart India Hackathon PS 26189

Court-defensible criminal network investigation platform: PostgreSQL + Neo4j fusion, spaCy NER ingest, OSINT audit chain, explainability, and triage.

## Quick start (local — recommended for demo)

```bash
# 1. PostgreSQL with seeded crime_network (Postgres.app or existing DB)
cd backend-api/dataset && python import_to_db.py

# 2. Optional Neo4j graph fusion
cd backend-api && docker compose up -d neo4j

# 3. Backend (installs spaCy model once)
cd backend-api/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload --port 8000

# 4. Frontend
cd ../../frontend
echo 'VITE_API_BASE_URL=http://localhost:8000' > .env
npm install && npm run dev
```

Or one command from repo root: `./scripts/start-vigil.sh`

**Login:** `INV-2847` / `vigil2026` · Supervisor: `SUP-1001` / `admin2026`

## Docker full stack (PostgreSQL + Neo4j + backend)

```bash
cd backend-api
docker compose up -d --build          # postgres + neo4j + API on :8000
docker compose --profile seed up seed # first-time CSV load (optional)
```

Then point frontend `.env` at `http://localhost:8000`.

- Neo4j Browser: http://localhost:7474 (`neo4j` / `vigilneo4j2026`)
- Health: `curl http://localhost:8000/health` → postgres, neo4j, nlp engine

## Architecture

| Layer | Tech | Role |
|-------|------|------|
| Data | PostgreSQL | Case records, CDR, transactions, audit chain |
| Graph | Neo4j (optional) | Entity fusion, provenance, full-text search |
| NLP | spaCy `en_core_web_sm` + regex | FIR/surveillance entity extraction |
| Analytics | NetworkX | Timeline, centrality, communities, risk triage |
| OSINT | Lawful public lookups | Hash-chained audit for disclosure |
| UI | React + Vite | Investigator console with live ingest panel |

## Demo highlights for judges

1. **Search** — identity resolution (same name, FIR typo, alias)
2. **Network** — hidden prepaid bridge across suspects
3. **AI Ingest** (right panel) — paste FIR → spaCy preview → ingest to Neo4j
4. **Timeline / Risk** — fused CDR + financial events + composite scores
5. **OSINT** — enrichment with tamper-evident audit log
6. **Explain** — court-defensible reasoning per entity
7. **Audit export** — supervisor JSON disclosure bundle

See `backend-api/docs/DEMO_TOMORROW.txt` for the 5-minute script.

## API highlights

- `POST /ingest/preview` — NLP extraction without saving
- `POST /ingest/fir/text` — ingest FIR text with entity resolution
- `GET /health` — postgres + neo4j + nlp status
- `GET /explain/{entity_id}` · `GET /cases/{id}/analyze/risk-score` · `GET /osint/audit-log`

Full section docs: `backend-api/docs/SECTION{1-4}_*.md`
