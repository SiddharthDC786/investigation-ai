from fastapi import APIRouter, HTTPException
from app.schemas.case import CaseCreate


router = APIRouter()

cases = []


@router.post("/cases")
def create_case(case: CaseCreate):
    cases.append(case)
    return case


@router.get("/cases")
def get_cases():
    return cases


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    for case in cases:
        if case.case_id == case_id:
            return case

    raise HTTPException(
        status_code=404,
        detail="Case not found"
    )