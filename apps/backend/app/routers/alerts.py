import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.alert import Alert
from app.models.alert_history import AlertHistory
from app.schemas.alert import (
    AlertCreateRequest,
    AlertHistoryResponse,
    AlertResponse,
    AlertUpdateRequest,
)
from app.services.alerts import send_test_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[Alert]:
    result = await db.execute(select(Alert).where(Alert.user_id == user.id))
    return list(result.scalars().all())


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Alert:
    alert = Alert(
        user_id=user.id,
        threshold=body.threshold,
        enabled=body.enabled,
        cooldown_hours=body.cooldown_hours,
    )
    db.add(alert)
    await db.flush()
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: uuid.UUID,
    body: AlertUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Alert:
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if body.threshold is not None:
        alert.threshold = body.threshold
    if body.enabled is not None:
        alert.enabled = body.enabled
    if body.cooldown_hours is not None:
        alert.cooldown_hours = body.cooldown_hours
    await db.flush()
    return alert


@router.get("/history", response_model=list[AlertHistoryResponse])
async def alert_history(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> list[AlertHistory]:
    result = await db.execute(
        select(AlertHistory)
        .where(AlertHistory.user_id == user.id)
        .order_by(AlertHistory.created_at.desc())
        .limit(min(limit, 100))
    )
    return list(result.scalars().all())


@router.post("/{alert_id}/test")
async def test_alert(
    alert_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await send_test_alert(db, user.id, alert_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
