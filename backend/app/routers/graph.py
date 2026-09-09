from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import assert_case_access, get_current_user
from app.schemas.graph import GraphResponse
from app.services.case_graph import build_case_graph, build_simplified_case_graph

router = APIRouter(tags=["graph"])


@router.get("/cases/{case_id}/graph", response_model=GraphResponse)
def get_graph(
    case_id: str,
    center_person_id: str | None = Query(None, alias="center_person_id"),
    simplified: bool = Query(True, description="People-only view with fewer nodes"),
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
    if simplified:
        return build_simplified_case_graph(db, case_id, center_person_id=center_person_id)
    return build_case_graph(db, case_id, center_person_id=center_person_id)
