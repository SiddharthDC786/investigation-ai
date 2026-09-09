from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import assert_case_access, get_current_user
from app.schemas.timeline import TimelineResponse
from app.services.timeline_service import build_case_timeline

router = APIRouter(tags=["timeline"])


@router.get("/cases/{case_id}/timeline", response_model=TimelineResponse)
def get_case_timeline(
    case_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    assert_case_access(user, case_id)
    case_exists = db.execute(
        text("SELECT 1 FROM cases WHERE case_id = :cid"),
        {"cid": case_id},
    ).first()
    if not case_exists:
        raise HTTPException(status_code=404, detail="Case not found")

    events = build_case_timeline(db, case_id)
    return TimelineResponse(case_id=case_id, events=events)
