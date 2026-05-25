"""Mock cloud providers for tests."""

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
        pass

    def get_server_ip(self, server_id: str) -> str | None:
        return "203.0.113.10"

    def get_estimated_monthly_spend(self) -> float:
        return 6.49
