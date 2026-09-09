from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.audit_chain import append_audit_entry
from app.services.provenance_service import (
    append_review_history,
    apply_confirmed_identity,
    block_identity,
    ensure_provenance_tables,
)


def ensure_reviews_table(db: Session) -> None:
    ensure_provenance_tables(db)
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
                canonical_person_id VARCHAR(16),
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
    db.execute(
        text(
            "ALTER TABLE officer_reviews ADD COLUMN IF NOT EXISTS canonical_person_id VARCHAR(16)"
        )
    )
    db.commit()


def _lookup_recorded_name(db: Session, *, case_id: str, entity_id: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT rn.recorded_name
            FROM entity_provenance ep
            JOIN recorded_names rn ON rn.record_id = ep.record_id
            WHERE ep.case_id = :cid AND ep.entity_id = :eid
            ORDER BY ep.created_at DESC
            LIMIT 1
            """
        ),
        {"cid": case_id, "eid": entity_id},
    ).scalar()
    if row:
        return row
    return db.execute(
        text(
            """
            SELECT name FROM people WHERE person_id = :eid
            """
        ),
        {"eid": entity_id},
    ).scalar()


def _infer_suggested_person(db: Session, *, case_id: str, entity_id: str, name: str) -> str | None:
    from ai.ner_pipeline import ExtractedEntity
    from app.services.entity_resolution import resolve_entity

    mention = ExtractedEntity(
        text=name, entity_type="person", start=0, end=len(name), confidence=0.9
    )
    result = resolve_entity(db, case_id=case_id, mention=mention, context_phones=[])
    if result.suggested_person_id:
        return result.suggested_person_id
    if result.action == "merged" and result.entity_id.startswith("P"):
        return result.entity_id
    return None


def _apply_review_effects(
    db: Session,
    *,
    case_id: str,
    entity_id: str,
    decision: str,
    reviewer_badge: str,
    reviewer_name: str,
) -> None:
    name = _lookup_recorded_name(db, case_id=case_id, entity_id=entity_id) or entity_id

    if decision == "confirmed":
        canonical = entity_id if entity_id.startswith("P") else None
        if not canonical:
            canonical = _infer_suggested_person(db, case_id=case_id, entity_id=entity_id, name=name)
        if canonical and canonical.startswith("P"):
            apply_confirmed_identity(
                db,
                case_id=case_id,
                mention_entity_id=entity_id,
                canonical_person_id=canonical,
                recorded_name=name if isinstance(name, str) else str(name),
                reviewer_badge=reviewer_badge,
                reviewer_name=reviewer_name,
            )
            db.execute(
                text(
                    """
                    UPDATE officer_reviews
                    SET canonical_person_id = :pid
                    WHERE case_id = :cid AND entity_id = :eid AND reviewer_badge = :badge
                    """
                ),
                {"pid": canonical, "cid": case_id, "eid": entity_id, "badge": reviewer_badge},
            )
    elif decision == "not_relevant":
        candidate = _infer_suggested_person(db, case_id=case_id, entity_id=entity_id, name=name)
        if candidate and candidate.startswith("P"):
            block_identity(
                db,
                case_id=case_id,
                recorded_name=name if isinstance(name, str) else str(name),
                blocked_person_id=candidate,
                reviewer_badge=reviewer_badge,
                reviewer_name=reviewer_name,
            )


def list_reviews(db: Session, *, case_id: str) -> list[dict[str, Any]]:
    ensure_reviews_table(db)
    rows = db.execute(
        text(
            """
            SELECT entity_id, decision, notes, reviewer_badge, reviewer_name,
                   canonical_person_id, created_at, updated_at
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
            "canonical_person_id": r.get("canonical_person_id"),
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
    append_review_history(
        db,
        case_id=case_id,
        entity_id=entity_id,
        decision=decision,
        notes=notes,
        reviewer_badge=reviewer_badge,
        reviewer_name=reviewer_name,
    )
    _apply_review_effects(
        db,
        case_id=case_id,
        entity_id=entity_id,
        decision=decision,
        reviewer_badge=reviewer_badge,
        reviewer_name=reviewer_name,
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
