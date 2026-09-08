from pydantic import BaseModel


class Entity(BaseModel):
    id: str
    type: str
    label: str