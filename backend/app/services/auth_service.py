from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.config import settings

ROLE_INVESTIGATOR = "investigator"
ROLE_SUPERVISOR = "supervisor"

_failed_attempts: dict[str, list[float]] = defaultdict(list)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    computed = _hash_password(password, salt)
    return hmac.compare_digest(computed, expected_hash)


def _demo_users() -> dict[str, dict[str, Any]]:
    """Demo accounts — disabled in production unless explicitly allowed."""
    if settings.environment.lower() == "production" and not settings.allow_demo_passwords:
        return {}
    salt = settings.auth_password_salt
    return {
        settings.demo_investigator_badge: {
            "badge_id": settings.demo_investigator_badge,
            "name": "Investigator Demo",
            "role": ROLE_INVESTIGATOR,
            "case_ids": settings.demo_investigator_cases,
            "password_hash": settings.demo_investigator_password_hash
            or _hash_password("vigil2026", salt),
        },
        settings.demo_supervisor_badge: {
            "badge_id": settings.demo_supervisor_badge,
            "name": "Supervisor Demo",
            "role": ROLE_SUPERVISOR,
            "case_ids": [],  # empty = all cases
            "password_hash": settings.demo_supervisor_password_hash
            or _hash_password("admin2026", salt),
        },
    }


def _check_login_rate_limit(badge_id: str) -> None:
    key = badge_id.strip().upper()
    now = time.time()
    window = settings.login_rate_window_seconds
    attempts = [t for t in _failed_attempts[key] if now - t < window]
    _failed_attempts[key] = attempts
    if len(attempts) >= settings.login_rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts — try again later",
        )


def _record_failed_login(badge_id: str) -> None:
    _failed_attempts[badge_id.strip().upper()].append(time.time())


def authenticate_user(badge_id: str, password: str) -> dict[str, Any]:
    _check_login_rate_limit(badge_id)
    users = _demo_users()
    user = users.get(badge_id.strip().upper())
    if not user:
        _record_failed_login(badge_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid badge or password")
    if not _verify_password(password, settings.auth_password_salt, user["password_hash"]):
        _record_failed_login(badge_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid badge or password")
    _failed_attempts.pop(badge_id.strip().upper(), None)
    return {
        "badge_id": user["badge_id"],
        "name": user["name"],
        "role": user["role"],
        "case_ids": user["case_ids"],
    }


def create_access_token(user: dict[str, Any]) -> tuple[str, int]:
    expires_minutes = settings.jwt_expire_minutes
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": user["badge_id"],
        "name": user["name"],
        "role": user["role"],
        "case_ids": user["case_ids"],
        "exp": exp,
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, expires_minutes * 60


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from exc


def user_can_access_case(user: dict[str, Any], case_id: str) -> bool:
    if user.get("role") == ROLE_SUPERVISOR:
        return True
    allowed = user.get("case_ids") or []
    if not allowed:
        return True
    return case_id in allowed
