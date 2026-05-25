"""Stripe Checkout and webhook processing."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.billing_event import BillingEvent
from app.models.license import License
from app.models.subscription import Subscription
from app.models.user import User
from app.services.email_service import send_license_email
from app.utils.logging import get_logger
from app.utils.security import generate_license_key, hash_password

logger = get_logger(__name__)


def create_checkout_session(email: str, tier: str) -> stripe.checkout.Session:
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    price_id = (
        settings.stripe_price_id_pro
        if tier == "pro"
        else settings.stripe_price_id_starter
    )
    if not price_id:
        raise ValueError("Stripe price ID not configured for tier")

    return stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"tier": tier, "email": email},
    )


async def process_webhook_event(
    db: AsyncSession,
    payload: bytes,
    signature: str,
) -> dict:
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError as e:
        raise ValueError("Invalid webhook signature") from e

    event_id = event["id"]
    existing = await db.execute(
        select(BillingEvent).where(BillingEvent.stripe_event_id == event_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}

    billing = BillingEvent(
        stripe_event_id=event_id,
        event_type=event["type"],
        processed=False,
        payload_json=json.dumps(event["data"]),
    )
    db.add(billing)
    await db.flush()

    if event["type"] == "checkout.session.completed":
        await _handle_checkout_completed(db, event)
    elif event["type"] in ("invoice.payment_failed", "customer.subscription.deleted"):
        await _handle_subscription_issue(db, event)

    billing.processed = True
    await db.flush()
    return {"status": "processed"}


async def _handle_checkout_completed(db: AsyncSession, event: dict) -> None:
    session = event["data"]["object"]
    email = session.get("customer_email") or session.get("metadata", {}).get("email")
    tier = session.get("metadata", {}).get("tier", "starter")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not email:
        logger.error("checkout_missing_email", session_id=session.get("id"))
        return

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        import secrets
        temp_password = secrets.token_urlsafe(16)
        user = User(email=email, hashed_password=hash_password(temp_password))
        db.add(user)
        await db.flush()

    license_key = generate_license_key()
    expires = datetime.now(timezone.utc) + timedelta(days=365)
    license_row = License(
        key=license_key,
        tier=tier,
        active=True,
        user_id=user.id,
        expires_at=expires,
    )
    db.add(license_row)

    sub = Subscription(
        user_id=user.id,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        status="active",
        tier=tier,
    )
    db.add(sub)
    await db.flush()

    send_license_email(email, license_key, tier)
    logger.info("license_created", user_id=str(user.id), tier=tier)


async def _handle_subscription_issue(db: AsyncSession, event: dict) -> None:
    obj = event["data"]["object"]
    customer_id = obj.get("customer")
    if not customer_id:
        return
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return
    sub.status = "inactive" if event["type"] == "customer.subscription.deleted" else "past_due"
    lic_result = await db.execute(
        select(License).where(License.user_id == sub.user_id, License.active.is_(True))
    )
    for lic in lic_result.scalars().all():
        lic.active = event["type"] != "invoice.payment_failed"
    await db.flush()
