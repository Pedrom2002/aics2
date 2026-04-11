"""Tests for SSE demo status stream endpoint."""

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_get_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "SSETestOrg",
            "email": "sse@test.com",
            "password": "testpassword123",
            "display_name": "SSEUser",
        },
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_sse_requires_auth(client: AsyncClient):
    """SSE endpoint requires authentication."""
    demo_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/demos/{demo_id}/status")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_sse_demo_not_found(client: AsyncClient):
    """SSE for non-existent demo sends error event."""
    token = await _register_and_get_token(client)
    demo_id = uuid.uuid4()

    resp = await client.get(
        f"/api/v1/demos/{demo_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    # The response should contain an error event for missing demo
    body = resp.text
    assert "error" in body or "not found" in body.lower() or "Demo not found" in body


@pytest.mark.asyncio
async def test_sse_content_type(client: AsyncClient):
    """SSE endpoint returns correct content type."""
    token = await _register_and_get_token(client)
    demo_id = uuid.uuid4()

    resp = await client.get(
        f"/api/v1/demos/{demo_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert "text/event-stream" in resp.headers.get("content-type", "")
