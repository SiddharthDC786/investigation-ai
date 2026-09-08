from __future__ import annotations

import logging

from app.services.neo4j_client import get_session, is_neo4j_available

logger = logging.getLogger(__name__)


def ensure_schema() -> None:
    if not is_neo4j_available():
        return

    statements = [
        """
        CREATE CONSTRAINT person_id IF NOT EXISTS
        FOR (p:Person) REQUIRE p.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT phone_id IF NOT EXISTS
        FOR (p:Phone) REQUIRE p.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT account_id IF NOT EXISTS
        FOR (a:Account) REQUIRE a.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT org_id IF NOT EXISTS
        FOR (o:Organization) REQUIRE o.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT location_id IF NOT EXISTS
        FOR (l:Location) REQUIRE l.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT source_doc_id IF NOT EXISTS
        FOR (s:SourceDocument) REQUIRE s.source_id IS UNIQUE
        """,
        """
        CREATE FULLTEXT INDEX entitySearch IF NOT EXISTS
        FOR (n:Person|Phone|Account|Organization|Location|SourceDocument)
        ON EACH [n.label, n.normalized_label, n.phone_number, n.account_number, n.text]
        """,
    ]

    with get_session() as session:
        for stmt in statements:
            try:
                session.run(stmt).consume()
            except Exception as exc:
                logger.debug("Schema statement skipped or failed: %s", exc)
