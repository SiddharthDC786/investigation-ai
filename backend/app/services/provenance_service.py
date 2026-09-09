from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def content_hash(text_content: str) -> str:
    return hashlib.sha256(text_content.encode("utf-8")).hexdigest()


def ensure_provenance_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS ingest_sources (
                source_id VARCHAR(32) PRIMARY KEY,
                case_id VARCHAR(16) NOT NULL,
                source_type VARCHAR(64) NOT NULL,
                content_hash VARCHAR(64) NOT NULL,
                byte_size INTEGER NOT NULL DEFAULT 0,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (case_id, source_type, content_hash)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS entity_provenance (
                provenance_id VARCHAR(32) PRIMARY KEY,
                case_id VARCHAR(16),
                entity_id VARCHAR(32) NOT NULL,
                source_type VARCHAR(64) NOT NULL,
                source_id VARCHAR(32) NOT NULL,
                record_id VARCHAR(32),
                excerpt TEXT,
                extraction_method VARCHAR(64) NOT NULL DEFAULT 'ner_extract',
                relationship_kind VARCHAR(32) NOT NULL DEFAULT 'observed',
                resolution_action VARCHAR(32) NOT NULL DEFAULT 'created',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS identity_decisions (
                decision_id VARCHAR(32) PRIMARY KEY,
                case_id VARCHAR(16) NOT NULL,
                mention_entity_id VARCHAR(32) NOT NULL,
                canonical_person_id VARCHAR(16) NOT NULL,
                recorded_name VARCHAR(128) NOT NULL,
                decision VARCHAR(32) NOT NULL,
                reviewer_badge VARCHAR(32) NOT NULL,
                reviewer_name VARCHAR(128) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (case_id, mention_entity_id, canonical_person_id)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS identity_blocks (
                block_id VARCHAR(32) PRIMARY KEY,
                case_id VARCHAR(16) NOT NULL,
                recorded_name VARCHAR(128) NOT NULL,
                blocked_person_id VARCHAR(16) NOT NULL,
                reviewer_badge VARCHAR(32) NOT NULL,
                reviewer_name VARCHAR(128) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (case_id, recorded_name, blocked_person_id)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS officer_review_history (
                history_id VARCHAR(32) PRIMARY KEY,
                case_id VARCHAR(16) NOT NULL,
                entity_id VARCHAR(32) NOT NULL,
                decision VARCHAR(32) NOT NULL,
                notes TEXT,
                reviewer_badge VARCHAR(32) NOT NULL,
                reviewer_name VARCHAR(128) NOT NULL,
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS neo4j_sync_log (
                log_id VARCHAR(32) PRIMARY KEY,
                operation VARCHAR(64) NOT NULL,
                status VARCHAR(16) NOT NULL,
                details JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_entity_provenance_entity ON entity_provenance(entity_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_entity_provenance_case ON entity_provenance(case_id)"
        )
    )
    db.commit()


def find_duplicate_source(
    db: Session,
    *,
    case_id: str,
    source_type: str,
    digest: str,
) -> dict[str, Any] | None:
    ensure_provenance_tables(db)
    row = db.execute(
        text(
            """
            SELECT source_id, ingested_at
            FROM ingest_sources
            WHERE case_id = :cid AND source_type = :stype AND content_hash = :hash
            """
        ),
        {"cid": case_id, "stype": source_type, "hash": digest},
    ).mappings().first()
    return dict(row) if row else None


def register_ingest_source(
    db: Session,
    *,
    case_id: str,
    source_type: str,
    digest: str,
    byte_size: int,
    source_id: str | None = None,
) -> str:
    ensure_provenance_tables(db)
    sid = source_id or f"SRC{uuid.uuid4().hex[:8].upper()}"
    db.execute(
        text(
            """
            INSERT INTO ingest_sources (source_id, case_id, source_type, content_hash, byte_size)
            VALUES (:sid, :cid, :stype, :hash, :size)
            ON CONFLICT (case_id, source_type, content_hash) DO NOTHING
            """
        ),
        {
            "sid": sid,
            "cid": case_id,
            "stype": source_type,
            "hash": digest,
            "size": byte_size,
        },
    )
    return sid


def record_provenance(
    db: Session,
    *,
    case_id: str | None,
    entity_id: str,
    source_type: str,
    source_id: str,
    record_id: str | None,
    excerpt: str,
    extraction_method: str = "ner_extract",
    relationship_kind: str = "observed",
    resolution_action: str = "created",
) -> None:
    ensure_provenance_tables(db)
    pid = f"PV-{uuid.uuid4().hex[:10].upper()}"
    db.execute(
        text(
            """
            INSERT INTO entity_provenance
                (provenance_id, case_id, entity_id, source_type, source_id, record_id,
                 excerpt, extraction_method, relationship_kind, resolution_action)
            VALUES
                (:pid, :cid, :eid, :stype, :sid, :rid, :excerpt, :method, :rel, :action)
            """
        ),
        {
            "pid": pid,
            "cid": case_id,
            "eid": entity_id,
            "stype": source_type,
            "sid": source_id,
            "rid": record_id,
            "excerpt": excerpt[:2000],
            "method": extraction_method,
            "rel": relationship_kind,
            "action": resolution_action,
        },
    )


def list_entity_provenance(db: Session, *, entity_id: str, case_id: str | None = None) -> list[dict[str, Any]]:
    ensure_provenance_tables(db)
    q = """
        SELECT source_type, source_id, record_id, excerpt, extraction_method,
               relationship_kind, resolution_action, created_at
        FROM entity_provenance
        WHERE entity_id = :eid
    """
    params: dict[str, Any] = {"eid": entity_id}
    if case_id:
        q += " AND case_id = :cid"
        params["cid"] = case_id
    q += " ORDER BY created_at DESC LIMIT 50"
    rows = db.execute(text(q), params).mappings().all()
    return [
        {
            "source_type": r["source_type"],
            "source_id": r["source_id"],
            "record_id": r["record_id"],
            "excerpt": r["excerpt"],
            "extraction_method": r["extraction_method"],
            "relationship_kind": r["relationship_kind"],
            "resolution_action": r["resolution_action"],
            "timestamp": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


def normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def officer_confirmed_link(
    db: Session,
    *,
    case_id: str,
    name: str,
    person_id: str,
) -> bool:
    ensure_provenance_tables(db)
    row = db.execute(
        text(
            """
            SELECT 1 FROM identity_decisions
            WHERE case_id = :cid AND canonical_person_id = :pid
              AND lower(recorded_name) = lower(:name)
              AND decision = 'confirmed'
            LIMIT 1
            """
        ),
        {"cid": case_id, "pid": person_id, "name": name.strip()},
    ).first()
    return row is not None


def is_identity_blocked(
    db: Session,
    *,
    case_id: str,
    name: str,
    candidate_person_id: str,
) -> bool:
    ensure_provenance_tables(db)
    norm = normalize_name(name)
    block = db.execute(
        text(
            """
            SELECT 1 FROM identity_blocks
            WHERE case_id = :cid AND blocked_person_id = :pid
              AND lower(recorded_name) = :norm
            LIMIT 1
            """
        ),
        {"cid": case_id, "pid": candidate_person_id, "norm": norm},
    ).first()
    if block:
        return True
    mention_block = db.execute(
        text(
            """
            SELECT 1 FROM identity_decisions
            WHERE case_id = :cid AND canonical_person_id = :pid
              AND lower(recorded_name) = :norm
              AND decision = 'not_relevant'
            LIMIT 1
            """
        ),
        {"cid": case_id, "pid": candidate_person_id, "norm": norm},
    ).first()
    return mention_block is not None


def apply_confirmed_identity(
    db: Session,
    *,
    case_id: str,
    mention_entity_id: str,
    canonical_person_id: str,
    recorded_name: str,
    reviewer_badge: str,
    reviewer_name: str,
) -> None:
    ensure_provenance_tables(db)
    did = f"ID-{uuid.uuid4().hex[:10].upper()}"
    db.execute(
        text(
            """
            INSERT INTO identity_decisions
                (decision_id, case_id, mention_entity_id, canonical_person_id,
                 recorded_name, decision, reviewer_badge, reviewer_name)
            VALUES
                (:did, :cid, :mid, :pid, :name, 'confirmed', :badge, :rname)
            ON CONFLICT (case_id, mention_entity_id, canonical_person_id)
            DO UPDATE SET
                decision = 'confirmed',
                recorded_name = EXCLUDED.recorded_name,
                reviewer_badge = EXCLUDED.reviewer_badge,
                reviewer_name = EXCLUDED.reviewer_name,
                created_at = NOW()
            """
        ),
        {
            "did": did,
            "cid": case_id,
            "mid": mention_entity_id,
            "pid": canonical_person_id,
            "name": recorded_name[:128],
            "badge": reviewer_badge,
            "rname": reviewer_name,
        },
    )
    db.execute(
        text(
            """
            UPDATE recorded_names
            SET person_id = :pid
            WHERE case_id = :cid AND lower(recorded_name) = lower(:name)
            """
        ),
        {"pid": canonical_person_id, "cid": case_id, "name": recorded_name},
    )


def block_identity(
    db: Session,
    *,
    case_id: str,
    recorded_name: str,
    blocked_person_id: str,
    reviewer_badge: str,
    reviewer_name: str,
) -> None:
    ensure_provenance_tables(db)
    bid = f"BL-{uuid.uuid4().hex[:10].upper()}"
    norm = normalize_name(recorded_name)
    db.execute(
        text(
            """
            INSERT INTO identity_blocks
                (block_id, case_id, recorded_name, blocked_person_id,
                 reviewer_badge, reviewer_name)
            VALUES
                (:bid, :cid, :name, :pid, :badge, :rname)
            ON CONFLICT (case_id, recorded_name, blocked_person_id) DO NOTHING
            """
        ),
        {
            "bid": bid,
            "cid": case_id,
            "name": norm[:128],
            "pid": blocked_person_id,
            "badge": reviewer_badge,
            "rname": reviewer_name,
        },
    )
    did = f"ID-{uuid.uuid4().hex[:10].upper()}"
    db.execute(
        text(
            """
            INSERT INTO identity_decisions
                (decision_id, case_id, mention_entity_id, canonical_person_id,
                 recorded_name, decision, reviewer_badge, reviewer_name)
            VALUES
                (:did, :cid, :mid, :pid, :name, 'not_relevant', :badge, :rname)
            ON CONFLICT (case_id, mention_entity_id, canonical_person_id)
            DO UPDATE SET decision = 'not_relevant', created_at = NOW()
            """
        ),
        {
            "did": did,
            "cid": case_id,
            "mid": recorded_name[:32],
            "pid": blocked_person_id,
            "name": recorded_name[:128],
            "badge": reviewer_badge,
            "rname": reviewer_name,
        },
    )


def append_review_history(
    db: Session,
    *,
    case_id: str,
    entity_id: str,
    decision: str,
    notes: str | None,
    reviewer_badge: str,
    reviewer_name: str,
) -> None:
    ensure_provenance_tables(db)
    hid = f"RH-{uuid.uuid4().hex[:10].upper()}"
    db.execute(
        text(
            """
            INSERT INTO officer_review_history
                (history_id, case_id, entity_id, decision, notes,
                 reviewer_badge, reviewer_name)
            VALUES
                (:hid, :cid, :eid, :decision, :notes, :badge, :rname)
            """
        ),
        {
            "hid": hid,
            "cid": case_id,
            "eid": entity_id,
            "decision": decision,
            "notes": notes,
            "badge": reviewer_badge,
            "rname": reviewer_name,
        },
    )


def log_neo4j_sync(db: Session, *, operation: str, status: str, details: dict | None = None) -> None:
    ensure_provenance_tables(db)
    lid = f"NS-{uuid.uuid4().hex[:10].upper()}"
    db.execute(
        text(
            """
            INSERT INTO neo4j_sync_log (log_id, operation, status, details)
            VALUES (:lid, :op, :status, CAST(:details AS jsonb))
            """
        ),
        {
            "lid": lid,
            "op": operation,
            "status": status,
            "details": __import__("json").dumps(details or {}),
        },
    )


def reconcile_graph_counts(db: Session) -> dict[str, Any]:
    """Compare PostgreSQL people count vs Neo4j Person nodes (when Neo4j enabled)."""
    from app.services.neo4j_client import get_session, is_neo4j_available

    pg_people = db.execute(text("SELECT COUNT(*) FROM people")).scalar() or 0
    pg_rels = db.execute(text("SELECT COUNT(*) FROM relationships")).scalar() or 0
    result: dict[str, Any] = {
        "postgres_people": pg_people,
        "postgres_relationships": pg_rels,
        "neo4j_people": None,
        "neo4j_relationships": None,
        "consistent": True,
        "issues": [],
    }
    if not is_neo4j_available():
        result["issues"].append("Neo4j unavailable — graph is PostgreSQL-authoritative only")
        return result

    try:
        with get_session() as session:
            neo_people = session.run("MATCH (p:Person) RETURN count(p) AS c").single()["c"]
            neo_rels = session.run(
                "MATCH ()-[r:RELATED_TO|OWNS|TRANSFERRED_TO|ALIAS_OF]->() RETURN count(r) AS c"
            ).single()["c"]
        result["neo4j_people"] = neo_people
        result["neo4j_relationships"] = neo_rels
        if neo_people < pg_people:
            result["consistent"] = False
            result["issues"].append(
                f"Neo4j missing people: PG={pg_people} Neo4j={neo_people}"
            )
        log_neo4j_sync(
            db,
            operation="reconcile",
            status="ok" if result["consistent"] else "mismatch",
            details=result,
        )
    except Exception as exc:
        result["consistent"] = False
        result["issues"].append(str(exc))
        log_neo4j_sync(db, operation="reconcile", status="error", details={"error": str(exc)})
    return result
