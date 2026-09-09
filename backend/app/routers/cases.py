from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import assert_case_access, get_current_user
from app.models.case import Case
from app.schemas.case import CaseCreate
from app.schemas.case_stats import CaseStatsResponse
from app.services.case_stats import get_case_stats
from app.services.auth_service import ROLE_SUPERVISOR

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("")
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if user.get("role") != ROLE_SUPERVISOR:
        raise HTTPException(status_code=403, detail="Supervisor access required to create cases")
    db_case = Case(**case.model_dump())
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.get("")
def get_cases(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    all_cases = db.query(Case).all()
    if user.get("role") == ROLE_SUPERVISOR or not user.get("case_ids"):
        return all_cases
    allowed = set(user["case_ids"])
    return [c for c in all_cases if c.case_id in allowed]


@router.get("/{case_id}")
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    assert_case_access(user, case_id)
    db_case = db.query(Case).filter(Case.case_id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.get("/{case_id}/stats", response_model=CaseStatsResponse)
def case_stats(
    case_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    assert_case_access(user, case_id)
    try:
        return get_case_stats(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc