import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.alert import Alert
from app.schemas.alert import AlertCreateRequest, AlertResponse, AlertUpdateRequest

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
    alert = Alert(user_id=user.id, threshold=body.threshold, enabled=body.enabled)
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
    await db.flush()
    return alert
