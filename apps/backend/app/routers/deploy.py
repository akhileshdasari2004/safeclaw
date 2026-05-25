import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.middleware.license import require_active_license
from app.models.deployment import Deployment
from app.models.license import License
from app.providers.factory import get_provider
from app.schemas.deploy import (
    DeployCreateRequest,
    DeployResponse,
    PlanItem,
    ProviderPlansResponse,
    ProviderRegionsResponse,
    RegionItem,
)
from app.services.provision import run_provision
from app.utils.audit import log_audit
from app.utils.security import encrypt_secret

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get("/providers/{provider}/regions", response_model=ProviderRegionsResponse)
async def list_regions(provider: str, user: CurrentUser) -> ProviderRegionsResponse:
    try:
        p = get_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ProviderRegionsResponse(
        provider=provider,
        regions=[RegionItem(id=r.id, name=r.name, country=r.country) for r in p.list_regions()],
    )


@router.get("/providers/{provider}/plans", response_model=ProviderPlansResponse)
async def list_plans(provider: str, region: str, user: CurrentUser) -> ProviderPlansResponse:
    try:
        p = get_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ProviderPlansResponse(
        provider=provider,
        plans=[
            PlanItem(
                id=pl.id,
                name=pl.name,
                vcpus=pl.vcpus,
                memory_gb=pl.memory_gb,
                disk_gb=pl.disk_gb,
                monthly_cost_usd=pl.monthly_cost_usd,
            )
            for pl in p.list_plans(region)
        ],
    )


@router.get("", response_model=list[DeployResponse])
async def list_deployments(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[Deployment]:
    result = await db.execute(
        select(Deployment).where(Deployment.user_id == user.id).order_by(Deployment.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{deployment_id}", response_model=DeployResponse)
async def get_deployment(
    deployment_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Deployment:
    result = await db.execute(
        select(Deployment).where(Deployment.id == deployment_id, Deployment.user_id == user.id)
    )
    dep = result.scalar_one_or_none()
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return dep


@router.post("", response_model=DeployResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_deployment(
    body: DeployCreateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: CurrentUser,
    license_row: License = Depends(require_active_license),
    db: AsyncSession = Depends(get_db),
) -> Deployment:
    if body.idempotency_key:
        existing = await db.execute(
            select(Deployment).where(Deployment.idempotency_key == body.idempotency_key)
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

    deployment = Deployment(
        user_id=user.id,
        provider=body.provider,
        region=body.region,
        server_name=body.server_name,
        plan_id=body.plan_id,
        status="pending",
        idempotency_key=body.idempotency_key,
        logs=f"SSH_PUBLIC_KEY:{body.ssh_public_key}\n",
    )
    db.add(deployment)
    await db.flush()

    await log_audit(
        db,
        "deployment.created",
        user_id=user.id,
        resource_type="deployment",
        resource_id=str(deployment.id),
        ip_address=request.client.host if request.client else None,
    )

    private_key = body.ssh_private_key
    if private_key:
        deployment.encrypted_ssh_private_key = encrypt_secret(private_key)

    async def _provision_task() -> None:
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            try:
                pk = None
                if private_key:
                    pk = private_key
                elif deployment.encrypted_ssh_private_key:
                    from app.utils.security import decrypt_secret
                    pk = decrypt_secret(deployment.encrypted_ssh_private_key)
                await run_provision(session, deployment.id, pk)
                await session.commit()
            except Exception:
                await session.rollback()

    background_tasks.add_task(lambda: asyncio.run(_provision_task()))
    return deployment


@router.post("/{deployment_id}/retry", response_model=DeployResponse)
async def retry_deployment(
    deployment_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    license_row: License = Depends(require_active_license),
    db: AsyncSession = Depends(get_db),
) -> Deployment:
    result = await db.execute(
        select(Deployment).where(Deployment.id == deployment_id, Deployment.user_id == user.id)
    )
    dep = result.scalar_one_or_none()
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if dep.status not in ("failed", "pending"):
        raise HTTPException(status_code=400, detail="Only failed deployments can be retried")

    dep.status = "pending"
    dep.error_message = None

    async def _retry() -> None:
        from app.database import AsyncSessionLocal
        from app.utils.security import decrypt_secret

        async with AsyncSessionLocal() as session:
            pk = None
            if dep.encrypted_ssh_private_key:
                pk = decrypt_secret(dep.encrypted_ssh_private_key)
            try:
                await run_provision(session, dep.id, pk)
                await session.commit()
            except Exception:
                await session.rollback()

    background_tasks.add_task(lambda: asyncio.run(_retry()))
    return dep
