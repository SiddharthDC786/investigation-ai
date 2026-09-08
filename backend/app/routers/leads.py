from fastapi import APIRouter

from app.schemas.lead import Lead

router = APIRouter(tags=["leads"])

@router.get("/cases/{case_id}/leads", response_model=list[Lead])
def get_leads(case_id: str):
    return [
        {
            "lead_id": "LEAD001",
            "description": "Person 1 and Person 2 connected via shared phone contact",
            "confidence": 0.62,
            "evidence": ["cdr_0007"],
        }
    ]