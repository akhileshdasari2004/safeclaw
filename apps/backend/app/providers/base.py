"""Cloud provider abstraction — isolates SDK differences."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProvisionedServer:
    server_id: str
    ip_address: str
    monthly_cost_usd: float


@dataclass
class RegionInfo:
    id: str
    name: str
    country: str | None = None


@dataclass
class PlanInfo:
    id: str
    name: str
    vcpus: int
    memory_gb: int
    disk_gb: int
    monthly_cost_usd: float


class CloudProviderBase(ABC):
    name: str

    @abstractmethod
    def list_regions(self) -> list[RegionInfo]:
        pass

    @abstractmethod
    def list_plans(self, region: str) -> list[PlanInfo]:
        pass

    @abstractmethod
    def create_server(
        self,
        name: str,
        region: str,
        plan_id: str,
        ssh_public_key: str,
    ) -> ProvisionedServer:
        pass

    @abstractmethod
    def delete_server(self, server_id: str) -> None:
        pass

    @abstractmethod
    def get_server_ip(self, server_id: str) -> str | None:
        pass

    @abstractmethod
    def get_estimated_monthly_spend(self) -> float:
        """Return account-level estimated monthly spend in USD."""
        pass
