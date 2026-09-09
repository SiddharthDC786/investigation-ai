import pytest
from sqlalchemy import text

from app.database import SessionLocal

CASE_ID = "CASE0001"


@pytest.fixture(autouse=True)
def _require_db():
    db = SessionLocal()
    try:
        if not db.execute(text("SELECT 1 FROM cases WHERE case_id = :cid"), {"cid": CASE_ID}).first():
            pytest.skip("crime_network DB not loaded")
    finally:
        db.close()


def test_login_and_me(raw_client):
    res = raw_client.post("/auth/login", json={"badge_id": "INV-2847", "password": "vigil2026"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    me = raw_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["badge_id"] == "INV-2847"


def test_unauthenticated_search_rejected(raw_client):
    res = raw_client.get(f"/cases/{CASE_ID}/search?name=Rahul")
    assert res.status_code == 401


def test_investigator_denied_other_case(auth_headers, raw_client):
    res = raw_client.get(
        "/cases/CASE9999/search?name=test",
        headers=auth_headers,
    )
    assert res.status_code == 403


def test_review_persistence(auth_client):
    entity_id = "P00014"
    save = auth_client.post(
        f"/cases/{CASE_ID}/reviews",
        json={"entity_id": entity_id, "decision": "confirmed", "notes": "Test review"},
    )
    assert save.status_code == 200
    listed = auth_client.get(f"/cases/{CASE_ID}/reviews")
    assert listed.status_code == 200
    rows = listed.json()
    assert any(r["entity_id"] == entity_id and r["decision"] == "confirmed" for r in rows)


def test_leads_from_evidence_not_hardcoded(auth_client):
    res = auth_client.get(f"/cases/{CASE_ID}/leads")
    assert res.status_code == 200
    leads = res.json()
    assert isinstance(leads, list)
    for lead in leads:
        assert lead["lead_id"] != "LEAD001" or "shared" in lead["description"].lower() or "cdr" in lead["lead_id"].lower()
        assert lead.get("score_type") == "investigation_priority"
        assert "confidence" not in lead


def test_osint_simulated_no_graph_links(auth_client):
    res = auth_client.post(
        "/osint/enrich",
        json={"case_id": CASE_ID, "entity_id": "P00014", "lookup_id": "OSINT-02"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("simulated") is True
    assert body.get("graph_links_added") == []
    assert "disclaimer" in body


def test_osint_court_no_unrelated_fallback(auth_client):
    res = auth_client.post(
        "/osint/enrich",
        json={"case_id": CASE_ID, "entity_id": "P00014", "lookup_id": "OSINT-02"},
    )
    assert res.status_code == 200
    for hit in res.json()["results"]:
        if hit.get("match_quality") == "no_match":
            assert hit["relevance_score"] == 0


def test_entity_resolution_requires_corroboration():
    from app.services.entity_resolution import resolve_entity
    from ai.ner_pipeline import ExtractedEntity
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        mention = ExtractedEntity(
            text="Rahul Mukherjee", entity_type="person", start=0, end=16, confidence=0.9
        )
        result = resolve_entity(db, case_id=CASE_ID, mention=mention, context_phones=[])
        assert result.action in ("suggested_match", "merged", "created")
        if result.action == "suggested_match":
            assert result.requires_review is True
            assert result.match_reason
    finally:
        db.close()
