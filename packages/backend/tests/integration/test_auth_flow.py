"""Integration test: full auth lifecycle.

Exercises register → login → refresh → access protected endpoint → logout
→ confirm refresh token is revoked. Reuses the `client` fixture from
`tests/conftest.py` (SQLite in-memory + ASGI transport).

These tests intentionally hit several routers in sequence so a regression
in any of register / login / refresh / logout / get_current_user is caught
by a single failing test, complementing the unit tests in `test_auth.py`.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_auth_lifecycle(client: AsyncClient) -> None:
    # 1. Register a fresh org/user
    register_payload = {
        "org_name": "Integration Org",
        "email": "integration@test.com",
        "password": "IntegrationPass123!",
        "display_name": "Integration User",
    }
    register_resp = await client.post("/api/v1/auth/register", json=register_payload)
    assert register_resp.status_code == 201, register_resp.text
    register_data = register_resp.json()
    assert register_data["user"]["email"] == register_payload["email"]
    assert "access_token" in register_data
    assert "refresh_token" in register_data

    initial_access = register_data["access_token"]
    initial_refresh = register_data["refresh_token"]

    # 2. Login as the same user
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    )
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    assert access_token  # non-empty
    assert refresh_token

    # 3. Refresh tokens
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    refreshed = refresh_resp.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]
    assert refreshed["refresh_token"] != refresh_token, "refresh token should rotate"

    new_access = refreshed["access_token"]
    new_refresh = refreshed["refresh_token"]

    # 4. Access a protected endpoint with the new access token.
    #    /api/v1/demos requires auth and should return an empty pagination envelope.
    protected = await client.get(
        "/api/v1/demos",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert protected.status_code == 200, protected.text
    body = protected.json()
    # Pagination envelope shape from PaginatedResponse
    assert "items" in body
    assert "total" in body

    # 5. Access without token must fail
    no_auth = await client.get("/api/v1/demos")
    assert no_auth.status_code in (401, 403)

    # 6. Logout — current refresh token should be revoked
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh},
    )
    assert logout_resp.status_code == 204

    # 7. Refreshing with the revoked token must fail
    revoked_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert revoked_refresh.status_code == 401

    # 8. The original (pre-refresh) tokens should also be invalid by now
    stale_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert stale_refresh.status_code == 401

    # 9. Sanity: the very first access token from register is no longer required
    #    to work after refresh, but most JWT setups will still accept it until
    #    expiry. We just assert it doesn't crash the server.
    sanity = await client.get(
        "/api/v1/demos",
        headers={"Authorization": f"Bearer {initial_access}"},
    )
    assert sanity.status_code in (200, 401)


@pytest.mark.asyncio
async def test_login_then_protected_then_logout(client: AsyncClient) -> None:
    """Smaller flow that focuses on the happy path only."""
    payload = {
        "org_name": "Quick Org",
        "email": "quick@test.com",
        "password": "QuickPass123!",
        "display_name": "Quick User",
    }
    reg = await client.post("/api/v1/auth/register", json=payload)
    assert reg.status_code == 201
    tokens = reg.json()

    me_resp = await client.get(
        "/api/v1/demos",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_resp.status_code == 200

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 204
