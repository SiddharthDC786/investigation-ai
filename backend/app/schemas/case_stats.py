from pydantic import BaseModel


class CaseStatsResponse(BaseModel):
    case_id: str
    persons: int
    cdr_records: int
    transactions: int
    timeline_events: int
