from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import text
from sqlalchemy.orm import Session

from ai.ner_pipeline import ExtractedEntity
from app.services.neo4j_client import get_session, is_neo4j_available

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
    return " ".join(value.strip().lower().split())


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
    action: str
    matched_on: str | None = None


def _pg_resolve_person(db: Session, case_id: str | None, name: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT p.person_id FROM people p
            LEFT JOIN recorded_names rn ON rn.person_id = p.person_id
            WHERE p.name ILIKE :exact OR rn.recorded_name ILIKE :exact
            LIMIT 1
            """
        ),
        {"exact": name.strip()},
    ).scalar()
    if row:
        return row

    candidates = db.execute(
        text("SELECT person_id, name FROM people LIMIT 500")
    ).mappings().all()
    best_id = None
    best_score = 0
    q = normalize_label(name)
    for cand in candidates:
        score = fuzz.ratio(q, normalize_label(cand["name"]))
        if score > best_score and score >= 88:
            best_score = score
            best_id = cand["person_id"]
    return best_id


def _pg_resolve_phone(db: Session, phone: str) -> str | None:
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
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


def resolve_entity(
    db: Session,
    *,
    case_id: str | None,
    mention: ExtractedEntity,
) -> ResolutionResult:
    label = mention.text.strip()
    entity_type = mention.entity_type
    entity_id = _entity_id(entity_type, label)

    if entity_type == "person":
        existing = _pg_resolve_person(db, case_id, label)
        if existing:
            return ResolutionResult(entity_id=existing, action="merged", matched_on=label)
    elif entity_type == "phone":
        existing = _pg_resolve_phone(db, label)
        if existing:
            digits = "".join(c for c in label if c.isdigit())
            return ResolutionResult(
                entity_id=f"PH-{digits[-10:]}",
                action="merged",
                matched_on=label,
            )

    return ResolutionResult(entity_id=entity_id, action="created", matched_on=label)


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
    SET m.excerpt = $excerpt, m.action = $action
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

    if alias_of and alias_of != entity_id:
        with get_session() as session:
            session.run(
                """
                MATCH (a:Person {id: $alias_id}), (c:Person {id: $canonical_id})
                MERGE (a)-[:ALIAS_OF]->(c)
                """,
                {"alias_id": entity_id, "canonical_id": alias_of},
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
                excerpt: m.excerpt
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
