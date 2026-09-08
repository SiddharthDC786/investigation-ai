from pydantic import BaseModel
from datetime import datetime

class SourceRecordOut(BaseModel):
    source_id: str
    case_id: str
    source_type: str
    raw_filename: str | None
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True