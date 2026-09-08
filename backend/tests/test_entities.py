from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_get_known_entity():
    response = client.get("/entities/P001")
    assert response.status_code == 200
    assert response.json()["type"] == "PERSON"

def test_get_unknown_entity():
    response = client.get("/entities/UNKNOWN999")
    assert response.status_code == 404