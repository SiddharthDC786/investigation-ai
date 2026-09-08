# Section 1 — Palantir Gotham-style data fusion (SIH PS 26189)

## Start Neo4j

From `backend-api/`:

```bash
docker compose up -d neo4j
```

Browser: http://localhost:7474 (neo4j / vigilneo4j2026)

## Backend

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # optional; regex fallback if skipped
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

On startup the API syncs PostgreSQL → Neo4j and creates full-text indexes.

## Section 1 endpoints

| Route | Purpose |
|-------|---------|
| `POST /ingest/fir` | NER on FIR text → PostgreSQL + Neo4j MERGE |
| `POST /ingest/surveillance` | NER on surveillance reports |
| `POST /ingest/cdr` | Structured CDR CSV |
| `POST /ingest/transactions` | Transaction CSV |
| `GET /entities/{id}` | Entity with traceable `sources[]` |
| `GET /cases/{case_id}/search` | Cross-source search (Neo4j FTS + PG fallback) |

Form field `case_id` optional on ingest routes.

## Open-source stack

- **NER:** spaCy `en_core_web_sm` + regex (phones, accounts, names)
- **Graph:** Neo4j Community (self-hosted via Docker)
- **Provenance:** every entity links to `SourceDocument` via `MENTIONED_IN`
