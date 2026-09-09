from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.services.auth_service import ROLE_SUPERVISOR, decode_token, user_can_access_case

_bearer = HTTPBearer(auto_error=False)


def _dev_user() -> dict:
    return {
        "badge_id": "DEV-MODE",
        "name": "Development Mode",
        "role": ROLE_SUPERVISOR,
        "case_ids": [],
    }


def resolve_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not settings.auth_enabled:
        user = _dev_user()
        request.state.user = user
        return user

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_token(credentials.credentials)
    user = {
        "badge_id": payload["sub"],
        "name": payload.get("name", payload["sub"]),
        "role": payload.get("role", "investigator"),
        "case_ids": payload.get("case_ids") or [],
    }
    request.state.user = user
    return user


def get_current_user(user: dict = Depends(resolve_user)) -> dict:
    return user


def require_supervisor(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != ROLE_SUPERVISOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor access required")
    return user


def assert_case_access(user: dict, case_id: str) -> None:
    if not settings.auth_enabled:
        return
    if not user_can_access_case(user, case_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied for case {case_id}",
        )


def require_case_access(case_id: str):
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        assert_case_access(user, case_id)
        return user

    return _checker
