# Section 2 — IBM i2 Analyst's Notebook-style analytics

Auto-generated link chart (existing `/cases/{case_id}/graph`) now includes PageRank/betweenness on each node.

## Endpoints

| Route | Purpose |
|-------|---------|
| `GET /cases/{case_id}/graph` | Link chart + auto centrality metadata on nodes |
| `GET /cases/{case_id}/timeline` | Chronological events from CDR, TXN, FIR, surveillance, chat |
| `GET /cases/{case_id}/analyze/centrality` | Betweenness + PageRank rankings (NetworkX) |
| `GET /cases/{case_id}/analyze/communities` | Louvain community detection (suspected rings) |

Centrality and communities **recompute automatically on ingest** (cache invalidated per case).

## Stack

- **NetworkX** — betweenness, PageRank, Louvain communities
- **PostgreSQL** — event sources for timeline
- No manual chart building — graph built from ingested + seeded data
