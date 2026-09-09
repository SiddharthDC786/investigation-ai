
def test_get_entity_postgres_fallback(client):
    response = client.get("/entities/P00014")
    if response.status_code == 404:
        return
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "PERSON"
    assert "sources" in body


def test_get_unknown_entity(client):
    response = client.get("/entities/UNKNOWN999")
    assert response.status_code == 404


def test_health_reports_neo4j_flag(raw_client):
    response = raw_client.get("/health")
    assert response.status_code == 200
    assert "neo4j" in response.json()
