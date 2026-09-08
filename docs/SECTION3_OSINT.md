# Section 3 — Social Links-style lawful OSINT

All enrichment uses **public synthetic datasets only** (organizations, FIR, locations). No scraping of private platforms.

## Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/osint/enrich` | POST | Run lawful lookup; link results into investigation graph |
| `/osint/audit-log` | GET | Hash-chained audit entries (`?case_id=CASE0001`) |
| `/audit/verify` | GET | Walk SHA-256 chain — returns `verified` or broken entry id |

## Lookup IDs

- `OSINT-01` — Public corporate registry (organizations table)
- `OSINT-02` — Published court bulletin (FIR public metadata)
- `OSINT-03` — Licensed address directory (locations + city)
- `OSINT-04` — Public sanctions/watchlist screening

## Example

```bash
curl -X POST http://localhost:8000/osint/enrich \
  -H 'Content-Type: application/json' \
  -d '{"case_id":"CASE0001","entity_id":"P00014","lookup_id":"OSINT-01","operator":"INV-2847","operator_name":"Officer"}'

curl 'http://localhost:8000/audit/verify?case_id=CASE0001'
```

Each audit entry: `entry_hash = SHA256(prev_hash + canonical JSON)`.
