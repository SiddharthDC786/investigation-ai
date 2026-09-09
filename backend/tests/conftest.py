import os

os.environ.setdefault("AUTH_ENABLED", "true")

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def raw_client():
    """Unauthenticated TestClient — for health and auth rejection tests."""
    return TestClient(app)


class _AuthedClient:
    def __init__(self, headers: dict):
        self._client = TestClient(app)
        self._headers = headers

    def get(self, url: str, **kwargs):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.get(url, headers=headers, **kwargs)

    def post(self, url: str, **kwargs):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.post(url, headers=headers, **kwargs)

    def put(self, url: str, **kwargs):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.put(url, headers=headers, **kwargs)

    def delete(self, url: str, **kwargs):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.delete(url, headers=headers, **kwargs)


@pytest.fixture
def auth_headers(raw_client: TestClient):
    if not settings.auth_enabled:
        return {}
    res = raw_client.post(
        "/auth/login",
        json={"badge_id": "INV-2847", "password": "vigil2026"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(auth_headers: dict):
    """Default client — authenticated investigator when auth is enabled."""
    return _AuthedClient(auth_headers)


@pytest.fixture
def supervisor_headers(raw_client: TestClient):
    if not settings.auth_enabled:
        return {}
    res = raw_client.post(
        "/auth/login",
        json={"badge_id": "SUP-1001", "password": "admin2026"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_client(client: _AuthedClient):
    return client
