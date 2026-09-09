import pytest

CASE_ID = "CASE0001"


@pytest.fixture(autouse=True)
def _require_db():
    from sqlalchemy import text
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        if not db.execute(text("SELECT 1 FROM cases WHERE case_id = :cid"), {"cid": CASE_ID}).first():
            pytest.skip("crime_network DB not loaded")
    finally:
        db.close()


def test_explain_entity(client):
    response = client.get(f"/explain/P00014?case_id={CASE_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == "P00014"
    assert body["narrative"]
    assert len(body["reasoning_steps"]) >= 1
    assert body["source_citations"]


def test_risk_scores(client):
    response = client.get(f"/cases/{CASE_ID}/analyze/risk-score")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == CASE_ID
    assert body.get("score_type") == "investigation_priority"
    assert len(body["scores"]) >= 1
    top = body["scores"][0]
    assert "composite_score" in top
    assert top["triage_rank"] == 1
    assert top["components"]["centrality"] >= 0


def test_case_summary_under_3_seconds(client):
    response = client.get(f"/case-summary/{CASE_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["narrative"]
    assert body["key_findings"]
    assert body["generated_in_ms"] < 3000
