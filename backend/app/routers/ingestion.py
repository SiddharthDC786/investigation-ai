from fastapi import APIRouter, Form, UploadFile

from app.database import get_db
from app.schemas.ingest import IngestResponse
from app.services.ingest_service import (
    ingest_cdr_csv,
    ingest_fir_file,
    ingest_surveillance_file,
    ingest_transactions_csv,
)
from sqlalchemy.orm import Session
from fastapi import Depends

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/cdr", response_model=IngestResponse)
async def ingest_cdr(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    return ingest_cdr_csv(db, file_bytes=contents, case_id=case_id)


@router.post("/fir", response_model=IngestResponse)
async def ingest_fir(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    return ingest_fir_file(db, file_bytes=contents, case_id=case_id)


@router.post("/transactions", response_model=IngestResponse)
async def ingest_transactions(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    return ingest_transactions_csv(db, file_bytes=contents, case_id=case_id)


@router.post("/surveillance", response_model=IngestResponse)
async def ingest_surveillance(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    return ingest_surveillance_file(db, file_bytes=contents, case_id=case_id)
