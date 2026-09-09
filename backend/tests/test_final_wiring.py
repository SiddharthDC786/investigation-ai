
def test_health_includes_postgres(raw_client):
    response = raw_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "postgres" in body
    assert "neo4j" in body


def test_case_stats(client):
    cases = client.get("/cases").json()
    if not cases:
        return
    case_id = cases[0]["case_id"]
    response = client.get(f"/cases/{case_id}/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == case_id
    assert "persons" in body
    assert "timeline_events" in body
