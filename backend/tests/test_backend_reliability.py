#!/usr/bin/env python3
"""Backend reliability tests: workflow, isolation, dedup, identity merges."""

import pytest
from sqlalchemy import text

from app.database import SessionLocal

CASE_ID = "CASE0001"
FIR_TEXT = (
    "FIR supplement: suspect Rahul Sharma of Chennai called from 6851846689 "
    "regarding unrelated matter. Witness Rahul Patel present."
)


@pytest.fixture(autouse=True)
def _require_db():
    db = SessionLocal()
    try:
        if not db.execute(text("SELECT 1 FROM cases WHERE case_id = :cid"), {"cid": CASE_ID}).first():
            pytest.skip("crime_network DB not loaded — run dataset/ci_seed.sql")
    finally:
        db.close()


def test_unauthenticated_ingest_rejected(raw_client):
    res = raw_client.post(
        "/ingest/fir/text",
        data={"text": FIR_TEXT, "case_id": CASE_ID},
    )
    assert res.status_code == 401


def test_investigator_denied_ingest_other_case(auth_headers, raw_client):
    res = raw_client.post(
        "/ingest/fir/text",
        data={"text": FIR_TEXT, "case_id": "CASE9999"},
        headers=auth_headers,
    )
    assert res.status_code == 403


def test_workflow_login_ingest_review_graph(auth_client):
    text = f"Unique workflow probe {pytest.__version__}: Rahul Sharma met witness at Chennai."
    ingest = auth_client.post(
        "/ingest/fir/text",
        data={"text": text, "case_id": CASE_ID},
    )
    assert ingest.status_code == 200, ingest.text
    body = ingest.json()
    assert body["status"] in ("success", "duplicate")
    if body["status"] == "success":
        assert body["entities_extracted"] >= 1

    graph = auth_client.get(f"/cases/{CASE_ID}/graph")
    assert graph.status_code == 200

    review = auth_client.post(
        f"/cases/{CASE_ID}/reviews",
        json={"entity_id": "P00014", "decision": "confirmed", "notes": "workflow test"},
    )
    assert review.status_code == 200


def test_duplicate_fir_ingest_idempotent(auth_client):
    import uuid

    unique = f"Dedup probe {uuid.uuid4().hex} — no persons named ZZZDEDUP."
    first = auth_client.post(
        "/ingest/fir/text",
        data={"text": unique, "case_id": CASE_ID},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "success"

    second = auth_client.post(
        "/ingest/fir/text",
        data={"text": unique, "case_id": CASE_ID},
    )
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert second.json()["entities_extracted"] == 0


def test_two_rahul_sharma_not_auto_merged():
    from ai.ner_pipeline import ExtractedEntity
    from app.services.entity_resolution import provisional_person_id, resolve_entity

    db = SessionLocal()
    try:
        mumbai = ExtractedEntity(
            text="Rahul Sharma", entity_type="person", start=0, end=12, confidence=0.9
        )
        chennai = ExtractedEntity(
            text="Rahul Sharma", entity_type="person", start=20, end=32, confidence=0.9
        )
        r1 = resolve_entity(
            db,
            case_id=CASE_ID,
            mention=mumbai,
            context_phones=["8871205599"],
            source_id="SRC-TEST1",
            all_mentions=[mumbai],
            source_text="Rahul Sharma phone 8871205599",
        )
        r2 = resolve_entity(
            db,
            case_id=CASE_ID,
            mention=chennai,
            context_phones=["6851846689"],
            source_id="SRC-TEST2",
            all_mentions=[chennai],
            source_text="Rahul Sharma phone 6851846689",
        )
        assert provisional_person_id(CASE_ID, "SRC-TEST1", 0, "Rahul Sharma") != provisional_person_id(
            CASE_ID, "SRC-TEST2", 20, "Rahul Sharma"
        )
        if r1.action == "merged" and r2.action == "merged":
            assert r1.entity_id != r2.entity_id
    finally:
        db.close()


def test_graph_timeline_require_case_access(auth_headers, raw_client):
    for path in (
        "/cases/CASE9999/graph",
        "/cases/CASE9999/timeline",
        "/cases/CASE9999/analyze/risk-score",
    ):
        res = raw_client.get(path, headers=auth_headers)
        assert res.status_code == 403
