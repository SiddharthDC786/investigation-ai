from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from neo4j import GraphDatabase, Driver

from app.config import settings

logger = logging.getLogger(__name__)

_driver: Driver | None = None
_available: bool | None = None


def is_neo4j_available() -> bool:
    global _available
    if not settings.neo4j_enabled:
        return False
    if _available is not None:
        return _available
    try:
        with get_session() as session:
            session.run("RETURN 1").consume()
        _available = True
    except Exception as exc:
        logger.warning("Neo4j unavailable, falling back to PostgreSQL: %s", exc)
        _available = False
    return _available


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


@contextmanager
def get_session() -> Iterator:
    driver = get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def close_driver() -> None:
    global _driver, _available
    if _driver is not None:
        _driver.close()
        _driver = None
    _available = None
