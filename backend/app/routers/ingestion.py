import uuid
from fastapi import APIRouter, UploadFile, Depends, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.source_record import SourceRecord

router = APIRouter(prefix="/ingest", tags=["ingestion"])

def save_source_record(db: Session, case_id: str, source_type: str, filename: str):
    source_id = f"SRC{uuid.uuid4().hex[:8].upper()}"
    record = SourceRecord(
        source_id=source_id,
        case_id=case_id,
        source_type=source_type,
        raw_filename=filename,
        status="RECEIVED",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.post("/cdr")
async def ingest_cdr(case_id: str = Form(...), file: UploadFile = None, db: Session = Depends(get_db)):
    contents = await file.read()
    lines = contents.decode().splitlines()
    record = save_source_record(db, case_id, "CDR", file.filename)
    return {
        "status": "success",
        "source_id": record.source_id,
        "records_received": max(len(lines) - 1, 0),
    }