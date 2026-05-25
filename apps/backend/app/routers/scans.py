import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.middleware.license import require_active_license
from app.models.license import License
from app.models.scan import Scan
from app.schemas.scan import ScanResponse, ScanResultSchema
from app.services.scanner import run_scan
from app.utils.security import decrypt_secret

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/deployments/{deployment_id}", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def trigger_scan(
    deployment_id: uuid.UUID,
    user: CurrentUser,
    license_row: License = Depends(require_active_license),
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    from app.models.deployment import Deployment

    dep_result = await db.execute(
        select(Deployment).where(Deployment.id == deployment_id, Deployment.user_id == user.id)
    )
    dep = dep_result.scalar_one_or_none()
    private_key = None
    if dep and dep.encrypted_ssh_private_key:
        try:
            private_key = decrypt_secret(dep.encrypted_ssh_private_key)
        except ValueError:
            pass

    try:
        scan = await run_scan(db, deployment_id, user.id, private_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    findings = scan.findings_json
    return ScanResponse(
        id=scan.id,
        deployment_id=scan.deployment_id,
        score=scan.score,
        grade=scan.grade,
        findings=ScanResultSchema(**findings),
        created_at=scan.created_at,
    )


@router.get("/deployments/{deployment_id}", response_model=list[ScanResponse])
async def list_scans(
    deployment_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ScanResponse]:
    from app.models.deployment import Deployment

    dep = await db.execute(
        select(Deployment).where(Deployment.id == deployment_id, Deployment.user_id == user.id)
    )
    if not dep.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Deployment not found")

    result = await db.execute(
        select(Scan).where(Scan.deployment_id == deployment_id).order_by(Scan.created_at.desc())
    )
    out = []
    for scan in result.scalars().all():
        out.append(
            ScanResponse(
                id=scan.id,
                deployment_id=scan.deployment_id,
                score=scan.score,
                grade=scan.grade,
                findings=ScanResultSchema(**scan.findings_json),
                created_at=scan.created_at,
            )
        )
    return out
