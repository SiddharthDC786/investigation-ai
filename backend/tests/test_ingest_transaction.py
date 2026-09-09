"""Focused tests for ingest transaction rollback and retry."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.services.ingest_service import ingest_text_document
from app.services.provenance_service import content_hash

ISOLATED_CASE = "CASEISOL"


@pytest.fixture
def ingest_case(isolated_db):
    return ISOLATED_CASE


def test_failed_import_rolls_back_and_retry_succeeds(ingest_case, isolated_db):
    db = isolated_db
    unique = (
        f"Retry probe {uuid.uuid4().hex}: suspect Rahul Sharma called 9876543210 from Mumbai."
    )
    digest = content_hash(unique)

    with patch(
        "app.services.ingest_service.record_provenance",
        side_effect=RuntimeError("simulated mid-import failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated mid-import failure"):
            ingest_text_document(
                db,
                text_content=unique,
                source_type="fir",
                case_id=ingest_case,
            )

    source_count = db.execute(
        text(
            """
            SELECT COUNT(*) FROM ingest_sources
            WHERE case_id = :cid AND content_hash = :hash
            """
        ),
        {"cid": ingest_case, "hash": digest},
    ).scalar()
    provenance_count = db.execute(
        text("SELECT COUNT(*) FROM entity_provenance WHERE case_id = :cid"),
        {"cid": ingest_case},
    ).scalar()
    names_count = db.execute(
        text("SELECT COUNT(*) FROM recorded_names WHERE case_id = :cid AND source_type = 'fir'"),
        {"cid": ingest_case},
    ).scalar()
    assert source_count == 0
    assert provenance_count == 0
    assert names_count == 0

    result = ingest_text_document(
        db,
        text_content=unique,
        source_type="fir",
        case_id=ingest_case,
    )
    assert result.status == "success"
    assert result.entities_extracted >= 1
    assert (
        db.execute(
            text(
                """
                SELECT COUNT(*) FROM ingest_sources
                WHERE case_id = :cid AND content_hash = :hash
                """
            ),
            {"cid": ingest_case, "hash": digest},
        ).scalar()
        == 1
    )


def test_successful_import_is_duplicate_on_reupload(ingest_case, isolated_db):
    db = isolated_db
    unique = f"Duplicate probe {uuid.uuid4().hex} for isolated ingest dedup test."
    digest = content_hash(unique)

    first = ingest_text_document(
        db,
        text_content=unique,
        source_type="fir",
        case_id=ingest_case,
    )
    assert first.status == "success"
    names_after_first = db.execute(
        text("SELECT COUNT(*) FROM recorded_names WHERE case_id = :cid"),
        {"cid": ingest_case},
    ).scalar()

    second = ingest_text_document(
        db,
        text_content=unique,
        source_type="fir",
        case_id=ingest_case,
    )
    assert second.status == "duplicate"
    assert second.entities_extracted == 0
    names_after_second = db.execute(
        text("SELECT COUNT(*) FROM recorded_names WHERE case_id = :cid"),
        {"cid": ingest_case},
    ).scalar()
    source_count = db.execute(
        text(
            """
            SELECT COUNT(*) FROM ingest_sources
            WHERE case_id = :cid AND content_hash = :hash
            """
        ),
        {"cid": ingest_case, "hash": digest},
    ).scalar()

    assert names_after_second == names_after_first
    assert source_count == 1
