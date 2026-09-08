from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_case_stats(db: Session, case_id: str) -> dict:
    case = db.execute(
        text("SELECT case_id FROM cases WHERE case_id = :cid"),
        {"cid": case_id},
    ).first()
    if not case:
        raise ValueError("Case not found")

    person_count = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT pid) FROM (
                SELECT person_id_a AS pid FROM relationships WHERE case_id = :cid
                UNION SELECT person_id_b FROM relationships WHERE case_id = :cid
            ) x
            """
        ),
        {"cid": case_id},
    ).scalar() or 0

    cdr_count = db.execute(
        text("SELECT COUNT(*) FROM cdr WHERE case_id = :cid"),
        {"cid": case_id},
    ).scalar() or 0

    txn_count = db.execute(
        text("SELECT COUNT(*) FROM transactions WHERE case_id = :cid"),
        {"cid": case_id},
    ).scalar() or 0

    surveillance_count = db.execute(
        text("SELECT COUNT(*) FROM surveillance WHERE case_id = :cid"),
        {"cid": case_id},
    ).scalar() or 0

    fir_count = db.execute(
        text("SELECT COUNT(*) FROM fir WHERE case_id = :cid"),
        {"cid": case_id},
    ).scalar() or 0

    timeline_events = cdr_count + txn_count + surveillance_count + fir_count

    return {
        "case_id": case_id,
        "persons": int(person_count),
        "cdr_records": int(cdr_count),
        "transactions": int(txn_count),
        "timeline_events": int(timeline_events),
    }
