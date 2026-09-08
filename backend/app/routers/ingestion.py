from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ingest import (
    IngestPreviewRequest,
    IngestPreviewResponse,
    IngestResponse,
    PreviewEntity,
)
from app.services.ingest_service import (
    ingest_cdr_csv,
    ingest_fir_file,
    ingest_surveillance_file,
    ingest_transactions_csv,
    preview_ingest_text,
)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/preview", response_model=IngestPreviewResponse)
def ingest_preview(body: IngestPreviewRequest):
    result = preview_ingest_text(body.text)
    return IngestPreviewResponse(
        engine=result["engine"],
        spacy_available=result["spacy_available"],
        entities_extracted=result["entities_extracted"],
        entities=[PreviewEntity(**e) for e in result["entities"]],
    )


@router.post("/fir/text", response_model=IngestResponse)
async def ingest_fir_text(
    text: str = Form(...),
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    return ingest_fir_file(db, file_bytes=text.encode("utf-8"), case_id=case_id)


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
