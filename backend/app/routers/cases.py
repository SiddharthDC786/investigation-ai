from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate

router = APIRouter(prefix="/cases", tags=["cases"])

@router.post("")
def create_case(case: CaseCreate, db: Session = Depends(get_db)):
    db_case = Case(**case.model_dump())
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.get("")
def get_cases(db: Session = Depends(get_db)):
    return db.query(Case).all()

@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    db_case = db.query(Case).filter(Case.case_id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case