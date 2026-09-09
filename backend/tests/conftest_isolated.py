"""Isolated CASEISOL fixtures — do not mutate CASE0001 demo data."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.database import SessionLocal
from app.services.provenance_service import ensure_provenance_tables
from app.services.review_service import ensure_reviews_table

ISOLATED_CASE = "CASEISOL"


@pytest.fixture
def isolated_db():
    db = SessionLocal()
    ensure_provenance_tables(db)
    ensure_reviews_table(db)
    db.execute(
        text(
            """
            INSERT INTO cases (case_id, title, description, status)
            VALUES (:cid, 'Isolated test case', 'pytest only', 'OPEN')
            ON CONFLICT (case_id) DO NOTHING
            """
        ),
        {"cid": ISOLATED_CASE},
    )
    for pid, city in (("PISOL1", "Mumbai"), ("PISOL2", "Chennai")):
        db.execute(
            text(
                """
                INSERT INTO people (person_id, name, dob, gender, city)
                VALUES (:pid, 'Rahul Sharma', '1990-01-01', 'Male', :city)
                ON CONFLICT (person_id) DO NOTHING
                """
            ),
            {"pid": pid, "city": city},
        )
    db.commit()
    yield db
    cleanup_tables = (
        "officer_review_history",
        "officer_reviews",
        "identity_decisions",
        "identity_blocks",
        "entity_provenance",
        "recorded_names",
        "ingest_sources",
        "fir",
    )
    for table in cleanup_tables:
        db.execute(text(f"DELETE FROM {table} WHERE case_id = :cid"), {"cid": ISOLATED_CASE})
    db.commit()
    db.close()


def seed_provisional_mention(
    db,
    *,
    case_id: str,
    mention_entity_id: str,
    recorded_name: str,
    record_id: str,
    source_id: str = "SRCISOL1",
) -> None:
    db.execute(
        text(
            """
            INSERT INTO recorded_names
                (record_id, case_id, source_type, source_id, recorded_name, variant_type, person_id, is_erroneous)
            VALUES
                (:rid, :cid, 'fir', :sid, :name, 'ner_extract', NULL, false)
            ON CONFLICT (record_id) DO NOTHING
            """
        ),
        {
            "rid": record_id,
            "cid": case_id,
            "sid": source_id,
            "name": recorded_name,
        },
    )
    db.execute(
        text(
            """
            INSERT INTO entity_provenance
                (provenance_id, case_id, entity_id, source_type, source_id, record_id,
                 excerpt, extraction_method, relationship_kind, resolution_action)
            VALUES
                (:pid, :cid, :eid, 'fir', :sid, :rid, :excerpt, 'ner_extract', 'suggested', 'suggested_match')
            """
        ),
        {
            "pid": f"PV-{uuid.uuid4().hex[:8].upper()}",
            "cid": case_id,
            "eid": mention_entity_id,
            "sid": source_id,
            "rid": record_id,
            "excerpt": f"Mention {recorded_name}",
        },
    )


@pytest.fixture
def two_same_name_mentions(isolated_db):
    db = isolated_db
    mention_a = "PU-ISOLAAAA"
    mention_b = "PU-ISOLBBBB"
    record_a = "RN-ISOLAAAA"
    record_b = "RN-ISOLBBBB"
    seed_provisional_mention(
        db,
        case_id=ISOLATED_CASE,
        mention_entity_id=mention_a,
        recorded_name="Rahul Sharma",
        record_id=record_a,
    )
    seed_provisional_mention(
        db,
        case_id=ISOLATED_CASE,
        mention_entity_id=mention_b,
        recorded_name="Rahul Sharma",
        record_id=record_b,
    )
    db.commit()
    return {
        "case_id": ISOLATED_CASE,
        "mention_a": mention_a,
        "mention_b": mention_b,
        "record_a": record_a,
        "record_b": record_b,
    }
