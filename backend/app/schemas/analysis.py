from pydantic import BaseModel, Field


class CentralityEntry(BaseModel):
    entity_id: str
    label: str
    entity_type: str
    betweenness: float
    pagerank: float
    rank: int


class CentralityResponse(BaseModel):
    case_id: str
    rankings: list[CentralityEntry] = Field(default_factory=list)


class CommunityCluster(BaseModel):
    community_id: str
    entity_ids: list[str] = Field(default_factory=list)
    label: str
    member_count: int
    suspicion_score: float


class CommunitiesResponse(BaseModel):
    case_id: str
    communities: list[CommunityCluster] = Field(default_factory=list)
