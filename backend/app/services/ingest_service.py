from __future__ import annotations

import csv
import hashlib
import io
import logging
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from ai.ner_pipeline import extract_entities
from app.schemas.ingest import ExtractedMention, IngestResponse
from app.services.entity_resolution import (
    merge_entity_in_neo4j,
    merge_transfer_in_neo4j,
    new_source_id,
    resolve_entity,
)
from app.services.network_analysis import invalidate_case_analysis
from app.services.neo4j_client import is_neo4j_available
from app.services.provenance_service import (
    content_hash,
    find_duplicate_source,
    record_provenance,
    register_ingest_source,
)

logger = logging.getLogger(__name__)


def _excerpt(text: str, start: int, end: int, radius: int = 60) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    return text[lo:hi].replace("\n", " ").strip()


def _record_id(source_id: str, name: str, start: int) -> str:
    digest = hashlib.md5(f"{source_id}:{start}:{name}".encode()).hexdigest()[:8].upper()
    return f"RN-{digest}"


def _persist_recorded_name(
    db: Session,
    *,
    case_id: str | None,
    source_type: str,
    source_id: str,
    name: str,
    person_id: str | None,
    variant_type: str = "ner_extract",
    record_id: str | None = None,
) -> str:
    rid = record_id or _record_id(source_id, name, len(name))
    db.execute(
        text(
            """
            INSERT INTO recorded_names
                (record_id, case_id, source_type, source_id, recorded_name, variant_type, person_id, is_erroneous)
            VALUES
                (:rid, :cid, :stype, :sid, :name, :vtype, :pid, false)
            ON CONFLICT (record_id) DO NOTHING
            """
        ),
        {
            "rid": rid[:16],
            "cid": case_id,
            "stype": source_type,
            "sid": source_id,
            "name": name[:128],
            "vtype": variant_type,
            "pid": person_id if person_id and person_id.startswith("P") else None,
        },
    )
    return rid[:16]


def _begin_ingest(
    db: Session,
    *,
    case_id: str | None,
    source_type: str,
    text_content: str,
    source_id: str | None = None,
) -> tuple[str, bool]:
    """
    Register source and detect duplicates.
    Returns (source_id, is_duplicate).
    """
    if not case_id:
        return source_id or new_source_id(), False

    digest = content_hash(text_content)
    existing = find_duplicate_source(db, case_id=case_id, source_type=source_type, digest=digest)
    if existing:
        return existing["source_id"], True

    sid = register_ingest_source(
        db,
        case_id=case_id,
        source_type=source_type,
        digest=digest,
        byte_size=len(text_content.encode("utf-8")),
        source_id=source_id,
    )
    return sid, False


def ingest_text_document(
    db: Session,
    *,
    text_content: str,
    source_type: str,
    case_id: str | None,
    source_id: str | None = None,
) -> IngestResponse:
    source_id, is_duplicate = _begin_ingest(
        db,
        case_id=case_id,
        source_type=source_type,
        text_content=text_content,
        source_id=source_id,
    )
    if is_duplicate:
        db.commit()
        return IngestResponse(
            status="duplicate",
            source_id=source_id,
            source_type=source_type,
            case_id=case_id,
            records_received=0,
            entities_extracted=0,
            entities_merged=0,
            mentions=[],
        )

    mentions_raw = extract_entities(text_content)
    mentions: list[ExtractedMention] = []
    merged = 0
    last_person_id: str | None = None

    try:
        for mention in mentions_raw:
            alias_of = None
            if mention.entity_type == "alias" and last_person_id:
                alias_of = last_person_id

            resolution = resolve_entity(
                db,
                case_id=case_id,
                mention=mention,
                source_id=source_id,
                all_mentions=mentions_raw,
                source_text=text_content,
            )
            if resolution.action == "merged":
                merged += 1

            effective_id = (
                resolution.suggested_person_id
                if resolution.action == "suggested_match" and resolution.suggested_person_id
                else resolution.entity_id
            )
            if mention.entity_type == "person" and resolution.action == "merged":
                last_person_id = resolution.entity_id
            elif mention.entity_type == "person":
                last_person_id = effective_id

            excerpt = _excerpt(text_content, mention.start, mention.end)
            rel_kind = "observed" if resolution.action == "merged" else "suggested"
            record_id = None
            if mention.entity_type in ("person", "alias"):
                pid = resolution.entity_id if resolution.action == "merged" else None
                record_id = _persist_recorded_name(
                    db,
                    case_id=case_id,
                    source_type=source_type,
                    source_id=source_id,
                    name=mention.text,
                    person_id=pid,
                    record_id=_record_id(source_id, mention.text, mention.start),
                )

            record_provenance(
                db,
                case_id=case_id,
                entity_id=resolution.entity_id,
                source_type=source_type,
                source_id=source_id,
                record_id=record_id,
                excerpt=excerpt,
                extraction_method="spacy_ner" if mention.entity_type == "person" else "regex_extract",
                relationship_kind=rel_kind,
                resolution_action=resolution.action,
            )

            merge_entity_in_neo4j(
                entity_id=resolution.entity_id,
                entity_type="person" if mention.entity_type == "alias" else mention.entity_type,
                label=mention.text,
                case_id=case_id,
                source_type=source_type,
                source_id=source_id,
                excerpt=excerpt,
                action=resolution.action,
                alias_of=alias_of if resolution.action == "merged" else None,
                relationship_kind=rel_kind,
            )

            mentions.append(
                ExtractedMention(
                    text=mention.text,
                    entity_type=mention.entity_type,
                    resolved_entity_id=resolution.entity_id,
                    action=resolution.action,
                    source_excerpt=excerpt,
                    match_reason=resolution.match_reason,
                    requires_review=resolution.requires_review,
                    suggested_person_id=resolution.suggested_person_id,
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Ingest failed for source %s", source_id)
        raise

    if case_id:
        invalidate_case_analysis(case_id)

    return IngestResponse(
        status="success",
        source_id=source_id,
        source_type=source_type,
        case_id=case_id,
        records_received=1,
        entities_extracted=len(mentions),
        entities_merged=merged,
        mentions=mentions,
    )


def ingest_fir_file(
    db: Session,
    *,
    file_bytes: bytes,
    case_id: str | None,
) -> IngestResponse:
    text_content = file_bytes.decode("utf-8", errors="replace")
    source_id = new_source_id("FIR")
    digest = content_hash(text_content)
    fir_id = f"FIR-{digest[:8].upper()}"

    if case_id:
        try:
            db.execute(
                text(
                    """
                    INSERT INTO fir (fir_id, case_id, date, police_station, complaint_text)
                    VALUES (:fid, :cid, CURRENT_DATE, 'Ingest API', :text)
                    ON CONFLICT (fir_id) DO UPDATE SET complaint_text = EXCLUDED.complaint_text
                    """
                ),
                {"fid": fir_id, "cid": case_id, "text": text_content[:50000]},
            )
        except Exception:
            db.rollback()
            raise

    result = ingest_text_document(
        db,
        text_content=text_content,
        source_type="fir",
        case_id=case_id,
        source_id=source_id,
    )
    result.source_id = source_id
    return result


def ingest_surveillance_file(
    db: Session,
    *,
    file_bytes: bytes,
    case_id: str | None,
) -> IngestResponse:
    text_content = file_bytes.decode("utf-8", errors="replace")
    source_id = new_source_id("SUR")
    digest = content_hash(text_content)
    surv_id = f"SUR-{digest[:8].upper()}"

    if case_id:
        try:
            db.execute(
                text(
                    """
                    INSERT INTO surveillance (surveillance_id, case_id, timestamp, location, report_text)
                    VALUES (:sid, :cid, :ts, 'Ingest API', :text)
                    ON CONFLICT (surveillance_id) DO UPDATE SET report_text = EXCLUDED.report_text
                    """
                ),
                {
                    "sid": surv_id,
                    "cid": case_id,
                    "ts": datetime.utcnow(),
                    "text": text_content[:50000],
                },
            )
        except Exception:
            db.rollback()
            raise

    result = ingest_text_document(
        db,
        text_content=text_content,
        source_type="surveillance",
        case_id=case_id,
        source_id=source_id,
    )
    result.source_id = source_id
    return result


def preview_ingest_text(text_content: str) -> dict:
    from ai.ner_pipeline import extract_entities, nlp_engine_name, spacy_available

    mentions_raw = extract_entities(text_content)
    entities = []
    for mention in mentions_raw:
        entities.append(
            {
                "text": mention.text,
                "entity_type": mention.entity_type,
                "confidence": mention.confidence,
                "source_excerpt": _excerpt(text_content, mention.start, mention.end),
            }
        )
    return {
        "engine": nlp_engine_name(),
        "spacy_available": spacy_available(),
        "entities_extracted": len(entities),
        "entities": entities,
    }


def ingest_cdr_csv(db: Session, *, file_bytes: bytes, case_id: str | None) -> IngestResponse:
    raw = file_bytes.decode("utf-8", errors="replace")
    digest = content_hash(raw)
    if case_id:
        existing = find_duplicate_source(db, case_id=case_id, source_type="cdr", digest=digest)
        if existing:
            return IngestResponse(
                status="duplicate",
                source_id=existing["source_id"],
                source_type="cdr",
                case_id=case_id,
                records_received=0,
                entities_extracted=0,
                entities_merged=0,
                mentions=[],
            )

    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    source_id = register_ingest_source(
        db,
        case_id=case_id or "UNKNOWN",
        source_type="cdr",
        digest=digest,
        byte_size=len(file_bytes),
        source_id=new_source_id("CDR"),
    ) if case_id else new_source_id("CDR")
    count = 0
    skipped = 0

    try:
        for row in rows:
            caller = row.get("caller_phone") or row.get("caller") or ""
            receiver = row.get("receiver_phone") or row.get("receiver") or ""
            if not caller or not receiver:
                continue

            cdr_id = row.get("cdr_id") or f"CDR-{count:05d}"
            result = db.execute(
                text(
                    """
                    INSERT INTO cdr (cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id)
                    VALUES (:id, :caller, :receiver, COALESCE(:ts, NOW()), COALESCE(:dur, 0), COALESCE(:tower, 'Unknown'), :cid)
                    ON CONFLICT (cdr_id) DO NOTHING
                    RETURNING cdr_id
                    """
                ),
                {
                    "id": cdr_id,
                    "caller": caller,
                    "receiver": receiver,
                    "ts": row.get("timestamp"),
                    "dur": int(row.get("duration_seconds") or 0),
                    "tower": row.get("tower_location") or "Unknown",
                    "cid": case_id or row.get("case_id"),
                },
            ).scalar()
            if not result:
                skipped += 1
                continue

            if is_neo4j_available():
                for phone, role in ((caller, "caller"), (receiver, "receiver")):
                    ph_id = f"PH-{''.join(c for c in phone if c.isdigit())[-10:]}"
                    merge_entity_in_neo4j(
                        entity_id=ph_id,
                        entity_type="phone",
                        label=phone,
                        case_id=case_id,
                        source_type="cdr",
                        source_id=source_id,
                        excerpt=f"{role} in CDR {cdr_id}",
                        action="merged",
                    )
                    record_provenance(
                        db,
                        case_id=case_id,
                        entity_id=ph_id,
                        source_type="cdr",
                        source_id=source_id,
                        record_id=cdr_id,
                        excerpt=f"{role} in CDR {cdr_id}",
                        extraction_method="csv_row",
                        relationship_kind="observed",
                        resolution_action="merged",
                    )
            count += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    if case_id:
        invalidate_case_analysis(case_id)
    return IngestResponse(
        status="success",
        source_id=source_id,
        source_type="cdr",
        case_id=case_id,
        records_received=count,
        entities_extracted=count * 2,
        entities_merged=count * 2,
    )


def ingest_transactions_csv(
    db: Session,
    *,
    file_bytes: bytes,
    case_id: str | None,
) -> IngestResponse:
    raw = file_bytes.decode("utf-8", errors="replace")
    digest = content_hash(raw)
    if case_id:
        existing = find_duplicate_source(db, case_id=case_id, source_type="transactions", digest=digest)
        if existing:
            return IngestResponse(
                status="duplicate",
                source_id=existing["source_id"],
                source_type="transactions",
                case_id=case_id,
                records_received=0,
                entities_extracted=0,
                entities_merged=0,
                mentions=[],
            )

    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    source_id = register_ingest_source(
        db,
        case_id=case_id or "UNKNOWN",
        source_type="transactions",
        digest=digest,
        byte_size=len(file_bytes),
        source_id=new_source_id("TXN"),
    ) if case_id else new_source_id("TXN")
    count = 0

    try:
        for row in rows:
            sender = row.get("sender_account") or row.get("sender") or ""
            receiver = row.get("receiver_account") or row.get("receiver") or ""
            if not sender or not receiver:
                continue

            txn_id = row.get("transaction_id") or f"TXN-{count:05d}"
            inserted = db.execute(
                text(
                    """
                    INSERT INTO transactions (transaction_id, sender_account, receiver_account, amount, timestamp, case_id)
                    VALUES (:id, :sender, :receiver, COALESCE(:amt, 0), COALESCE(:ts, NOW()), :cid)
                    ON CONFLICT (transaction_id) DO NOTHING
                    RETURNING transaction_id
                    """
                ),
                {
                    "id": txn_id,
                    "sender": sender,
                    "receiver": receiver,
                    "amt": row.get("amount") or 0,
                    "ts": row.get("timestamp"),
                    "cid": case_id or row.get("case_id"),
                },
            ).scalar()
            if not inserted:
                continue

            if is_neo4j_available():
                merge_transfer_in_neo4j(
                    sender_account=sender,
                    receiver_account=receiver,
                    case_id=case_id or row.get("case_id"),
                    source_id=source_id,
                    transaction_id=txn_id,
                    amount=row.get("amount") or 0,
                )
            count += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    if case_id:
        invalidate_case_analysis(case_id)
    return IngestResponse(
        status="success",
        source_id=source_id,
        source_type="transactions",
        case_id=case_id,
        records_received=count,
        entities_extracted=count * 2,
        entities_merged=count * 2 if is_neo4j_available() else 0,
    )
