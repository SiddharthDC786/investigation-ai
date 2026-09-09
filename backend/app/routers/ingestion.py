from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import assert_case_access, get_current_user
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
from app.services.ocr_service import extract_text_from_image

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def _require_case(user: dict, case_id: str | None) -> str:
    if not case_id or not case_id.strip():
        raise HTTPException(status_code=400, detail="case_id is required for ingest")
    assert_case_access(user, case_id.strip())
    return case_id.strip()


@router.post("/preview", response_model=IngestPreviewResponse)
def ingest_preview(body: IngestPreviewRequest):
    result = preview_ingest_text(body.text)
    return IngestPreviewResponse(
        engine=result["engine"],
        spacy_available=result["spacy_available"],
        entities_extracted=result["entities_extracted"],
        entities=[PreviewEntity(**e) for e in result["entities"]],
    )


@router.post("/preview/image", response_model=IngestPreviewResponse)
async def ingest_preview_image(file: UploadFile):
    contents = await file.read()
    try:
        text = extract_text_from_image(contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = preview_ingest_text(text)
    return IngestPreviewResponse(
        engine=result["engine"],
        spacy_available=result["spacy_available"],
        entities_extracted=result["entities_extracted"],
        entities=[PreviewEntity(**e) for e in result["entities"]],
        extracted_text=text,
    )


@router.post("/fir/text", response_model=IngestResponse)
async def ingest_fir_text(
    text: str = Form(...),
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    cid = _require_case(user, case_id)
    return ingest_fir_file(db, file_bytes=text.encode("utf-8"), case_id=cid)


@router.post("/fir/image", response_model=IngestResponse)
async def ingest_fir_image(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    cid = _require_case(user, case_id)
    contents = await file.read()
    try:
        ocr_text = extract_text_from_image(contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = ingest_fir_file(db, file_bytes=ocr_text.encode("utf-8"), case_id=cid)
    result.extracted_text = ocr_text
    return result


@router.post("/cdr", response_model=IngestResponse)
async def ingest_cdr(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    cid = _require_case(user, case_id)
    contents = await file.read()
    return ingest_cdr_csv(db, file_bytes=contents, case_id=cid)


@router.post("/fir", response_model=IngestResponse)
async def ingest_fir(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    cid = _require_case(user, case_id)
    contents = await file.read()
    return ingest_fir_file(db, file_bytes=contents, case_id=cid)


@router.post("/transactions", response_model=IngestResponse)
async def ingest_transactions(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    cid = _require_case(user, case_id)
    contents = await file.read()
    return ingest_transactions_csv(db, file_bytes=contents, case_id=cid)


@router.post("/surveillance", response_model=IngestResponse)
async def ingest_surveillance(
    file: UploadFile,
    case_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    cid = _require_case(user, case_id)
    contents = await file.read()
    return ingest_surveillance_file(db, file_bytes=contents, case_id=cid)
