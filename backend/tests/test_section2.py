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


def test_timeline_returns_events(client):
    response = client.get(f"/cases/{CASE_ID}/timeline")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == CASE_ID
    assert isinstance(body["events"], list)
    if body["events"]:
        event = body["events"][0]
        assert "timestamp" in event
        assert "entityIds" in event


def test_centrality_rankings(client):
    response = client.get(f"/cases/{CASE_ID}/analyze/centrality")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == CASE_ID
    assert isinstance(body["rankings"], list)
    if body["rankings"]:
        row = body["rankings"][0]
        assert "pagerank" in row
        assert "betweenness" in row
        assert row["rank"] == 1


def test_community_detection(client):
    response = client.get(f"/cases/{CASE_ID}/analyze/communities")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == CASE_ID
    assert isinstance(body["communities"], list)
