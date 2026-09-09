from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import text
from sqlalchemy.orm import Session

from ai.ner_pipeline import ExtractedEntity
from app.services.neo4j_client import get_session, is_neo4j_available
from app.services.provenance_service import (
    is_identity_blocked,
    normalize_name,
    officer_confirmed_link,
)

LABEL_TO_NEO4J = {
    "person": "Person",
    "phone": "Phone",
    "account": "Account",
    "organization": "Organization",
    "location": "Location",
}

TYPE_TO_RESPONSE = {
    "person": "PERSON",
    "phone": "PHONE",
    "account": "ACCOUNT",
    "organization": "ORGANIZATION",
    "location": "LOCATION",
}

def normalize_label(value: str) -> str:
    return normalize_name(value)


def provisional_person_id(
    case_id: str | None,
    source_id: str | None,
    mention_start: int,
    name: str,
) -> str:
    """Unique ID per mention — identical names never share a provisional ID."""
    scope = case_id or "GLOBAL"
    sid = source_id or "NO-SRC"
    digest = hashlib.sha256(
        f"{scope}:{sid}:{mention_start}:{normalize_label(name)}".encode()
    ).hexdigest()[:10].upper()
    return f"PU-{digest}"


def phones_near_mention(
    text: str,
    person_start: int,
    person_end: int,
    mentions: list[ExtractedEntity],
    *,
    window: int = 120,
) -> list[str]:
    """Phones within character window of a person mention — not whole-document phones."""
    phones: list[str] = []
    for mention in mentions:
        if mention.entity_type != "phone":
            continue
        dist = min(abs(mention.start - person_end), abs(mention.end - person_start))
        if dist <= window:
            phones.append(mention.text)
    return phones


def _entity_id(entity_type: str, label: str) -> str:
    norm = normalize_label(label)
    if entity_type == "phone":
        digits = "".join(c for c in label if c.isdigit())
        return f"PH-{digits[-10:]}" if digits else f"PH-{hashlib.md5(label.encode()).hexdigest()[:8]}"
    if entity_type == "account":
        return f"AC-{label}"
    digest = hashlib.md5(f"{entity_type}:{norm}".encode()).hexdigest()[:10].upper()
    prefix = {"person": "P", "organization": "ORG", "location": "LOC"}.get(entity_type, "E")
    return f"{prefix}-{digest}"


@dataclass
class ResolutionResult:
    entity_id: str
    action: str  # merged | created | suggested_match
    matched_on: str | None = None
    match_reason: str | None = None
    requires_review: bool = False
    suggested_person_id: str | None = None


def _person_ids_in_case(db: Session, case_id: str) -> set[str]:
    """People linked to a case via relationships, CDR phones, transactions, or case FIR aliases."""
    rows = db.execute(
        text(
            """
            SELECT DISTINCT person_id FROM (
                SELECT person_id_a AS person_id FROM relationships WHERE case_id = :cid
                UNION
                SELECT person_id_b FROM relationships WHERE case_id = :cid
                UNION
                SELECT ph.person_id FROM cdr c
                    JOIN phones ph ON ph.phone_number IN (c.caller_phone, c.receiver_phone)
                    WHERE c.case_id = :cid
                UNION
                SELECT ba.person_id FROM transactions t
                    JOIN bank_accounts ba ON ba.account_number IN (t.sender_account, t.receiver_account)
                    WHERE t.case_id = :cid
                UNION
                SELECT rn.person_id FROM recorded_names rn
                    WHERE rn.case_id = :cid AND rn.person_id IS NOT NULL
            ) q
            WHERE person_id IS NOT NULL
            """
        ),
        {"cid": case_id},
    ).scalars().all()
    return set(rows)


def _fetch_person_row(db: Session, person_id: str) -> dict | None:
    row = db.execute(
        text("SELECT person_id, name, city FROM people WHERE person_id = :pid"),
        {"pid": person_id},
    ).mappings().first()
    return dict(row) if row else None


def _pg_resolve_phone(db: Session, phone: str, case_id: str | None = None) -> str | None:
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
    if case_id:
        row = db.execute(
            text(
                """
                SELECT ph.phone_id FROM phones ph
                JOIN (
                    SELECT DISTINCT unnest(ARRAY[caller_phone, receiver_phone]) AS num
                    FROM cdr WHERE case_id = :cid
                ) c ON c.num = ph.phone_number
                WHERE ph.phone_number LIKE :pattern
                LIMIT 1
                """
            ),
            {"cid": case_id, "pattern": f"%{digits[-10:]}"},
        ).scalar()
        if row:
            return row
    row = db.execute(
        text(
            """
            SELECT phone_id FROM phones
            WHERE phone_number LIKE :pattern
            LIMIT 1
            """
        ),
        {"pattern": f"%{digits[-10:]}"},
    ).scalar()
    return row


def _pg_resolve_person(
    db: Session,
    case_id: str | None,
    name: str,
    *,
    context_phones: list[str] | None = None,
    context_city: str | None = None,
    source_id: str | None = None,
    mention_start: int = 0,
) -> ResolutionResult:
    label = name.strip()
    provisional_id = provisional_person_id(case_id, source_id, mention_start, label)

    if not case_id:
        return ResolutionResult(
            entity_id=provisional_id,
            action="created",
            matched_on=label,
            match_reason="No case scope — new provisional entity",
            requires_review=True,
        )

    case_people = _person_ids_in_case(db, case_id)
    q_norm = normalize_label(label)

    # Case-scoped alias table with confirmed person_id
    alias_row = db.execute(
        text(
            """
            SELECT rn.person_id, rn.recorded_name
            FROM recorded_names rn
            WHERE rn.case_id = :cid AND rn.person_id IS NOT NULL
              AND lower(rn.recorded_name) = lower(:name)
            LIMIT 1
            """
        ),
        {"cid": case_id, "name": label},
    ).mappings().first()
    if alias_row and alias_row["person_id"] in case_people:
        pid = alias_row["person_id"]
        if is_identity_blocked(db, case_id=case_id, name=label, candidate_person_id=pid):
            pass
        elif officer_confirmed_link(db, case_id=case_id, name=label, person_id=pid):
            return ResolutionResult(
                entity_id=pid,
                action="merged",
                matched_on=alias_row["recorded_name"],
                match_reason="Officer-confirmed alias link",
                requires_review=False,
            )

    exact_candidates: list[tuple[str, str]] = []
    for pid in case_people:
        if is_identity_blocked(db, case_id=case_id, name=label, candidate_person_id=pid):
            continue
        person = _fetch_person_row(db, pid)
        if not person:
            continue
        if normalize_label(person["name"]) == q_norm:
            exact_candidates.append((pid, person["name"]))

    corroborating_phone = False
    if context_phones and exact_candidates:
        digits_set = {"".join(c for c in p if c.isdigit())[-10:] for p in context_phones if p}
        for pid, _ in exact_candidates:
            owned = db.execute(
                text(
                    """
                    SELECT phone_number FROM phones WHERE person_id = :pid
                    """
                ),
                {"pid": pid},
            ).scalars().all()
            for num in owned:
                d = "".join(c for c in num if c.isdigit())[-10:]
                if d in digits_set:
                    corroborating_phone = True
                    break
            if corroborating_phone:
                break

    corroborating_city = False
    if context_city and exact_candidates:
        city_norm = normalize_label(context_city)
        for pid, _ in exact_candidates:
            person = _fetch_person_row(db, pid)
            if person and normalize_label(person["city"]) == city_norm:
                corroborating_city = True
                break

    if len(exact_candidates) == 1 and (corroborating_phone or corroborating_city):
        pid, pname = exact_candidates[0]
        reason = "Exact name + corroborating phone in document" if corroborating_phone else "Exact name + matching city"
        return ResolutionResult(
            entity_id=pid,
            action="merged",
            matched_on=pname,
            match_reason=reason,
            requires_review=False,
        )

    if len(exact_candidates) > 1:
        return ResolutionResult(
            entity_id=provisional_id,
            action="suggested_match",
            matched_on=label,
            match_reason=f"{len(exact_candidates)} case persons share exact name — requires officer review",
            requires_review=True,
            suggested_person_id=exact_candidates[0][0],
        )

    if len(exact_candidates) == 1:
        pid, pname = exact_candidates[0]
        return ResolutionResult(
            entity_id=provisional_id,
            action="suggested_match",
            matched_on=pname,
            match_reason="Exact name only — insufficient without phone or city corroboration",
            requires_review=True,
            suggested_person_id=pid,
        )

    # Fuzzy within case scope only — never auto-merge
    best_id = None
    best_name = None
    best_score = 0
    for pid in case_people:
        if is_identity_blocked(db, case_id=case_id, name=label, candidate_person_id=pid):
            continue
        person = _fetch_person_row(db, pid)
        if not person:
            continue
        score = fuzz.ratio(q_norm, normalize_label(person["name"]))
        alias_scores = db.execute(
            text(
                """
                SELECT recorded_name FROM recorded_names
                WHERE case_id = :cid AND person_id = :pid
                """
            ),
            {"cid": case_id, "pid": pid},
        ).scalars().all()
        for alias in alias_scores:
            score = max(score, fuzz.ratio(q_norm, normalize_label(alias)))
        if score > best_score and score >= 88:
            best_score = score
            best_id = pid
            best_name = person["name"]

    if best_id:
        return ResolutionResult(
            entity_id=provisional_id,
            action="suggested_match",
            matched_on=best_name,
            match_reason=f"Fuzzy name match ({best_score}%) — officer must confirm identity",
            requires_review=True,
            suggested_person_id=best_id,
        )

    return ResolutionResult(
        entity_id=provisional_id,
        action="created",
        matched_on=label,
        match_reason="No case-scoped match — new provisional entity",
        requires_review=False,
    )


def resolve_entity(
    db: Session,
    *,
    case_id: str | None,
    mention: ExtractedEntity,
    context_phones: list[str] | None = None,
    context_city: str | None = None,
    source_id: str | None = None,
    all_mentions: list[ExtractedEntity] | None = None,
    source_text: str | None = None,
) -> ResolutionResult:
    label = mention.text.strip()
    entity_type = "person" if mention.entity_type == "alias" else mention.entity_type

    if entity_type == "person":
        local_phones = context_phones
        if all_mentions and source_text is not None:
            local_phones = phones_near_mention(
                source_text, mention.start, mention.end, all_mentions
            )
        return _pg_resolve_person(
            db,
            case_id,
            label,
            context_phones=local_phones,
            context_city=context_city,
            source_id=source_id,
            mention_start=mention.start,
        )
    if entity_type == "phone":
        existing = _pg_resolve_phone(db, label, case_id)
        if existing:
            digits = "".join(c for c in label if c.isdigit())
            return ResolutionResult(
                entity_id=f"PH-{digits[-10:]}",
                action="merged",
                matched_on=label,
                match_reason="Phone number matched case CDR or registry",
                requires_review=False,
            )

    return ResolutionResult(
        entity_id=_entity_id(entity_type, label),
        action="created",
        matched_on=label,
        match_reason="New entity extracted from document",
        requires_review=False,
    )


def merge_entity_in_neo4j(
    *,
    entity_id: str,
    entity_type: str,
    label: str,
    case_id: str | None,
    source_type: str,
    source_id: str,
    excerpt: str,
    action: str,
    alias_of: str | None = None,
    relationship_kind: str = "observed",
) -> None:
    if not is_neo4j_available():
        return

    node_label = LABEL_TO_NEO4J.get(entity_type, "Person")
    norm = normalize_label(label)

    cypher = f"""
    MERGE (e:{node_label} {{id: $entity_id}})
    ON CREATE SET
        e.label = $label,
        e.normalized_label = $norm,
        e.case_id = $case_id,
        e.created_at = datetime()
    ON MATCH SET
        e.label = coalesce(e.label, $label),
        e.updated_at = datetime()
    WITH e
    MERGE (s:SourceDocument {{source_id: $source_id}})
    ON CREATE SET
        s.source_type = $source_type,
        s.case_id = $case_id,
        s.text = $excerpt,
        s.ingested_at = datetime()
    MERGE (e)-[m:MENTIONED_IN]->(s)
    SET m.excerpt = $excerpt, m.action = $action, m.relationship_kind = $rel_kind
    """
    params = {
        "entity_id": entity_id,
        "label": label,
        "norm": norm,
        "case_id": case_id,
        "source_type": source_type,
        "source_id": source_id,
        "excerpt": excerpt[:500],
        "action": action,
        "rel_kind": relationship_kind,
    }

    if entity_type == "phone":
        digits = "".join(c for c in label if c.isdigit())
        params["phone_number"] = digits[-10:] if digits else label
        cypher = cypher.replace(
            "e.updated_at = datetime()",
            "e.updated_at = datetime(), e.phone_number = $phone_number",
        )

    if entity_type == "account":
        params["account_number"] = label
        cypher = cypher.replace(
            "e.updated_at = datetime()",
            "e.updated_at = datetime(), e.account_number = $account_number",
        )

    with get_session() as session:
        session.run(cypher, params).consume()

    if alias_of and alias_of != entity_id and action == "merged":
        with get_session() as session:
            session.run(
                """
                MATCH (a:Person {id: $alias_id}), (c:Person {id: $canonical_id})
                MERGE (a)-[r:ALIAS_OF]->(c)
                SET r.confirmed = true
                """,
                {"alias_id": entity_id, "canonical_id": alias_of},
            ).consume()


def merge_transfer_in_neo4j(
    *,
    sender_account: str,
    receiver_account: str,
    case_id: str | None,
    source_id: str,
    transaction_id: str,
    amount: str | float,
) -> None:
    if not is_neo4j_available():
        return

    sender_id = f"AC-{sender_account}"
    receiver_id = f"AC-{receiver_account}"
    excerpt = f"Transfer {amount} in {transaction_id}"

    for entity_id, label, entity_type in (
        (sender_id, sender_account, "account"),
        (receiver_id, receiver_account, "account"),
    ):
        merge_entity_in_neo4j(
            entity_id=entity_id,
            entity_type=entity_type,
            label=label,
            case_id=case_id,
            source_type="transactions",
            source_id=source_id,
            excerpt=excerpt,
            action="merged",
            relationship_kind="observed",
        )

    with get_session() as session:
        session.run(
            """
            MATCH (a:Account {id: $sender_id}), (b:Account {id: $receiver_id})
            MERGE (a)-[t:TRANSFERRED_TO {transaction_id: $txn_id}]->(b)
            ON CREATE SET
                t.amount = $amount,
                t.case_id = $case_id,
                t.source_id = $source_id,
                t.created_at = datetime(),
                t.relationship_kind = 'observed'
            """,
            {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "txn_id": transaction_id,
                "amount": str(amount),
                "case_id": case_id,
                "source_id": source_id,
            },
        ).consume()


def get_entity_from_neo4j(entity_id: str) -> dict | None:
    if not is_neo4j_available():
        return None

    with get_session() as session:
        record = session.run(
            """
            MATCH (e {id: $entity_id})
            OPTIONAL MATCH (e)-[m:MENTIONED_IN]->(s:SourceDocument)
            RETURN e, collect({
                source_type: s.source_type,
                source_id: s.source_id,
                excerpt: m.excerpt,
                relationship_kind: coalesce(m.relationship_kind, 'observed')
            }) AS sources
            """,
            {"entity_id": entity_id},
        ).single()

    if not record or record["e"] is None:
        return None

    node = dict(record["e"])
    sources = [s for s in record["sources"] if s.get("source_id")]
    aliases: list[str] = []
    if node.get("normalized_label"):
        with get_session() as session:
            alias_rows = session.run(
                """
                MATCH (a:Person)-[:ALIAS_OF]->(c {id: $entity_id})
                RETURN a.label AS label
                """,
                {"entity_id": entity_id},
            )
            aliases = [r["label"] for r in alias_rows if r["label"]]

    labels = list(record["e"].labels) if hasattr(record["e"], "labels") else []
    node_type = labels[0] if labels else "Person"
    type_map = {
        "Person": "PERSON",
        "Phone": "PHONE",
        "Account": "ACCOUNT",
        "Organization": "ORGANIZATION",
        "Location": "LOCATION",
    }

    return {
        "id": node.get("id", entity_id),
        "type": type_map.get(node_type, "PERSON"),
        "label": node.get("label", entity_id),
        "sources": sources,
        "resolved_aliases": aliases,
    }


def new_source_id(prefix: str = "SRC") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"
