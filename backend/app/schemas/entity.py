from pydantic import BaseModel, Field


class EntitySourceRef(BaseModel):
    source_type: str
    source_id: str
    excerpt: str | None = None


class Entity(BaseModel):
    id: str
    type: str
    label: str
    sources: list[EntitySourceRef] = Field(default_factory=list)
    resolved_aliases: list[str] = Field(default_factory=list)
