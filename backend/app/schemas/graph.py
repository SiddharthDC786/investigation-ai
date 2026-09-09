from pydantic import BaseModel, Field

from app.schemas.investigation import InvestigationEntity


class GraphLink(BaseModel):
    source: str
    target: str
    label: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    nodes: list[InvestigationEntity]
    links: list[GraphLink] = Field(default_factory=list)
    focus_person_id: str | None = None
    summary: str | None = None
