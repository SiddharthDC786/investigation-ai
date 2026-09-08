from fastapi import APIRouter
from app.services.lead_service import get_case_leads

router = APIRouter(tags=["leads"])

@router.get("/cases/{case_id}/leads")
def get_leads(case_id: str):
    return get_case_leads(case_id)

     