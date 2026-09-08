from fastapi import APIRouter

router = APIRouter(prefix="/resolution", tags=["resolution"])

@router.get("/candidates")
def get_merge_candidates():
    """
    Placeholder - pairs of entities the system thinks might be duplicates.
    """
    return [
        {
            "candidate_id": "CAND001",
            "entity_a": "P001",
            "entity_b": "P045",
            "similarity_score": 0.87,
            "reason": "Similar name and shared phone number",
        }
    ]

@router.post("/{candidate_id}/merge")
def merge_candidate(candidate_id: str):
    return {"status": "merged", "candidate_id": candidate_id}

@router.post("/{candidate_id}/reject")
def reject_candidate(candidate_id: str):
    return {"status": "rejected", "candidate_id": candidate_id}