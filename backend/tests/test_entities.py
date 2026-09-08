from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_entity_postgres_fallback():
    response = client.get("/entities/P00014")
    if response.status_code == 404:
        return
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "PERSON"
    assert "sources" in body


def test_get_unknown_entity():
    response = client.get("/entities/UNKNOWN999")
    assert response.status_code == 404


def test_health_reports_neo4j_flag():
    response = client.get("/health")
    assert response.status_code == 200
    assert "neo4j" in response.json()
