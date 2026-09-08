from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.osint import (
    OsintAuditLogResponse,
    OsintEnrichRequest,
    OsintEnrichResponse,
    AuditChainEntry,
)
from app.services.audit_chain import fetch_audit_log, verify_audit_chain
from app.services.osint_enrichment import run_osint_enrichment

router = APIRouter(tags=["osint"])


@router.post("/osint/enrich", response_model=OsintEnrichResponse)
def osint_enrich(body: OsintEnrichRequest, db: Session = Depends(get_db)):
    try:
        result = run_osint_enrichment(
            db,
            case_id=body.case_id,
            entity_id=body.entity_id,
            lookup_id=body.lookup_id,
            operator=body.operator,
            operator_name=body.operator_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return OsintEnrichResponse(**result)


@router.get("/osint/audit-log", response_model=OsintAuditLogResponse)
def osint_audit_log(
    case_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    entries = fetch_audit_log(db, case_id=case_id, limit=limit)
    verification = verify_audit_chain(db, case_id=case_id)
    return OsintAuditLogResponse(
        case_id=case_id,
        entries=[AuditChainEntry(**e) for e in entries],
        chain_status=verification["status"],
    )
