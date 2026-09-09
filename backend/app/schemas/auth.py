from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    badge_id: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    badge_id: str
    name: str
    role: str
    case_ids: list[str] = Field(default_factory=list)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile
