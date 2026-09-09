from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.schemas.auth import LoginRequest, LoginResponse, UserProfile
from app.services.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    user = authenticate_user(body.badge_id, body.password)
    token, expires_in = create_access_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserProfile(
            badge_id=user["badge_id"],
            name=user["name"],
            role=user["role"],
            case_ids=user["case_ids"],
        ),
    )


@router.get("/me", response_model=UserProfile)
def me(user: dict = Depends(get_current_user)):
    return UserProfile(
        badge_id=user["badge_id"],
        name=user["name"],
        role=user["role"],
        case_ids=user["case_ids"],
    )
