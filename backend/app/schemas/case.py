from pydantic import BaseModel


class CaseCreate(BaseModel):
    case_id: str
    title: str
    description: str | None = None