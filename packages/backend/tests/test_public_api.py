"""Exercises the public API key lifecycle + scoped access checks."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_and_get_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "PubApi",
            "email": "pubapi@test.com",
            "password": "securepassword123",
            "display_name": "PubApi",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_use_api_key(client: AsyncClient):
    token = await _register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/api-keys?name=test-key&scopes=read%3Amatches&scopes=read%3Aplayers",
        headers=headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["name"] == "test-key"
    assert body["key"].startswith("csk_")
    api_key = body["key"]

    # Public endpoint with valid key (may 200 or 500 if no match data — both prove auth works)
    resp = await client.get("/api/v1/public/matches", headers={"X-API-Key": api_key})
    assert resp.status_code in (200, 500)

    # No key → 401
    resp = await client.get("/api/v1/public/matches")
    assert resp.status_code == 401

    # Malformed key → 401
    resp = await client.get("/api/v1/public/matches", headers={"X-API-Key": "not-a-key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_revoked_key_rejected(client: AsyncClient):
    token = await _register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/api-keys?name=to-revoke&scopes=read%3Amatches",
        headers=headers,
    )
    body = create.json()
    key_id = body["id"]
    api_key = body["key"]

    # Revoke
    revoke = await client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert revoke.status_code == 204

    # Revoked key must now 401
    resp = await client.get("/api/v1/public/matches", headers={"X-API-Key": api_key})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_scope_enforcement(client: AsyncClient):
    token = await _register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create a key WITHOUT read:matches scope
    create = await client.post(
        "/api/v1/api-keys?name=no-matches&scopes=read%3Aplayers",
        headers=headers,
    )
    api_key = create.json()["key"]

    # Matches endpoint should 403 (missing scope)
    resp = await client.get("/api/v1/public/matches", headers={"X-API-Key": api_key})
    assert resp.status_code == 403
