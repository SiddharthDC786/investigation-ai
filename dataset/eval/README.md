# Vigil evaluation fixtures (held-out from rule tuning)

Use `backend-api/dataset/eval/run_eval.py` to measure extraction and resolution quality.
Do not edit these rows to tune production rules.

| id | scenario | input | expected |
|----|----------|-------|----------|
| E01 | same_name_split | Rahul + Hyderabad vs Rahul + Mumbai | two distinct person_ids |
| E02 | fir_typo | Mukkherjee in FIR, Mukherjee in people | suggested_match or merge with alias |
| E03 | phone_corroboration | name + phone in FIR | auto-merge when phone matches case person |
| E04 | name_only | common name, no phone/city | suggested_match, requires_review |
| E05 | unrelated_org | OSINT registry city-only | no_match or zero relevance |
| E06 | hindi_token | शर्मा in FIR text | extracted or skipped honestly in English NER |
| E07 | case_isolation | search CASE0002 person from CASE0001 token | no spurious link |

Report precision/recall from script output — do not invent accuracy percentages.
