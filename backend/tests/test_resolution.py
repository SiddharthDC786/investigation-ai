# tests/test_resolution.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_candidates():
    response = client.get("/resolution/candidates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)