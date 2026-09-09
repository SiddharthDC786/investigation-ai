import pytest


def test_get_graph(client):
    response = client.get("/cases/CASE0001/graph")
    if response.status_code == 404:
        pytest.skip("crime_network database not loaded")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "links" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["links"], list)
