from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Case(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime(timezone=True), server_default=func.now())