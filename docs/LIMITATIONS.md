# Vigil — Limitations & Feature Status

## Implemented (demo-ready)

- Person search with fuzzy names, filters, disambiguation
- CDR connection map with source evidence on links
- Person-filtered timeline
- Investigation priority list (not guilt probability)
- FIR OCR → review → ingest
- Server-side JWT auth with case access checks
- Officer review persistence (`/cases/{id}/reviews`)
- Hash-chained audit log per case (tamper **detection**, not tamper-proof)
- Leads generated from shared phones / CDR in case

## Simulated (clearly labelled in UI)

- OSINT enrichments (synthetic registry, bulletin, directory, watchlist)
- Face search — **demo stub** with `simulated: true` and `demo_similarity` score (not biometric probability)
- Synthetic dataset (Faker-generated — no real PII)

## NLP scope

- **English:** spaCy `en_core_web_sm` for FIR entity extraction
- **Hindi:** Devanagari name regex supplement (not full Indic NER model)
- UI is bilingual (English/Hindi); extracted FIR text is primarily English + Hindi names

## Evaluation

Run automated held-out metrics:

```bash
cd backend-api
python dataset/eval/run_eval.py
```

Produces `dataset/eval/eval_report.json` with NER precision/recall and resolution pass/fail counts.

## Planned (future scope)

- Government SSO / JWT from state identity systems
- Real OSINT API contracts
- Real biometrics integration
- Multilingual FIR NER beyond English/Hindi UI
- Mobile field app

## Honest claims

- Priority scores rank **investigation urgency** from graph centrality + role + case evidence.
- Entity resolution **never auto-merges on name alone** — requires corroborating phone or city within case scope.
- Audit chain detects edits to logged fields; a privileged DBA can still insert/delete rows outside the chain.

## PS number note

Repository README: **PS 26189**. Confirm with your college if they reference a different number (e.g. 28189).
