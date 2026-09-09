from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import assert_case_access, get_current_user
from app.schemas.analysis import (
    CentralityResponse,
    CommunitiesResponse,
    CentralityEntry,
    CommunityCluster,
    RiskScoreResponse,
    RiskScoreEntry,
    RiskScoreComponents,
)
from app.services.network_analysis import get_centrality_rankings, get_community_clusters
from app.services.risk_score_service import compute_risk_scores

router = APIRouter(prefix="/cases/{case_id}/analyze", tags=["analysis"])


@router.get("/centrality", response_model=CentralityResponse)
def get_centrality(
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

    rankings = get_centrality_rankings(db, case_id)
    return CentralityResponse(
        case_id=case_id,
        rankings=[CentralityEntry(**row) for row in rankings],
    )


@router.get("/communities", response_model=CommunitiesResponse)
def get_communities(
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

    clusters = get_community_clusters(db, case_id)
    return CommunitiesResponse(
        case_id=case_id,
        communities=[CommunityCluster(**row) for row in clusters],
    )


@router.get("/risk-score", response_model=RiskScoreResponse)
def get_risk_scores(
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

    scores = compute_risk_scores(db, case_id)
    return RiskScoreResponse(
        case_id=case_id,
        scores=[
            RiskScoreEntry(
                **{
                    **row,
                    "components": RiskScoreComponents(**row["components"]),
                }
            )
            for row in scores
        ],
    )
