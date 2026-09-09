from __future__ import annotations

import csv
import io
import logging
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

logger = logging.getLogger(__name__)


def _excerpt(text: str, start: int, end: int, radius: int = 60) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    return text[lo:hi].replace("\n", " ").strip()


def _persist_recorded_name(
    db: Session,
    *,
    case_id: str | None,
    source_type: str,
    source_id: str,
    name: str,
    person_id: str | None,
    variant_type: str = "ner_extract",
) -> None:
    record_id = f"RN-{source_id[-8:]}-{len(name)}"
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
            "rid": record_id[:16],
            "cid": case_id,
            "stype": source_type,
            "sid": source_id,
            "name": name[:128],
            "vtype": variant_type,
            "pid": person_id if person_id and person_id.startswith("P") else None,
        },
    )


def ingest_text_document(
    db: Session,
    *,
    text_content: str,
    source_type: str,
    case_id: str | None,
    source_id: str | None = None,
) -> IngestResponse:
    source_id = source_id or new_source_id()
    mentions_raw = extract_entities(text_content)
    context_phones = [m.text for m in mentions_raw if m.entity_type == "phone"]
    mentions: list[ExtractedMention] = []
    merged = 0
    last_person_id: str | None = None

    for mention in mentions_raw:
        alias_of = None
        if mention.entity_type == "alias" and last_person_id:
            alias_of = last_person_id

        resolution = resolve_entity(
            db,
            case_id=case_id,
            mention=mention,
            context_phones=context_phones,
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

        if mention.entity_type == "person":
            pid = resolution.entity_id if resolution.action == "merged" else None
            _persist_recorded_name(
                db,
                case_id=case_id,
                source_type=source_type,
                source_id=source_id,
                name=mention.text,
                person_id=pid,
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
    fir_id = f"FIR-{source_id[-6:]}"

    if case_id:
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
    surv_id = f"SUR-{source_id[-6:]}"

    if case_id:
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
    reader = csv.DictReader(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
    rows = list(reader)
    source_id = new_source_id("CDR")
    count = 0

    for row in rows:
        caller = row.get("caller_phone") or row.get("caller") or ""
        receiver = row.get("receiver_phone") or row.get("receiver") or ""
        if not caller or not receiver:
            continue

        cdr_id = row.get("cdr_id") or f"CDR-{count:05d}"
        db.execute(
            text(
                """
                INSERT INTO cdr (cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id)
                VALUES (:id, :caller, :receiver, COALESCE(:ts, NOW()), COALESCE(:dur, 0), COALESCE(:tower, 'Unknown'), :cid)
                ON CONFLICT (cdr_id) DO NOTHING
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
        )

        if is_neo4j_available():
            for phone, role in ((caller, "caller"), (receiver, "receiver")):
                merge_entity_in_neo4j(
                    entity_id=f"PH-{''.join(c for c in phone if c.isdigit())[-10:]}",
                    entity_type="phone",
                    label=phone,
                    case_id=case_id,
                    source_type="cdr",
                    source_id=source_id,
                    excerpt=f"{role} in CDR {cdr_id}",
                    action="merged",
                )
        count += 1

    db.commit()
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
    reader = csv.DictReader(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
    rows = list(reader)
    source_id = new_source_id("TXN")
    count = 0

    for row in rows:
        sender = row.get("sender_account") or row.get("sender") or ""
        receiver = row.get("receiver_account") or row.get("receiver") or ""
        if not sender or not receiver:
            continue

        txn_id = row.get("transaction_id") or f"TXN-{count:05d}"
        db.execute(
            text(
                """
                INSERT INTO transactions (transaction_id, sender_account, receiver_account, amount, timestamp, case_id)
                VALUES (:id, :sender, :receiver, COALESCE(:amt, 0), COALESCE(:ts, NOW()), :cid)
                ON CONFLICT (transaction_id) DO NOTHING
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
        )
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
