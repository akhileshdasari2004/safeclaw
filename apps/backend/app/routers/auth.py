from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.license import License
from app.models.user import User
from app.schemas.auth import (
    LicenseResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.utils.audit import log_audit
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.flush()

    if body.license_key:
        lic = await db.execute(
            select(License).where(License.key == body.license_key, License.active.is_(True))
        )
        license_row = lic.scalar_one_or_none()
        if not license_row:
            raise HTTPException(status_code=400, detail="Invalid license key")
        if license_row.user_id and license_row.user_id != user.id:
            # Allow claiming unassigned keys only if no user — for MVP assign to purchaser email flow
            if license_row.user_id:
                raise HTTPException(status_code=400, detail="License already assigned")
        license_row.user_id = user.id

    await log_audit(
        db, "user.register", user_id=user.id, ip_address=request.client.host if request.client else None
    )
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: dict, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="refresh_token required")
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return TokenResponse(
        access_token=create_access_token(payload["sub"]),
        refresh_token=create_refresh_token(payload["sub"]),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> User:
    return user


@router.get("/licenses", response_model=list[LicenseResponse])
async def my_licenses(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[License]:
    result = await db.execute(select(License).where(License.user_id == user.id))
    return list(result.scalars().all())
