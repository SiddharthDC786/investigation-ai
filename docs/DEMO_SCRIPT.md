# Vigil — 3-Minute Demo Script (CASE0001)

**Login:** INV-2847 / vigil2026

| Time | Action | Say |
|------|--------|-----|
| 0:00 | Login, show Live badge | "Vigil fuses FIR, CDR, and bank data on one screen — server auth, not mock login." |
| 0:20 | Search **Rahul** + city **Hyderabad** | "Same name problem — we disambiguate suspects, witnesses, handlers." |
| 0:45 | Select **Rahul Mukherjee P00014** | "Matched person card — role and linked records." |
| 1:00 | Open **Connection Map** | "CDR-backed links; hover for call count and source record." |
| 1:20 | Open **Timeline** | "Only this person's events — calls, money, FIR mentions." |
| 1:35 | **Priority List** | "Investigation priority score — not probability of guilt." |
| 1:50 | Inspector → **FIR ingest** paste sample text → Preview → Upload | "Human reviews OCR before database write." |
| 2:10 | **Record Search (OSINT)** on suspect | "Simulated OSINT — labelled; no fake graph links added." |
| 2:25 | Confirm review button in inspector | "Officer review saved server-side — survives refresh." |
| 2:40 | **Action Log** + hash verified | "Tamper-evident chain for court disclosure." |
| 2:55 | Mention open stack + PS 26189 | "PostgreSQL, FastAPI, React — district-laptop deployable." |

## Sample FIR snippet (ingest)

```
FIR-042/2026 Cyber Cell Hyderabad. Complainant reports fraud by Rahul Mukherjee
contact 9876543210 and associate Sunil Patel. Amount transferred to account 1234567890.
```

## Refresh test

After saving a review, press F5 — review buttons should still show your decision.
