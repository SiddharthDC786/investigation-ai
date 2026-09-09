from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.audit_chain import append_audit_entry


def ensure_reviews_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS officer_reviews (
                review_id VARCHAR(32) PRIMARY KEY,
                case_id VARCHAR(16) NOT NULL,
                entity_id VARCHAR(32) NOT NULL,
                decision VARCHAR(32) NOT NULL,
                notes TEXT,
                reviewer_badge VARCHAR(32) NOT NULL,
                reviewer_name VARCHAR(128) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (case_id, entity_id, reviewer_badge)
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_officer_reviews_case ON officer_reviews(case_id)"
        )
    )
    db.commit()


def list_reviews(db: Session, *, case_id: str) -> list[dict[str, Any]]:
    ensure_reviews_table(db)
    rows = db.execute(
        text(
            """
            SELECT entity_id, decision, notes, reviewer_badge, reviewer_name,
                   created_at, updated_at
            FROM officer_reviews
            WHERE case_id = :cid
            ORDER BY updated_at DESC
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    return [
        {
            "entity_id": r["entity_id"],
            "decision": r["decision"],
            "notes": r["notes"],
            "reviewer_badge": r["reviewer_badge"],
            "reviewer_name": r["reviewer_name"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]


def upsert_review(
    db: Session,
    *,
    case_id: str,
    entity_id: str,
    decision: str,
    notes: str | None,
    reviewer_badge: str,
    reviewer_name: str,
) -> dict[str, Any]:
    ensure_reviews_table(db)
    review_id = f"REV-{uuid.uuid4().hex[:10].upper()}"
    db.execute(
        text(
            """
            INSERT INTO officer_reviews
                (review_id, case_id, entity_id, decision, notes,
                 reviewer_badge, reviewer_name, created_at, updated_at)
            VALUES
                (:rid, :cid, :eid, :decision, :notes, :badge, :name, NOW(), NOW())
            ON CONFLICT (case_id, entity_id, reviewer_badge)
            DO UPDATE SET
                decision = EXCLUDED.decision,
                notes = EXCLUDED.notes,
                updated_at = NOW()
            """
        ),
        {
            "rid": review_id,
            "cid": case_id,
            "eid": entity_id,
            "decision": decision,
            "notes": notes,
            "badge": reviewer_badge,
            "name": reviewer_name,
        },
    )
    append_audit_entry(
        db,
        case_id=case_id,
        action=f"Officer review: {decision.replace('_', ' ')} on {entity_id}",
        entity_id=entity_id,
        source="Vigil review queue",
        operator=f"{reviewer_badge} ({reviewer_name})",
        lawful_basis="Human review of AI suggestion — persisted server-side",
        payload={"decision": decision, "notes": notes},
    )
    db.commit()
    return {"entity_id": entity_id, "decision": decision, "notes": notes}
