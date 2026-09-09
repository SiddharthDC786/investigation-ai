from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def compute_case_leads(db: Session, case_id: str) -> list[dict]:
    """Generate leads from observed case evidence — no hardcoded stubs."""
    leads: list[dict] = []

    shared_phones = db.execute(
        text(
            """
            WITH case_calls AS (
                SELECT caller_phone AS phone FROM cdr WHERE case_id = :cid
                UNION ALL
                SELECT receiver_phone FROM cdr WHERE case_id = :cid
            ),
            phone_owners AS (
                SELECT ph.phone_number, ph.person_id, p.name
                FROM phones ph
                JOIN people p ON p.person_id = ph.person_id
                WHERE ph.phone_number IN (SELECT phone FROM case_calls)
            ),
            shared AS (
                SELECT phone_number, COUNT(DISTINCT person_id) AS owner_count,
                       array_agg(DISTINCT person_id) AS person_ids,
                       array_agg(DISTINCT name) AS names
                FROM phone_owners
                GROUP BY phone_number
                HAVING COUNT(DISTINCT person_id) >= 2
            )
            SELECT phone_number, owner_count, person_ids, names FROM shared
            ORDER BY owner_count DESC
            LIMIT 10
            """
        ),
        {"cid": case_id},
    ).mappings().all()

    for idx, row in enumerate(shared_phones, start=1):
        names = row["names"] or []
        label = ", ".join(names[:3])
        leads.append(
            {
                "lead_id": f"LEAD-SHARED-{idx:03d}",
                "description": (
                    f"Shared phone {row['phone_number']} links {row['owner_count']} persons: {label}"
                ),
                "priority_score": min(99, 40 + int(row["owner_count"]) * 15),
                "score_type": "investigation_priority",
                "evidence": [f"cdr_shared_phone:{row['phone_number']}"],
                "source_type": "observed",
                "requires_review": False,
            }
        )

    bridge_rows = db.execute(
        text(
            """
            SELECT c.cdr_id, c.caller_phone, c.receiver_phone, c.duration_seconds
            FROM cdr c
            WHERE c.case_id = :cid
            ORDER BY c.duration_seconds DESC
            LIMIT 5
            """
        ),
        {"cid": case_id},
    ).mappings().all()

    for idx, row in enumerate(bridge_rows[:3], start=1):
        leads.append(
            {
                "lead_id": f"LEAD-CDR-{idx:03d}",
                "description": (
                    f"Call {row['caller_phone']} → {row['receiver_phone']} "
                    f"({row['duration_seconds']}s) — review CDR {row['cdr_id']}"
                ),
                "priority_score": min(85, 30 + int(row["duration_seconds"] or 0) // 60),
                "score_type": "investigation_priority",
                "evidence": [row["cdr_id"]],
                "source_type": "observed",
                "requires_review": False,
            }
        )

    return leads
