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


class RiskScoreComponents(BaseModel):
    centrality: float
    role: float
    case_history: float


class RiskScoreEntry(BaseModel):
    entity_id: str
    label: str
    city: str | None = None
    role: str | None = None
    composite_score: int
    severity: str
    components: RiskScoreComponents
    triage_rank: int
    explainability: list[str] = Field(default_factory=list)


class RiskScoreResponse(BaseModel):
    case_id: str
    score_type: str = "investigation_priority"
    score_disclaimer: str = (
        "Scores rank investigation priority from network position and case evidence. "
        "They are not probabilities of guilt or conviction."
    )
    scores: list[RiskScoreEntry] = Field(default_factory=list)
