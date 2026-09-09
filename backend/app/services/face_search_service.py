from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.face_search import FaceSearchResponse

DEMO_FACE_SUSPECT = "P00014"


def demo_face_search(db: Session, *, case_id: str) -> FaceSearchResponse:
    """Training/demo stub — never present as real biometrics."""
    row = db.execute(
        text(
            """
            SELECT person_id FROM (
                SELECT person_id_a AS person_id FROM relationships WHERE case_id = :cid
                UNION SELECT person_id_b FROM relationships WHERE case_id = :cid
            ) q
            WHERE person_id = :pid
            LIMIT 1
            """
        ),
        {"cid": case_id, "pid": DEMO_FACE_SUSPECT},
    ).scalar()

    person_id = row or DEMO_FACE_SUSPECT
    return FaceSearchResponse(
        person_id=person_id,
        similarity_score=72,
        simulated=True,
        match_quality="demo_stub",
        requires_officer_review=True,
        message=(
            f"Demo stub matched training suspect {person_id} in {case_id}. "
            "Confirm with other identifiers before action."
        ),
    )
