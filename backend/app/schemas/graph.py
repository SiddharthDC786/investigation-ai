from pydantic import BaseModel, Field

from app.schemas.investigation import InvestigationEntity


class GraphLink(BaseModel):
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[InvestigationEntity]
    links: list[GraphLink] = Field(default_factory=list)
