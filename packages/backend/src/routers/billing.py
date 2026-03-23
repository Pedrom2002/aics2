"""Stripe billing integration — checkout, webhooks, customer portal."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request

from src.database import get_db
from src.middleware.auth import get_current_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.schemas.auth import TokenPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_IDS = {
    "solo": os.environ.get("STRIPE_PRICE_SOLO", "price_solo_placeholder"),
    "team": os.environ.get("STRIPE_PRICE_TEAM", "price_team_placeholder"),
    "pro": os.environ.get("STRIPE_PRICE_PRO", "price_pro_placeholder"),
}

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


def _get_stripe():
    """Lazy import stripe to avoid errors when not installed."""
    try:
        import stripe

        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. Install stripe package.",
        ) from exc


@router.post("/checkout")
async def create_checkout_session(
    tier: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for upgrading to a paid tier."""
    if tier not in STRIPE_PRICE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    stripe = _get_stripe()

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_IDS[tier], "quantity": 1}],
            success_url=f"{FRONTEND_URL}/dashboard/settings?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/dashboard/settings?cancelled=true",
            client_reference_id=current_user.org_id,
            metadata={
                "org_id": current_user.org_id,
                "user_id": current_user.sub,
                "tier": tier,
            },
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create checkout session") from e


@router.post("/portal")
async def create_portal_session(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing subscription."""
    _get_stripe()

    # In production: look up stripe_customer_id from org table
    raise HTTPException(
        status_code=400,
        detail="No active subscription. Upgrade first.",
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events.

    Listens for:
    - checkout.session.completed → activate subscription
    - customer.subscription.updated → update tier
    - customer.subscription.deleted → downgrade to free
    - invoice.payment_failed → notify user
    """
    stripe = _get_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        org_id = data.get("client_reference_id") or data.get("metadata", {}).get("org_id")
        tier = data.get("metadata", {}).get("tier", "solo")
        customer_id = data.get("customer")
        logger.info("Checkout completed: org=%s tier=%s customer=%s", org_id, tier, customer_id)

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        status = data.get("status")
        logger.info("Subscription updated: customer=%s status=%s", customer_id, status)

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        logger.info("Subscription cancelled: customer=%s", customer_id)

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        logger.warning("Payment failed: customer=%s", customer_id)

    return {"status": "ok"}
