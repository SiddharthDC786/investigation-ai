SAMPLE_FIR = """
FIRST INFORMATION REPORT
Complainant Rahul Sharma contacted police regarding fraud.
Suspect Amit Verma used phone 9876543210 and account A/C 123456789012.
Organization Delhi Trading Co was mentioned near Mumbai.
"""


def test_ingest_fir_extracts_entities(client):
    response = client.post(
        "/ingest/fir",
        data={"case_id": "CASE0001"},
        files={"file": ("fir.txt", SAMPLE_FIR, "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["entities_extracted"] >= 2
    assert body["source_type"] == "fir"
    types = {m["entity_type"] for m in body["mentions"]}
    assert "person" in types or "phone" in types


def test_ingest_cdr_csv(client):
    csv_data = "cdr_id,caller_phone,receiver_phone,timestamp,duration_seconds,tower_location\nCDR1,9000000001,9000000002,2024-01-01 10:00:00,60,Tower A\n"
    response = client.post(
        "/ingest/cdr",
        data={"case_id": "CASE0001"},
        files={"file": ("cdr.csv", csv_data, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["records_received"] == 1
