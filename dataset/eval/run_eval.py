#!/usr/bin/env python3
"""Automated evaluation for NER extraction and entity resolution (held-out fixtures)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures.json"
FIXTURES_EXTRA = ROOT / "fixtures_extended.json"

sys.path.insert(0, str(ROOT.parent.parent / "backend"))
sys.path.insert(0, str(ROOT.parent.parent))


def _normalize(s: str) -> str:
    return " ".join(s.lower().split())


def eval_ner(text: str, expected_spans: list[str]) -> dict:
    from ai.ner_pipeline import extract_entities

    found = [e.text for e in extract_entities(text)]
    found_norm = {_normalize(x) for x in found}
    expected_norm = [_normalize(x) for x in expected_spans]

    tp = sum(1 for e in expected_norm if any(e in f or f in e for f in found_norm))
    fp = max(0, len(found_norm) - tp)
    fn = max(0, len(expected_norm) - tp)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    return {
        "found": found,
        "expected": expected_spans,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "passed": tp == len(expected_norm) and fn == 0,
    }


def eval_resolution(case_id: str, name: str, context_phones: list[str], fixture: dict) -> dict:
    from ai.ner_pipeline import ExtractedEntity
    from app.database import SessionLocal
    from app.services.entity_resolution import resolve_entity

    db = SessionLocal()
    try:
        mention = ExtractedEntity(
            text=name, entity_type="person", start=0, end=len(name), confidence=0.9
        )
        result = resolve_entity(db, case_id=case_id, mention=mention, context_phones=context_phones)
    finally:
        db.close()

    passed = True
    incorrect_merge = False
    if fixture.get("expect_action"):
        passed = result.action == fixture["expect_action"]
    if fixture.get("expect_action_in"):
        passed = result.action in fixture["expect_action_in"]
    if fixture.get("expect_requires_review"):
        passed = passed and result.requires_review is True
    if fixture.get("expect_not_auto_merge_without_phone") and not context_phones:
        if result.action == "merged" and "corroborating" not in (result.match_reason or ""):
            passed = False
            incorrect_merge = True

    return {
        "action": result.action,
        "requires_review": result.requires_review,
        "match_reason": result.match_reason,
        "passed": passed,
        "incorrect_merge": incorrect_merge,
    }


def eval_osint(case_id: str, entity_id: str, lookup_id: str, nonsense: str) -> dict:
    from app.database import SessionLocal
    from app.services.osint_enrichment import run_osint_enrichment

    db = SessionLocal()
    try:
        person_label = nonsense
        from app.services.osint_enrichment import _enrich_court_bulletin

        hits = _enrich_court_bulletin(db, case_id, entity_id, person_label)
        all_no_match = all(h.get("match_quality") == "no_match" for h in hits)
        return {"hits": len(hits), "all_no_match": all_no_match, "passed": all_no_match}
    finally:
        db.close()


def main() -> int:
    fixture_paths = [FIXTURES]
    if FIXTURES_EXTRA.exists():
        fixture_paths.append(FIXTURES_EXTRA)
    if not FIXTURES.exists():
        print("Missing fixtures.json")
        return 1

    fixtures: list[dict] = []
    for path in fixture_paths:
        fixtures.extend(json.loads(path.read_text()))
    results: list[dict] = []
    ner_precisions: list[float] = []
    ner_recalls: list[float] = []

    for fx in fixtures:
        fid = fx["id"]
        ftype = fx.get("type", "note")
        row: dict = {"id": fid, "scenario": fx.get("scenario"), "type": ftype}

        if ftype == "ner":
            metrics = eval_ner(fx["text"], fx.get("expected_spans", []))
            row.update(metrics)
            if metrics["precision"] is not None:
                ner_precisions.append(metrics["precision"])
                ner_recalls.append(metrics["recall"])
        elif ftype == "resolution":
            try:
                metrics = eval_resolution(
                    fx["case_id"],
                    fx["name"],
                    fx.get("context_phones", []),
                    fx,
                )
                row.update(metrics)
            except Exception as exc:
                row["passed"] = False
                row["error"] = str(exc)
        elif ftype == "osint":
            try:
                metrics = eval_osint(
                    fx["case_id"],
                    fx["entity_id"],
                    fx["lookup_id"],
                    fx.get("expect_no_unrelated_when", "ZZZNOTINANYFIRZZZ"),
                )
                row.update(metrics)
            except Exception as exc:
                row["passed"] = False
                row["error"] = str(exc)
        else:
            row["passed"] = None
            row["note"] = fx.get("note", "")

        results.append(row)
        status = row.get("passed")
        mark = "PASS" if status else ("SKIP" if status is None else "FAIL")
        print(f"[{mark}] {fid} ({fx.get('scenario')})")

    passed = sum(1 for r in results if r.get("passed") is True)
    failed = sum(1 for r in results if r.get("passed") is False)
    skipped = sum(1 for r in results if r.get("passed") is None)
    incorrect_merges = sum(1 for r in results if r.get("incorrect_merge"))

    print("\n--- Summary ---")
    print(f"Fixtures: {len(results)} | passed: {passed} | failed: {failed} | skipped: {skipped}")
    if incorrect_merges:
        print(f"Incorrect auto-merges: {incorrect_merges} (critical — higher priority than missed suggestions)")
    if ner_precisions:
        avg_p = sum(ner_precisions) / len(ner_precisions)
        avg_r = sum(ner_recalls) / len(ner_recalls)
        print(f"NER avg precision: {avg_p:.3f} | avg recall: {avg_r:.3f}")
        print("(Held-out fixtures — not used for rule tuning.)")

    out = ROOT / "eval_report.json"
    out.write_text(
        json.dumps(
            {
                "results": results,
                "summary": {
                    "passed": passed,
                    "failed": failed,
                    "incorrect_merges": incorrect_merges,
                },
            },
            indent=2,
        )
    )
    print(f"Report: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
