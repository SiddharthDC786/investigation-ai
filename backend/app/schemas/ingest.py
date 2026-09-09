from pydantic import BaseModel, Field


class ExtractedMention(BaseModel):
    text: str
    entity_type: str
    resolved_entity_id: str | None = None
    action: str
    source_excerpt: str | None = None
    match_reason: str | None = None
    requires_review: bool = False
    suggested_person_id: str | None = None


class IngestResponse(BaseModel):
    status: str
    source_id: str
    source_type: str
    case_id: str | None = None
    records_received: int = 0
    entities_extracted: int = 0
    entities_merged: int = 0
    mentions: list[ExtractedMention] = Field(default_factory=list)
    extracted_text: str | None = None


class PreviewEntity(BaseModel):
    text: str
    entity_type: str
    confidence: float
    source_excerpt: str | None = None


class IngestPreviewRequest(BaseModel):
    text: str


class IngestPreviewResponse(BaseModel):
    engine: str
    spacy_available: bool
    entities_extracted: int
    entities: list[PreviewEntity] = Field(default_factory=list)
    extracted_text: str | None = None
