from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.case_summary import CaseSummaryResponse
from app.services.case_summary_service import build_case_summary

router = APIRouter(tags=["case-summary"])


@router.get("/case-summary/{case_id}", response_model=CaseSummaryResponse)
def get_case_summary(case_id: str, db: Session = Depends(get_db)):
    try:
        result = build_case_summary(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CaseSummaryResponse(**result)
