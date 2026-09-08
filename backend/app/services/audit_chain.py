from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

GENESIS_HASH = "0" * 64

LOOKUP_LABELS = {
    "OSINT-01": "Public registry — business affiliation",
    "OSINT-02": "Published court bulletin scan",
    "OSINT-03": "Licensed address directory lookup",
    "OSINT-04": "Sanctions / watchlist screening",
}


def ensure_audit_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS audit_chain (
                entry_id VARCHAR(32) PRIMARY KEY,
                case_id VARCHAR(16),
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                action TEXT NOT NULL,
                entity_id VARCHAR(32),
                source VARCHAR(256) NOT NULL,
                operator VARCHAR(128) NOT NULL,
                lawful_basis TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}',
                prev_hash VARCHAR(64) NOT NULL,
                entry_hash VARCHAR(64) NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_audit_chain_case ON audit_chain(case_id)"
        )
    )
    db.commit()


def _canonical_payload(fields: dict[str, Any]) -> str:
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(prev_hash: str, fields: dict[str, Any]) -> str:
    material = f"{prev_hash}|{_canonical_payload(fields)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _ts_for_hash(ts: Any) -> str:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        return ts.isoformat()
    return str(ts)


def _last_hash(db: Session, case_id: str | None) -> str:
    if case_id:
        row = db.execute(
            text(
                """
                SELECT entry_hash FROM audit_chain
                WHERE case_id = :cid
                ORDER BY timestamp DESC, entry_id DESC
                LIMIT 1
                """
            ),
            {"cid": case_id},
        ).scalar()
    else:
        row = db.execute(
            text(
                """
                SELECT entry_hash FROM audit_chain
                WHERE case_id IS NULL
                ORDER BY timestamp DESC, entry_id DESC
                LIMIT 1
                """
            )
        ).scalar()
    return row or GENESIS_HASH


def append_audit_entry(
    db: Session,
    *,
    case_id: str | None,
    action: str,
    entity_id: str | None,
    source: str,
    operator: str,
    lawful_basis: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    ensure_audit_table(db)
    entry_id = f"AUD-{uuid.uuid4().hex[:10].upper()}"
    prev_hash = _last_hash(db, case_id)
    ts = datetime.now(timezone.utc)

    hash_fields = {
        "entry_id": entry_id,
        "case_id": case_id,
        "timestamp": _ts_for_hash(ts),
        "action": action,
        "entity_id": entity_id,
        "source": source,
        "operator": operator,
        "lawful_basis": lawful_basis,
        "payload": payload or {},
    }
    entry_hash = compute_entry_hash(prev_hash, hash_fields)

    db.execute(
        text(
            """
            INSERT INTO audit_chain
                (entry_id, case_id, timestamp, action, entity_id, source, operator,
                 lawful_basis, payload, prev_hash, entry_hash)
            VALUES
                (:eid, :cid, :ts, :action, :ent, :source, :op, :basis, CAST(:payload AS JSONB),
                 :prev, :hash)
            """
        ),
        {
            "eid": entry_id,
            "cid": case_id,
            "ts": ts,
            "action": action,
            "ent": entity_id,
            "source": source,
            "op": operator,
            "basis": lawful_basis,
            "payload": json.dumps(payload or {}),
            "prev": prev_hash,
            "hash": entry_hash,
        },
    )
    db.commit()
    return {"entry_id": entry_id, "entry_hash": entry_hash, "prev_hash": prev_hash}


def fetch_audit_log(
    db: Session,
    *,
    case_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_audit_table(db)
    if case_id:
        rows = db.execute(
            text(
                """
                SELECT entry_id, timestamp, action, entity_id, source, operator,
                       lawful_basis, prev_hash, entry_hash
                FROM audit_chain
                WHERE case_id = :cid
                ORDER BY timestamp DESC, entry_id DESC
                LIMIT :lim
                """
            ),
            {"cid": case_id, "lim": limit},
        ).mappings().all()
    else:
        rows = db.execute(
            text(
                """
                SELECT entry_id, timestamp, action, entity_id, source, operator,
                       lawful_basis, prev_hash, entry_hash
                FROM audit_chain
                ORDER BY timestamp DESC, entry_id DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).mappings().all()

    return [
        {
            "id": r["entry_id"],
            "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(r["timestamp"], "strftime")
            else str(r["timestamp"]),
            "action": r["action"],
            "entityId": r["entity_id"] or "",
            "source": r["source"],
            "operator": r["operator"],
            "lawfulBasis": r["lawful_basis"],
            "entryHash": r["entry_hash"],
            "prevHash": r["prev_hash"],
        }
        for r in rows
    ]


def verify_audit_chain(db: Session, *, case_id: str | None = None) -> dict[str, Any]:
    ensure_audit_table(db)
    if case_id:
        rows = db.execute(
            text(
                """
                SELECT entry_id, case_id, timestamp, action, entity_id, source, operator,
                       lawful_basis, payload, prev_hash, entry_hash
                FROM audit_chain
                WHERE case_id = :cid
                ORDER BY timestamp ASC, entry_id ASC
                """
            ),
            {"cid": case_id},
        ).mappings().all()
    else:
        rows = db.execute(
            text(
                """
                SELECT entry_id, case_id, timestamp, action, entity_id, source, operator,
                       lawful_basis, payload, prev_hash, entry_hash
                FROM audit_chain
                ORDER BY timestamp ASC, entry_id ASC
                """
            )
        ).mappings().all()

    if not rows:
        return {
            "status": "verified",
            "entries_checked": 0,
            "broken_entry_id": None,
            "message": "Empty chain — nothing to verify.",
        }

    expected_prev = GENESIS_HASH
    for row in rows:
        if row["prev_hash"] != expected_prev:
            return {
                "status": "broken",
                "entries_checked": 0,
                "broken_entry_id": row["entry_id"],
                "message": (
                    f"Chain broken at {row['entry_id']}: prev_hash mismatch "
                    f"(expected {expected_prev[:12]}…, got {row['prev_hash'][:12]}…)."
                ),
            }

        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        hash_fields = {
            "entry_id": row["entry_id"],
            "case_id": row["case_id"],
            "timestamp": _ts_for_hash(row["timestamp"]),
            "action": row["action"],
            "entity_id": row["entity_id"],
            "source": row["source"],
            "operator": row["operator"],
            "lawful_basis": row["lawful_basis"],
            "payload": payload or {},
        }
        recomputed = compute_entry_hash(row["prev_hash"], hash_fields)
        if recomputed != row["entry_hash"]:
            return {
                "status": "broken",
                "entries_checked": 0,
                "broken_entry_id": row["entry_id"],
                "message": f"Tamper detected at {row['entry_id']}: entry_hash invalid.",
            }
        expected_prev = row["entry_hash"]

    return {
        "status": "verified",
        "entries_checked": len(rows),
        "broken_entry_id": None,
        "message": f"Hash chain intact across {len(rows)} entries.",
    }
