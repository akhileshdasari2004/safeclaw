from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.schemas.billing import CheckoutRequest, CheckoutSessionResponse
from app.services import stripe_service
from app.utils.audit import log_audit

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    body: CheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionResponse:
    try:
        session = stripe_service.create_checkout_session(body.email, body.tier)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await log_audit(
        db,
        "billing.checkout_created",
        ip_address=request.client.host if request.client else None,
        details=f"tier={body.tier}",
    )
    return CheckoutSessionResponse(checkout_url=session.url, session_id=session.id)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature")

    try:
        result = await stripe_service.process_webhook_event(db, payload, signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result


@router.get("/subscription")
async def subscription_status(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    from sqlalchemy import select
    from app.models.subscription import Subscription

    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"status": "none"}
    return {
        "status": sub.status,
        "tier": sub.tier,
        "stripe_subscription_id": sub.stripe_subscription_id,
        "stripe_customer_id": sub.stripe_customer_id,
        "updated_at": sub.updated_at.isoformat(),
    }


@router.post("/portal")
async def billing_portal(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    from sqlalchemy import select
    from app.models.subscription import Subscription

    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer on file")
    try:
        session = stripe_service.create_portal_session(sub.stripe_customer_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"portal_url": session.url}
