"""Tests for NLP preview and enhanced ingest."""

SAMPLE = """
Suspect Rahul Mukherjee aka Meera Chopra called +91 8871205599 from Mumbai.
Transferred from A/C 998877665544 to account 112233445566. Vehicle MH12AB1234 noted.
"""


def test_health_includes_nlp(raw_client):
    response = raw_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "nlp" in body
    assert body["nlp"]["engine"] in ("spacy", "regex")


def test_ingest_preview_extracts_entities(client):
    response = client.post("/ingest/preview", json={"text": SAMPLE})
    assert response.status_code == 200
    body = response.json()
    assert body["entities_extracted"] >= 4
    types = {e["entity_type"] for e in body["entities"]}
    assert "person" in types or "alias" in types
    assert "phone" in types
    assert "account" in types


def test_ingest_fir_text(client):
    response = client.post(
        "/ingest/fir/text",
        data={"text": SAMPLE, "case_id": "CASE0001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["entities_extracted"] >= 1
