from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies.auth import assert_case_access, get_current_user
from app.database import get_db
from app.services.review_service import list_reviews, upsert_review

router = APIRouter(tags=["reviews"])


class ReviewUpsertRequest(BaseModel):
    entity_id: str = Field(min_length=1, max_length=32)
    decision: str = Field(pattern="^(confirmed|need_more_proof|not_relevant)$")
    notes: str | None = Field(default=None, max_length=2000)
    canonical_person_id: str | None = Field(default=None, max_length=16)


class ReviewEntry(BaseModel):
    entity_id: str
    decision: str
    notes: str | None = None
    reviewer_badge: str
    reviewer_name: str
    created_at: str | None = None
    updated_at: str | None = None


@router.get("/cases/{case_id}/reviews", response_model=list[ReviewEntry])
def get_case_reviews(
    case_id: str,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    assert_case_access(user, case_id)
    return list_reviews(db, case_id=case_id)


@router.post("/cases/{case_id}/reviews", response_model=ReviewEntry)
def save_case_review(
    case_id: str,
    body: ReviewUpsertRequest,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    assert_case_access(user, case_id)
    try:
        upsert_review(
            db,
            case_id=case_id,
            entity_id=body.entity_id,
            decision=body.decision,
            notes=body.notes,
            reviewer_badge=user["badge_id"],
            reviewer_name=user["name"],
            canonical_person_id=body.canonical_person_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rows = list_reviews(db, case_id=case_id)
    match = next((r for r in rows if r["entity_id"] == body.entity_id), None)
    return match or {
        "entity_id": body.entity_id,
        "decision": body.decision,
        "notes": body.notes,
        "reviewer_badge": user["badge_id"],
        "reviewer_name": user["name"],
    }
