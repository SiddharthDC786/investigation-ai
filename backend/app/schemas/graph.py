from pydantic import BaseModel, Field

from app.schemas.investigation import InvestigationEntity


class GraphLink(BaseModel):
    source: str
    target: str
    label: str
    weight: float = 1.0
    link_type: str = "phone_call"  # phone_call | relationship | shared_contact
    evidence: str | None = None


class GraphStats(BaseModel):
    person_count: int = 0
    link_count: int = 0
    shared_contact_count: int = 0


class GraphResponse(BaseModel):
    nodes: list[InvestigationEntity]
    links: list[GraphLink] = Field(default_factory=list)
    focus_person_id: str | None = None
    summary: str | None = None
    connection_story: list[str] = Field(default_factory=list)
    stats: GraphStats | None = None
