# Section 4 — Vigil differentiator (court-defensible AI)

Structured template narratives — no external LLM — guaranteed **under 3 seconds** for live demo.

## Endpoints

| Route | Purpose |
|-------|---------|
| `GET /explain/{entity_id}?case_id=` | Plain-language flagged reasoning with source citations |
| `GET /cases/{case_id}/analyze/risk-score` | Composite triage score (centrality + role + case history) |
| `GET /case-summary/{case_id}` | Investigator briefing narrative |

## Example

```bash
curl 'http://localhost:8000/explain/P00014?case_id=CASE0001'
curl 'http://localhost:8000/cases/CASE0001/analyze/risk-score'
curl 'http://localhost:8000/case-summary/CASE0001'
```

Risk formula blends NetworkX PageRank/betweenness, inferred role weights, and CDR/TXN/FIR history.
