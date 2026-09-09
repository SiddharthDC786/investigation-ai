from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import assert_case_access, get_current_user
from app.schemas.osint import AuditVerifyResponse
from app.services.audit_chain import verify_audit_chain

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/verify", response_model=AuditVerifyResponse)
def verify_audit(
    case_id: str | None = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if case_id:
        assert_case_access(user, case_id)
    result = verify_audit_chain(db, case_id=case_id)
    return AuditVerifyResponse(**result)
