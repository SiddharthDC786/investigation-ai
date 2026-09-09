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


def test_investigation_map_shows_full_case_network_when_focus_is_associate(client):
    """Selecting an associate should still show everyone connected in the case."""
    suspect = client.get("/cases/CASE0001/graph?simplified=true")
    if suspect.status_code == 404:
        pytest.skip("crime_network database not loaded")
    assert suspect.status_code == 200
    suspect_ids = {n["id"] for n in suspect.json()["nodes"] if n["type"] == "person"}

    associate = client.get("/cases/CASE0001/graph?simplified=true&center_person_id=P00052")
    assert associate.status_code == 200
    body = associate.json()
    associate_ids = {n["id"] for n in body["nodes"] if n["type"] == "person"}

    assert body["focus_person_id"] == "P00052"
    assert "P00014" in associate_ids, "primary suspect should remain on map when focus is associate"
    assert len(associate_ids) >= len(suspect_ids) - 1, "associate focus should not shrink the network"
    assert len(body["links"]) >= 1
