from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import assert_case_access, get_current_user
from app.schemas.lead import Lead
from app.services.leads_service import compute_case_leads

router = APIRouter(tags=["leads"])


@router.get("/cases/{case_id}/leads", response_model=list[Lead])
def get_leads(
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
    return compute_case_leads(db, case_id)
