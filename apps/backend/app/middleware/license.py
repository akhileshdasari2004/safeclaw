from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.license import License


async def require_active_license(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> License:
    result = await db.execute(
        select(License).where(License.user_id == user.id, License.active.is_(True))
    )
    license_row = result.scalar_one_or_none()
    if not license_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active license required. Purchase a plan to continue.",
        )
    if license_row.expires_at and license_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License expired",
        )
    return license_row


ActiveLicense = Depends(require_active_license)
