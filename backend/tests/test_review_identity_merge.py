"""Focused tests for provisional identity confirmation."""

import pytest
from sqlalchemy import text

from app.services.review_service import upsert_review

from tests.conftest_isolated import ISOLATED_CASE


def test_confirm_one_mention_does_not_update_other_same_name(two_same_name_mentions, isolated_db):
    ctx = two_same_name_mentions
    db = isolated_db

    upsert_review(
        db,
        case_id=ctx["case_id"],
        entity_id=ctx["mention_a"],
        decision="confirmed",
        notes="merge mention A only",
        reviewer_badge="INV-TEST",
        reviewer_name="Test Officer",
        canonical_person_id="PISOL1",
    )

    person_a = db.execute(
        text("SELECT person_id FROM recorded_names WHERE record_id = :rid"),
        {"rid": ctx["record_a"]},
    ).scalar()
    person_b = db.execute(
        text("SELECT person_id FROM recorded_names WHERE record_id = :rid"),
        {"rid": ctx["record_b"]},
    ).scalar()
    assert person_a == "PISOL1"
    assert person_b is None


def test_invalid_provisional_canonical_rejected_without_changes(two_same_name_mentions, isolated_db):
    ctx = two_same_name_mentions
    db = isolated_db

    with pytest.raises(ValueError, match="Provisional IDs cannot be used as merge targets"):
        upsert_review(
            db,
            case_id=ctx["case_id"],
            entity_id=ctx["mention_a"],
            decision="confirmed",
            notes="bad target",
            reviewer_badge="INV-TEST",
            reviewer_name="Test Officer",
            canonical_person_id="PU-FAKEID01",
        )

    person_a = db.execute(
        text("SELECT person_id FROM recorded_names WHERE record_id = :rid"),
        {"rid": ctx["record_a"]},
    ).scalar()
    reviews = db.execute(
        text("SELECT COUNT(*) FROM officer_reviews WHERE case_id = :cid"),
        {"cid": ctx["case_id"]},
    ).scalar()
    assert person_a is None
    assert reviews == 0


def test_ordinary_review_of_registered_person_still_works(isolated_db):
    db = isolated_db
    upsert_review(
        db,
        case_id=ISOLATED_CASE,
        entity_id="PISOL1",
        decision="confirmed",
        notes="relevance only",
        reviewer_badge="INV-TEST",
        reviewer_name="Test Officer",
    )
    row = db.execute(
        text(
            """
            SELECT decision FROM officer_reviews
            WHERE case_id = :cid AND entity_id = 'PISOL1'
            """
        ),
        {"cid": ISOLATED_CASE},
    ).scalar()
    history = db.execute(
        text(
            "SELECT COUNT(*) FROM officer_review_history WHERE case_id = :cid AND entity_id = 'PISOL1'"
        ),
        {"cid": ISOLATED_CASE},
    ).scalar()
    assert row == "confirmed"
    assert history == 1

    identity_rows = db.execute(
        text("SELECT COUNT(*) FROM identity_decisions WHERE case_id = :cid"),
        {"cid": ISOLATED_CASE},
    ).scalar()
    assert identity_rows == 0
