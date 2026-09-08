from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analysis import CentralityResponse, CommunitiesResponse, CentralityEntry, CommunityCluster
from app.services.network_analysis import get_centrality_rankings, get_community_clusters

router = APIRouter(prefix="/cases/{case_id}/analyze", tags=["analysis"])


@router.get("/centrality", response_model=CentralityResponse)
def get_centrality(case_id: str, db: Session = Depends(get_db)):
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
def get_communities(case_id: str, db: Session = Depends(get_db)):
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
