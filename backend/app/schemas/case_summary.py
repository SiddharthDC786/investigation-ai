from pydantic import BaseModel, Field


class CaseSummaryResponse(BaseModel):
    case_id: str
    title: str
    narrative: str
    key_findings: list[str] = Field(default_factory=list)
    top_subjects: list[str] = Field(default_factory=list)
    timeline_highlights: list[str] = Field(default_factory=list)
    generated_in_ms: int
