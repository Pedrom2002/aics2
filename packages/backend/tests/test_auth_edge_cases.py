"""Edge cases for auth: expired JWT, rate limit breach, concurrent refresh race."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from httpx import AsyncClient

from src.config import settings


async def _register(client: AsyncClient, email: str, org: str = "Edge Team") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": f"{org}-{email}",
            "email": email,
            "password": "securepassword123",
            "display_name": "Edge User",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_expired_access_token_rejected(client: AsyncClient):
    """An access token past its exp must be rejected by protected endpoints."""
    data = await _register(client, "expired@test.com")
    user_id = data["user"]["id"]
    org_id = data["organization"]["id"]

    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": "admin",
        "email": "expired@test.com",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    expired = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    response = await client.get(
        "/api/v1/demos",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tampered_jwt_rejected(client: AsyncClient):
    """A JWT signed with the wrong secret must be rejected."""
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000000",
            "org_id": "00000000-0000-0000-0000-000000000000",
            "role": "admin",
            "email": "attacker@evil.com",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        "this-is-not-the-real-secret",
        algorithm="HS256",
    )
    response = await client.get(
        "/api/v1/demos",
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_reuse_detected(client: AsyncClient):
    """Re-using an already-rotated refresh token must fail (rotation invariant)."""
    reg = await _register(client, "reuse@test.com")
    original = reg["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert first.status_code == 200

    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_concurrent_refresh_single_success(client: AsyncClient):
    """Two parallel refreshes with the same token: at most one may succeed."""
    reg = await _register(client, "concurrent@test.com")
    refresh_token = reg["refresh_token"]

    results = await asyncio.gather(
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
        return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
    assert len(successes) <= 1


@pytest.mark.asyncio
async def test_invalid_refresh_token_rejected(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "obviously-not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client: AsyncClient):
    """Pydantic enforces a minimum password length."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Weak PW",
            "email": "weak@test.com",
            "password": "123",
            "display_name": "Weak",
        },
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_logout_twice_idempotent(client: AsyncClient):
    reg = await _register(client, "logout2@test.com")
    rt = reg["refresh_token"]

    first = await client.post("/api/v1/auth/logout", json={"refresh_token": rt})
    assert first.status_code in (204, 200)

    second = await client.post("/api/v1/auth/logout", json={"refresh_token": rt})
    assert second.status_code in (204, 200, 401)
