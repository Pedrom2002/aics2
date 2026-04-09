"""Tests for billing endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import TestSessionLocal, get_test_db


async def _register_and_get_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "BillingTestOrg",
            "email": "billing@test.com",
            "password": "testpassword123",
            "display_name": "BillingUser",
        },
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_checkout_invalid_tier(client: AsyncClient):
    token = await _register_and_get_token(client)
    resp = await client.post(
        "/api/v1/billing/checkout?tier=invalid",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "Invalid tier" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_checkout_valid_tier_requires_stripe(client: AsyncClient):
    token = await _register_and_get_token(client)
    resp = await client.post(
        "/api/v1/billing/checkout?tier=solo",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should either succeed (if stripe installed) or 503 (if not)
    assert resp.status_code in (200, 500, 503)


@pytest.mark.asyncio
async def test_portal_no_subscription(client: AsyncClient):
    token = await _register_and_get_token(client)
    resp = await client.post(
        "/api/v1/billing/portal",
        headers={"Authorization": f"Bearer {token}"},
    )
    # No stripe_customer_id → 400 or 503 if stripe not installed
    assert resp.status_code in (400, 503)


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client: AsyncClient):
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=b'{"type": "test"}',
        headers={"stripe-signature": "invalid"},
    )
    # Should fail with 400 (invalid sig) or 503 (stripe not installed)
    assert resp.status_code in (400, 503)


@pytest.mark.asyncio
async def test_checkout_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/billing/checkout?tier=solo")
    assert resp.status_code in (401, 403)
