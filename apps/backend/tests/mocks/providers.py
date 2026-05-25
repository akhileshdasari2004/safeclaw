"""Mock cloud providers for tests."""

from __future__ import annotations

from app.providers.base import CloudProviderBase, PlanInfo, ProvisionedServer, RegionInfo


class MockProvider(CloudProviderBase):
    name = "hetzner"

    def list_regions(self) -> list[RegionInfo]:
        return [RegionInfo("fsn1", "Falkenstein", "DE")]

    def list_plans(self, region: str) -> list[PlanInfo]:
        return [PlanInfo("cx22", "CX22", 2, 4, 40, 6.49)]

    def create_server(self, name: str, region: str, plan_id: str, ssh_public_key: str) -> ProvisionedServer:
        return ProvisionedServer(server_id="mock-1", ip_address="203.0.113.10", monthly_cost_usd=6.49)

    def delete_server(self, server_id: str) -> None:
        self.deleted_servers.append(server_id)

    def __init__(self) -> None:
        self.deleted_servers: list[str] = []

    def get_server_ip(self, server_id: str) -> str | None:
        return "203.0.113.10"

    def get_estimated_monthly_spend(self) -> float:
        return 6.49


class TimeoutProvider(MockProvider):
    """Simulates provider API timeout."""

    def create_server(self, name: str, region: str, plan_id: str, ssh_public_key: str) -> ProvisionedServer:
        raise TimeoutError("Provider API timed out")


class RateLimitProvider(MockProvider):
    """Simulates HTTP 429 rate limit."""

    def create_server(self, name: str, region: str, plan_id: str, ssh_public_key: str) -> ProvisionedServer:
        raise RuntimeError("429 Too Many Requests")


class PartialCreateProvider(MockProvider):
    """Server created but missing IP — API inconsistency."""

    def create_server(self, name: str, region: str, plan_id: str, ssh_public_key: str) -> ProvisionedServer:
        return ProvisionedServer(server_id="partial-1", ip_address="", monthly_cost_usd=6.49)
