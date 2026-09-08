from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.neo4j_client import get_session, is_neo4j_available

logger = logging.getLogger(__name__)


def _pg_fulltext_hits(
    db: Session,
    case_id: str,
    query: str,
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """PostgreSQL fallback: search names, phones, FIR/surveillance text."""
    q = query.strip()
    if not q:
        return []

    pattern = f"%{q}%"
    hits: list[dict[str, Any]] = []

    people = db.execute(
        text(
            """
            SELECT DISTINCT p.person_id AS id, p.name AS label, 'person' AS entity_type,
                   'people' AS source_type, p.person_id AS source_id
            FROM people p
            LEFT JOIN recorded_names rn ON rn.person_id = p.person_id
            WHERE p.name ILIKE :pattern OR rn.recorded_name ILIKE :pattern
            LIMIT :lim
            """
        ),
        {"pattern": pattern, "lim": limit},
    ).mappings().all()
    hits.extend(dict(r) for r in people)

    phones = db.execute(
        text(
            """
            SELECT DISTINCT ('PH-' || regexp_replace(phone_number, '[^0-9]', '', 'g')) AS id,
                   phone_number AS label, 'phone' AS entity_type,
                   'phones' AS source_type, phone_id AS source_id
            FROM phones
            WHERE phone_number LIKE :pattern
            LIMIT :lim
            """
        ),
        {"pattern": pattern, "lim": limit},
    ).mappings().all()
    hits.extend(dict(r) for r in phones)

    fir_rows = db.execute(
        text(
            """
            SELECT fir_id AS source_id, complaint_text
            FROM fir WHERE case_id = :cid AND complaint_text ILIKE :pattern
            LIMIT 5
            """
        ),
        {"cid": case_id, "pattern": pattern},
    ).mappings().all()
    for row in fir_rows:
        hits.append(
            {
                "id": row["source_id"],
                "label": q,
                "entity_type": "document",
                "source_type": "fir",
                "source_id": row["source_id"],
                "excerpt": row["complaint_text"][:200],
            }
        )

    chat_rows = db.execute(
        text(
            """
            SELECT message_id AS source_id, message_text, sender_phone
            FROM chat_messages
            WHERE case_id = :cid AND message_text ILIKE :pattern
            LIMIT 5
            """
        ),
        {"cid": case_id, "pattern": pattern},
    ).mappings().all()
    for row in chat_rows:
        hits.append(
            {
                "id": row["source_id"],
                "label": row["sender_phone"],
                "entity_type": "phone",
                "source_type": "chat_messages",
                "source_id": row["source_id"],
                "excerpt": row["message_text"][:200],
            }
        )

    return hits[:limit]


def neo4j_fulltext_search(
    case_id: str,
    query: str,
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    if not is_neo4j_available():
        return []

    lucene_query = query.strip()
    if not lucene_query:
        return []

    cypher = """
    CALL db.index.fulltext.queryNodes('entitySearch', $q)
    YIELD node, score
    WHERE node.case_id IS NULL OR node.case_id = $case_id
    OPTIONAL MATCH (node)-[m:MENTIONED_IN]->(s:SourceDocument)
    RETURN node.id AS id,
           coalesce(node.label, node.phone_number, node.account_number, node.id) AS label,
           labels(node)[0] AS neo4j_label,
           score,
           s.source_type AS source_type,
           s.source_id AS source_id,
           m.excerpt AS excerpt
    ORDER BY score DESC
    LIMIT $limit
    """

    label_map = {
        "Person": "person",
        "Phone": "phone",
        "Account": "account",
        "Organization": "organization",
        "Location": "location",
        "SourceDocument": "document",
    }

    hits: list[dict[str, Any]] = []
    try:
        with get_session() as session:
            rows = session.run(
                cypher,
                {"q": lucene_query, "case_id": case_id, "limit": limit},
            )
            for row in rows:
                hits.append(
                    {
                        "id": row["id"],
                        "label": row["label"],
                        "entity_type": label_map.get(row["neo4j_label"], "person"),
                        "source_type": row["source_type"],
                        "source_id": row["source_id"],
                        "excerpt": row["excerpt"],
                        "score": row["score"],
                    }
                )
    except Exception as exc:
        logger.warning("Neo4j full-text search failed: %s", exc)

    return hits


def cross_source_search(
    db: Session,
    case_id: str,
    query: str,
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Merge Neo4j full-text hits with PostgreSQL fallback (deduped by id)."""
    neo_hits = neo4j_fulltext_search(case_id, query, limit=limit)
    if neo_hits:
        return neo_hits

    return _pg_fulltext_hits(db, case_id, query, limit=limit)
