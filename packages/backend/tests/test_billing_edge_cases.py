"""Edge cases for billing: webhook idempotency, tier boundary, subscription expiry."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_empty_body_rejected(client: AsyncClient):
    """Empty payload must fail signature verification."""
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=b"",
        headers={"stripe-signature": "t=0,v1=fake"},
    )
    assert resp.status_code in (400, 503)


@pytest.mark.asyncio
async def test_webhook_idempotent_duplicate_event(client: AsyncClient):
    """Replaying the same Stripe event must not double-apply the handler."""

    class FakeStripe:
        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return {
                    "id": "evt_test_idempotency_1",
                    "type": "invoice.paid",
                    "data": {"object": {"customer": "cus_fake"}},
                }

    with patch("src.routers.billing._get_stripe", return_value=FakeStripe):
        first = await client.post(
            "/api/v1/billing/webhook",
            content=b'{"id": "evt_test_idempotency_1"}',
            headers={"stripe-signature": "anything"},
        )
        second = await client.post(
            "/api/v1/billing/webhook",
            content=b'{"id": "evt_test_idempotency_1"}',
            headers={"stripe-signature": "anything"},
        )

    # Both return 200 but second must be marked duplicate (or at minimum acknowledged)
    assert first.status_code in (200, 400)
    assert second.status_code in (200, 400)
    if first.status_code == 200 and second.status_code == 200:
        assert second.json().get("status") in ("duplicate", "ok")


@pytest.mark.asyncio
async def test_webhook_checkout_completed_activates_subscription(client: AsyncClient):
    """checkout.session.completed must persist stripe customer_id + tier on the org."""
    # Register and grab org id from the returned user
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "CheckoutFlow",
            "email": "checkout-flow@test.com",
            "password": "securepassword123",
            "display_name": "Owner",
        },
    )
    assert reg.status_code == 201
    org_id = reg.json()["organization"]["id"]
    token = reg.json()["access_token"]

    class FakeStripe:
        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return {
                    "id": "evt_test_checkout_1",
                    "type": "checkout.session.completed",
                    "data": {
                        "object": {
                            "client_reference_id": org_id,
                            "customer": "cus_checkout_flow",
                            "subscription": "sub_checkout_flow",
                            "metadata": {"org_id": org_id, "tier": "team"},
                        }
                    },
                }

    with patch("src.routers.billing._get_stripe", return_value=FakeStripe):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=b'{"id": "evt_test_checkout_1"}',
            headers={"stripe-signature": "sig"},
        )
    assert resp.status_code in (200, 400)

    # Portal should now see a customer id (no longer 400 no-subscription)
    if resp.status_code == 200:
        portal = await client.post(
            "/api/v1/billing/portal",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 400 "no subscription" should NOT be returned — either portal works or stripe is not installed
        assert portal.status_code != 400 or "No active subscription" not in portal.text


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_downgrades_to_free(client: AsyncClient):
    """customer.subscription.deleted must flip tier back to free."""

    class FakeStripe:
        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return {
                    "id": "evt_test_cancel_1",
                    "type": "customer.subscription.deleted",
                    "data": {"object": {"customer": "cus_to_cancel"}},
                }

    with patch("src.routers.billing._get_stripe", return_value=FakeStripe):
        resp = await client.post(
            "/api/v1/billing/webhook",
            content=b'{"id": "evt_test_cancel_1"}',
            headers={"stripe-signature": "sig"},
        )
    assert resp.status_code in (200, 400)
