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


def test_osint_enrich_and_audit_chain(client):
    response = client.post(
        "/osint/enrich",
        json={
            "case_id": CASE_ID,
            "entity_id": "P00014",
            "lookup_id": "OSINT-01",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["audit_entry_id"].startswith("AUD-")
    assert len(body["audit_hash"]) == 64
    assert body["results"]
    assert body.get("simulated") is True
    assert body.get("graph_links_added") == []

    verify = client.get(f"/audit/verify?case_id={CASE_ID}")
    assert verify.status_code == 200
    assert verify.json()["status"] == "verified"

    log = client.get(f"/osint/audit-log?case_id={CASE_ID}")
    assert log.status_code == 200
    assert log.json()["chain_status"] == "verified"
    assert any("OSINT" in e["action"] for e in log.json()["entries"])


def test_osint_unknown_lookup(client):
    response = client.post(
        "/osint/enrich",
        json={
            "case_id": CASE_ID,
            "entity_id": "P00014",
            "lookup_id": "OSINT-INVALID",
        },
    )
    assert response.status_code == 400


def test_audit_verify_denied_other_case(auth_headers, raw_client):
    response = raw_client.get("/audit/verify?case_id=CASE9999", headers=auth_headers)
    assert response.status_code == 403


def test_audit_verify_supervisor_other_case(supervisor_headers, raw_client):
    response = raw_client.get("/audit/verify?case_id=CASE9999", headers=supervisor_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "verified"
    assert response.json()["entries_checked"] == 0
