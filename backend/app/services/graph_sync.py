from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.entity_resolution import merge_entity_in_neo4j
from app.services.neo4j_client import get_session, is_neo4j_available
from app.services.neo4j_schema import ensure_schema

logger = logging.getLogger(__name__)


def sync_postgres_to_neo4j(db: Session) -> dict[str, int]:
    """Bootstrap Neo4j graph from existing PostgreSQL crime_network data."""
    if not is_neo4j_available():
        return {"synced": 0}

    ensure_schema()
    counts = {"people": 0, "phones": 0, "relationships": 0, "documents": 0}

    people = db.execute(text("SELECT person_id, name, city FROM people")).mappings().all()
    for person in people:
        merge_entity_in_neo4j(
            entity_id=person["person_id"],
            entity_type="person",
            label=person["name"],
            case_id=None,
            source_type="people.csv",
            source_id=person["person_id"],
            excerpt=f"Canonical identity: {person['name']}, {person['city']}",
            action="merged",
        )
        counts["people"] += 1

    phones = db.execute(
        text("SELECT phone_id, phone_number, person_id FROM phones")
    ).mappings().all()
    for phone in phones:
        digits = "".join(c for c in phone["phone_number"] if c.isdigit())
        merge_entity_in_neo4j(
            entity_id=f"PH-{digits[-10:]}",
            entity_type="phone",
            label=phone["phone_number"],
            case_id=None,
            source_type="phones.csv",
            source_id=phone["phone_id"],
            excerpt=f"Registered to {phone['person_id']}",
            action="merged",
        )
        counts["phones"] += 1

        if is_neo4j_available():
            with get_session() as session:
                session.run(
                    """
                    MATCH (p:Person {id: $pid}), (ph:Phone {id: $phid})
                    MERGE (p)-[:OWNS]->(ph)
                    """,
                    {"pid": phone["person_id"], "phid": f"PH-{digits[-10:]}"},
                ).consume()

    rels = db.execute(
        text(
            """
            SELECT person_id_a, person_id_b, relationship_type, case_id
            FROM relationships
            """
        )
    ).mappings().all()
    for rel in rels:
        if not is_neo4j_available():
            break
        with get_session() as session:
            session.run(
                """
                MATCH (a:Person {id: $a}), (b:Person {id: $b})
                MERGE (a)-[r:RELATED_TO {type: $rtype, case_id: $cid}]->(b)
                """,
                {
                    "a": rel["person_id_a"],
                    "b": rel["person_id_b"],
                    "rtype": rel["relationship_type"],
                    "cid": rel["case_id"],
                },
            ).consume()
        counts["relationships"] += 1

    fir_rows = db.execute(
        text("SELECT fir_id, case_id, complaint_text FROM fir LIMIT 200")
    ).mappings().all()
    for fir in fir_rows:
        merge_entity_in_neo4j(
            entity_id=fir["fir_id"],
            entity_type="person",
            label=fir["fir_id"],
            case_id=fir["case_id"],
            source_type="fir",
            source_id=fir["fir_id"],
            excerpt=fir["complaint_text"][:500],
            action="merged",
        )
        if is_neo4j_available():
            with get_session() as session:
                session.run(
                    """
                    MERGE (s:SourceDocument {source_id: $sid})
                    SET s.source_type = 'fir', s.case_id = $cid, s.text = $text
                    """,
                    {
                        "sid": fir["fir_id"],
                        "cid": fir["case_id"],
                        "text": fir["complaint_text"][:2000],
                    },
                ).consume()
        counts["documents"] += 1

    aliases = db.execute(
        text(
            """
            SELECT person_id, recorded_name, source_type, source_id
            FROM recorded_names WHERE person_id IS NOT NULL
            """
        )
    ).mappings().all()
    for alias in aliases:
        merge_entity_in_neo4j(
            entity_id=alias["person_id"],
            entity_type="person",
            label=alias["recorded_name"],
            case_id=None,
            source_type=alias["source_type"],
            source_id=alias["source_id"],
            excerpt=f"Alias: {alias['recorded_name']}",
            action="merged",
            alias_of=alias["person_id"],
        )

    logger.info("Neo4j sync complete: %s", counts)
    return counts
