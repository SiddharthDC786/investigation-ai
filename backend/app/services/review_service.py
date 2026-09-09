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
    is_provisional_entity_id,
    is_registered_person,
)


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


def _lookup_provenance_record(
    db: Session,
    *,
    case_id: str,
    entity_id: str,
) -> tuple[str | None, str | None]:
    row = db.execute(
        text(
            """
            SELECT ep.record_id, rn.recorded_name
            FROM entity_provenance ep
            LEFT JOIN recorded_names rn ON rn.record_id = ep.record_id
            WHERE ep.case_id = :cid AND ep.entity_id = :eid
            ORDER BY ep.created_at DESC
            LIMIT 1
            """
        ),
        {"cid": case_id, "eid": entity_id},
    ).mappings().first()
    if not row:
        return None, None
    return row["record_id"], row["recorded_name"]


def _infer_suggested_person(db: Session, *, case_id: str, name: str) -> str | None:
    from ai.ner_pipeline import ExtractedEntity
    from app.services.entity_resolution import resolve_entity

    mention = ExtractedEntity(
        text=name, entity_type="person", start=0, end=len(name), confidence=0.9
    )
    result = resolve_entity(db, case_id=case_id, mention=mention, context_phones=[])
    if result.suggested_person_id and is_registered_person(db, result.suggested_person_id):
        return result.suggested_person_id
    if result.action == "merged" and is_registered_person(db, result.entity_id):
        return result.entity_id
    return None


def _resolve_merge_target(
    db: Session,
    *,
    case_id: str,
    mention_entity_id: str,
    recorded_name: str,
    explicit_canonical: str | None,
) -> str:
    if not is_provisional_entity_id(mention_entity_id):
        raise ValueError("Identity merge applies only to provisional entity IDs (PU-...)")

    if explicit_canonical:
        if is_provisional_entity_id(explicit_canonical):
            raise ValueError("Provisional IDs cannot be used as merge targets")
        if not is_registered_person(db, explicit_canonical):
            raise ValueError(f"Unknown canonical person: {explicit_canonical}")
        return explicit_canonical

    suggested = _infer_suggested_person(db, case_id=case_id, name=recorded_name)
    if not suggested:
        raise ValueError(
            "Cannot identify an unambiguous canonical person for this provisional mention"
        )
    return suggested


def _apply_identity_review_effects(
    db: Session,
    *,
    case_id: str,
    entity_id: str,
    decision: str,
    reviewer_badge: str,
    reviewer_name: str,
    canonical_person_id: str | None = None,
) -> str | None:
    """Apply identity-merge side effects for provisional mentions only."""
    if not is_provisional_entity_id(entity_id):
        return None

    record_id, recorded_name = _lookup_provenance_record(db, case_id=case_id, entity_id=entity_id)
    if not record_id or not recorded_name:
        raise ValueError("No provenance record found for this provisional mention")

    if decision == "confirmed":
        canonical = _resolve_merge_target(
            db,
            case_id=case_id,
            mention_entity_id=entity_id,
            recorded_name=recorded_name,
            explicit_canonical=canonical_person_id,
        )
        apply_confirmed_identity(
            db,
            case_id=case_id,
            mention_entity_id=entity_id,
            canonical_person_id=canonical,
            recorded_name=recorded_name,
            record_id=record_id,
            reviewer_badge=reviewer_badge,
            reviewer_name=reviewer_name,
        )
        return canonical

    if decision == "not_relevant":
        candidate = _infer_suggested_person(db, case_id=case_id, name=recorded_name)
        if candidate:
            block_identity(
                db,
                case_id=case_id,
                mention_entity_id=entity_id,
                recorded_name=recorded_name,
                blocked_person_id=candidate,
                reviewer_badge=reviewer_badge,
                reviewer_name=reviewer_name,
            )
    return None


def list_reviews(db: Session, *, case_id: str) -> list[dict[str, Any]]:
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
    canonical_person_id: str | None = None,
) -> dict[str, Any]:
    merged_canonical: str | None = None
    try:
        if decision in {"confirmed", "not_relevant"} and is_provisional_entity_id(entity_id):
            merged_canonical = _apply_identity_review_effects(
                db,
                case_id=case_id,
                entity_id=entity_id,
                decision=decision,
                reviewer_badge=reviewer_badge,
                reviewer_name=reviewer_name,
                canonical_person_id=canonical_person_id,
            )
        elif decision == "confirmed" and canonical_person_id:
            if is_provisional_entity_id(canonical_person_id) or not is_registered_person(
                db, canonical_person_id
            ):
                raise ValueError(f"Invalid canonical person target: {canonical_person_id}")

        review_id = f"REV-{uuid.uuid4().hex[:10].upper()}"
        db.execute(
            text(
                """
                INSERT INTO officer_reviews
                    (review_id, case_id, entity_id, decision, notes,
                     reviewer_badge, reviewer_name, canonical_person_id,
                     created_at, updated_at)
                VALUES
                    (:rid, :cid, :eid, :decision, :notes, :badge, :name, :cpid, NOW(), NOW())
                ON CONFLICT (case_id, entity_id, reviewer_badge)
                DO UPDATE SET
                    decision = EXCLUDED.decision,
                    notes = EXCLUDED.notes,
                    canonical_person_id = EXCLUDED.canonical_person_id,
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
                "cpid": merged_canonical,
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
        append_audit_entry(
            db,
            case_id=case_id,
            action=f"Officer review: {decision.replace('_', ' ')} on {entity_id}",
            entity_id=entity_id,
            source="Vigil review queue",
            operator=f"{reviewer_badge} ({reviewer_name})",
            lawful_basis="Human review of AI suggestion — persisted server-side",
            payload={"decision": decision, "notes": notes, "canonical_person_id": merged_canonical},
        )
        db.commit()
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "entity_id": entity_id,
        "decision": decision,
        "notes": notes,
        "canonical_person_id": merged_canonical,
    }
