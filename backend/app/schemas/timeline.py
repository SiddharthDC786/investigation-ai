from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    id: str
    timestamp: str
    title: str
    description: str
    entityIds: list[str] = Field(default_factory=list)
    source: str


class TimelineResponse(BaseModel):
    case_id: str
    events: list[TimelineEvent] = Field(default_factory=list)
