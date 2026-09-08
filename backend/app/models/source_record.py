from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class SourceRecord(Base):
    __tablename__ = "source_records"

    source_id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False)
    source_type = Column(String, nullable=False)  # CDR, FIR, TRANSACTION, SURVEILLANCE
    raw_filename = Column(String, nullable=True)
    status = Column(String, default="RECEIVED")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())