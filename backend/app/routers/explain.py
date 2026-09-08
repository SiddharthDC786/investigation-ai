from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.explain import ExplainResponse, SourceCitation, RelationshipFact
from app.services.explain_service import build_entity_explanation

router = APIRouter(tags=["explain"])


@router.get("/explain/{entity_id}", response_model=ExplainResponse)
def explain_entity(
    entity_id: str,
    case_id: str = Query(..., alias="case_id"),
    db: Session = Depends(get_db),
):
    case_exists = db.execute(
        text("SELECT 1 FROM cases WHERE case_id = :cid"),
        {"cid": case_id},
    ).first()
    if not case_exists:
        raise HTTPException(status_code=404, detail="Case not found")

    result = build_entity_explanation(db, case_id, entity_id)
    return ExplainResponse(
        entity_id=result["entity_id"],
        case_id=result["case_id"],
        label=result["label"],
        narrative=result["narrative"],
        reasoning_steps=result["reasoning_steps"],
        source_citations=[SourceCitation(**c) for c in result["source_citations"]],
        relationships=[RelationshipFact(**r) for r in result["relationships"]],
        risk_factors=result["risk_factors"],
    )
