"""Wraps cloud providers with retry/backoff on transient API errors."""

from __future__ import annotations

from app.providers.base import CloudProviderBase, PlanInfo, ProvisionedServer, RegionInfo
from app.providers.retry import call_with_backoff


class ResilientCloudProvider(CloudProviderBase):
    def __init__(self, inner: CloudProviderBase) -> None:
        self._inner = inner
        self.name = inner.name

    def list_regions(self) -> list[RegionInfo]:
        return self._inner.list_regions()

    def list_plans(self, region: str) -> list[PlanInfo]:
        return self._inner.list_plans(region)

    def create_server(
        self,
        name: str,
        region: str,
        plan_id: str,
        ssh_public_key: str,
    ) -> ProvisionedServer:
        return call_with_backoff(
            lambda: self._inner.create_server(name, region, plan_id, ssh_public_key)
        )

    def delete_server(self, server_id: str) -> None:
        return call_with_backoff(lambda: self._inner.delete_server(server_id))

    def get_server_ip(self, server_id: str) -> str | None:
        return call_with_backoff(lambda: self._inner.get_server_ip(server_id))

    def get_estimated_monthly_spend(self) -> float:
        return self._inner.get_estimated_monthly_spend()
