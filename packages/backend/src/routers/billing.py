"""Stripe billing integration — checkout, webhooks, customer portal."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, update

from src.config import settings
from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.organization import Organization

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.schemas.auth import TokenPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])
limiter = Limiter(key_func=get_remote_address)

STRIPE_PRICE_IDS = {
    "solo": settings.STRIPE_PRICE_SOLO,
    "team": settings.STRIPE_PRICE_TEAM,
    "pro": settings.STRIPE_PRICE_PRO,
}

# Tier → max demos mapping
TIER_LIMITS = {
    "free": 10,
    "solo": 15,
    "team": 30,
    "pro": 9999,
    "enterprise": 9999,
}


def _get_stripe():
    """Lazy import stripe to avoid errors when not installed."""
    try:
        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        return stripe
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. Install stripe package.",
        ) from exc


@router.post("/checkout")
@limiter.limit("5/minute")
async def create_checkout_session(
    request: Request,
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
            success_url=f"{settings.FRONTEND_URL}/dashboard/settings?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard/settings?cancelled=true",
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
@limiter.limit("5/minute")
async def create_portal_session(
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing subscription."""
    stripe = _get_stripe()

    org_id = uuid.UUID(current_user.org_id)
    result = await db.execute(
        select(Organization.stripe_customer_id).where(Organization.id == org_id)
    )
    customer_id = result.scalar_one_or_none()

    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription. Upgrade first.",
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard/settings",
        )
        return {"portal_url": session.url}
    except Exception as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create portal session") from e


_PRICE_TO_TIER = {
    settings.STRIPE_PRICE_SOLO: "solo",
    settings.STRIPE_PRICE_TEAM: "team",
    settings.STRIPE_PRICE_PRO: "pro",
}


def _tier_from_subscription_data(data: dict) -> str | None:
    """Resolve a tier name from a Stripe subscription payload."""
    try:
        items = data.get("items", {}).get("data", [])
        for item in items:
            price_id = (item.get("price") or {}).get("id")
            tier = _PRICE_TO_TIER.get(price_id)
            if tier:
                return tier
    except (AttributeError, TypeError):
        pass
    return data.get("metadata", {}).get("tier") if isinstance(data.get("metadata"), dict) else None


async def _update_org_by_customer(
    db: AsyncSession,
    customer_id: str | None,
    **values,
) -> None:
    if not customer_id:
        return
    await db.execute(
        update(Organization).where(Organization.stripe_customer_id == customer_id).values(**values)
    )
    await db.commit()


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events with signature verification.

    Handled event types:
    - payment_intent.succeeded
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.paid
    - checkout.session.completed (kept from prior implementation)

    Returns 200 for handled/ignored events, 400 for invalid signatures.
    """
    stripe = _get_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        # Fail closed if signing secret not configured (mirrors Stripe SDK behavior)
        raise HTTPException(status_code=400, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as exc:  # noqa: BLE001 — Stripe raises generic exceptions
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {}) or {}

    # Idempotency: dedup by Stripe event id via Redis (24h TTL).
    if event_id:
        try:
            from redis.asyncio import Redis

            redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            key = f"stripe:event:{event_id}"
            was_set = await redis_client.set(key, "1", nx=True, ex=86400)
            await redis_client.close()
            if not was_set:
                logger.info("Stripe event %s already processed — skipping", event_id)
                return {"status": "duplicate", "event": event_type}
        except Exception as exc:  # noqa: BLE001 — dedup is best-effort
            logger.warning("Idempotency check failed (continuing): %s", exc)

    try:
        if event_type == "checkout.session.completed":
            org_id = data.get("client_reference_id") or data.get("metadata", {}).get("org_id")
            tier = data.get("metadata", {}).get("tier", "solo")
            customer_id = data.get("customer")
            subscription_id = data.get("subscription")
            if org_id:
                await db.execute(
                    update(Organization)
                    .where(Organization.id == uuid.UUID(org_id))
                    .values(
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                        tier=tier,
                        subscription_status="active",
                        max_demos_per_month=TIER_LIMITS.get(tier, 10),
                    )
                )
                await db.commit()
                logger.info("Activated subscription: org=%s tier=%s", org_id, tier)

        elif event_type == "payment_intent.succeeded":
            customer_id = data.get("customer")
            logger.info(
                "Payment succeeded: customer=%s amount=%s", customer_id, data.get("amount_received")
            )
            await _update_org_by_customer(db, customer_id, subscription_status="active")

        elif event_type == "customer.subscription.created":
            customer_id = data.get("customer")
            subscription_id = data.get("id")
            status = data.get("status", "active")
            tier = _tier_from_subscription_data(data) or "solo"
            await _update_org_by_customer(
                db,
                customer_id,
                stripe_subscription_id=subscription_id,
                tier=tier,
                subscription_status=status,
                max_demos_per_month=TIER_LIMITS.get(tier, 10),
            )
            logger.info("Subscription created: customer=%s tier=%s", customer_id, tier)

        elif event_type == "customer.subscription.updated":
            customer_id = data.get("customer")
            status = data.get("status", "active")
            tier = _tier_from_subscription_data(data)
            values: dict = {"subscription_status": status}
            if tier:
                values["tier"] = tier
                values["max_demos_per_month"] = TIER_LIMITS.get(tier, 10)
            await _update_org_by_customer(db, customer_id, **values)
            logger.info(
                "Subscription updated: customer=%s status=%s tier=%s",
                customer_id,
                status,
                tier,
            )

        elif event_type == "customer.subscription.deleted":
            customer_id = data.get("customer")
            await _update_org_by_customer(
                db,
                customer_id,
                tier="free",
                max_demos_per_month=TIER_LIMITS["free"],
                stripe_subscription_id=None,
                subscription_status="canceled",
            )
            logger.info("Subscription cancelled, downgraded to free: customer=%s", customer_id)

        elif event_type == "invoice.paid":
            customer_id = data.get("customer")
            await _update_org_by_customer(db, customer_id, subscription_status="active")
            logger.info("Invoice paid: customer=%s", customer_id)

        elif event_type == "invoice.payment_failed":
            customer_id = data.get("customer")
            await _update_org_by_customer(db, customer_id, subscription_status="past_due")
            logger.warning("Payment failed: customer=%s", customer_id)

        else:
            logger.debug("Ignoring Stripe event type: %s", event_type)

    except Exception as exc:  # pragma: no cover — safety net
        logger.exception("Error handling Stripe event %s: %s", event_type, exc)
        # Still return 200 so Stripe does not keep retrying for handler bugs
        return {"status": "error", "event": event_type}

    return {"status": "ok", "event": event_type}
