from pydantic import BaseModel


class Lead(BaseModel):
    lead_id: str
    description: str
    confidence: float
    evidence: list[str]