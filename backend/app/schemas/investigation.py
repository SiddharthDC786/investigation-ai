from typing import Literal

from pydantic import BaseModel, Field

EntityType = Literal["person", "phone", "account", "address"]
SeverityBand = Literal["high", "medium", "low"]
NameMatchType = Literal["exact", "alias", "typo", "partial"]
PersonRole = Literal[
    "suspect", "associate", "facilitator", "witness", "complainant", "handler"
]


class Connection(BaseModel):
    targetId: str
    reason: str


class InvestigationEntity(BaseModel):
    id: str
    label: str
    type: EntityType
    role: PersonRole | None = None
    subtitle: str | None = None
    aliases: list[str] = Field(default_factory=list)
    score: int = 50
    severity: SeverityBand = "medium"
    sources: list[str] = Field(default_factory=list)
    explainability: list[str] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class NameMatchHit(BaseModel):
    entity: InvestigationEntity
    matchType: NameMatchType
    matchedOn: str
    confidence: int


class RelatedPersonHit(BaseModel):
    entity: InvestigationEntity
    hops: int
    connectionReason: str


class InvestigationSearchResult(BaseModel):
    nameCandidates: list[NameMatchHit]
    needsDisambiguation: bool
    primaryMatches: list[InvestigationEntity]
    relatedPeople: list[RelatedPersonHit]
    linkedRecords: list[InvestigationEntity]
