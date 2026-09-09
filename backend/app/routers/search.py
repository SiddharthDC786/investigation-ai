from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.investigation import InvestigationSearchResult
from app.services.investigation_search import run_investigation_search

router = APIRouter(tags=["search"])


@router.get(
    "/cases/{case_id}/search",
    response_model=InvestigationSearchResult,
)
def search_case(
    case_id: str,
    name: str = Query("", alias="name"),
    phone: str = Query("", alias="phone"),
    area: str = Query("", alias="area"),
    role: str = Query("all", alias="role"),
    gender: str = Query("", alias="gender"),
    age: str = Query("", alias="age"),
    father_name: str = Query("", alias="father_name"),
    selected_person_id: str | None = Query(None, alias="selected_person_id"),
    face_person_id: str | None = Query(None, alias="face_person_id"),
    db: Session = Depends(get_db),
):
    case_exists = db.execute(
        text("SELECT 1 FROM cases WHERE case_id = :cid"),
        {"cid": case_id},
    ).first()
    if not case_exists:
        raise HTTPException(status_code=404, detail="Case not found")

    return run_investigation_search(
        db,
        case_id,
        name=name,
        phone=phone,
        area=area,
        role=role,
        gender=gender,
        age=age,
        father_name=father_name,
        selected_person_id=selected_person_id,
        face_person_id=face_person_id,
    )


@router.post("/cases/{case_id}/search/face")
def search_by_face(case_id: str):
    """Demo face match — replace with ML pipeline later."""
    return {"personId": "P00014", "confidence": 87}
