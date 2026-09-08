from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    source_type: str
    source_id: str
    excerpt: str | None = None


class RelationshipFact(BaseModel):
    related_entity_id: str
    related_label: str
    relationship: str


class ExplainResponse(BaseModel):
    entity_id: str
    case_id: str
    label: str
    narrative: str
    reasoning_steps: list[str] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    relationships: list[RelationshipFact] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
