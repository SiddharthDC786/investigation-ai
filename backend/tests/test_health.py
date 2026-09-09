
def test_health(raw_client):
    response = raw_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ("ok", "degraded")
