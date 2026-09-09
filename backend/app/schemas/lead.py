from pydantic import BaseModel, Field


class Lead(BaseModel):
    lead_id: str
    description: str
    priority_score: int = Field(description="Investigation priority 0-99 — not probability of guilt")
    score_type: str = "investigation_priority"
    evidence: list[str] = Field(default_factory=list)
    source_type: str = "observed"
    requires_review: bool = False
