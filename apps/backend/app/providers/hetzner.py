"""Hetzner Cloud provider — uses official hcloud Python SDK."""

from __future__ import annotations

from hcloud import Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType
from hcloud.ssh_keys import SSHKey

from app.providers.base import CloudProviderBase, PlanInfo, ProvisionedServer, RegionInfo
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Curated plans for MVP — maps to Hetzner server types
HETZNER_PLANS = [
    PlanInfo("cx22", "CX22", 2, 4, 40, 6.49),
    PlanInfo("cx32", "CX32", 4, 8, 80, 10.99),
    PlanInfo("cx42", "CX42", 8, 16, 160, 19.99),
]

HETZNER_REGIONS = [
    RegionInfo("fsn1", "Falkenstein", "DE"),
    RegionInfo("nbg1", "Nuremberg", "DE"),
    RegionInfo("hel1", "Helsinki", "FI"),
    RegionInfo("ash", "Ashburn", "US"),
]


class HetznerProvider(CloudProviderBase):
    name = "hetzner"

    def __init__(self, api_token: str) -> None:
        self._client = Client(token=api_token)

    def list_regions(self) -> list[RegionInfo]:
        return list(HETZNER_REGIONS)

    def list_plans(self, region: str) -> list[PlanInfo]:
        _ = region
        return list(HETZNER_PLANS)

    def _ensure_ssh_key(self, public_key: str, name: str) -> SSHKey:
        fingerprint = None
        try:
            import hashlib
            import base64

            parts = public_key.strip().split()
            if len(parts) >= 2:
                key_data = base64.b64decode(parts[1])
                fp = hashlib.md5(key_data).hexdigest()  # noqa: S324 — Hetzner uses MD5 fingerprint
                fingerprint = ":".join(a + b for a, b in zip(fp[::2], fp[1::2], strict=False))
        except Exception:
            pass

        keys = self._client.ssh_keys.get_all()
        for k in keys:
            if k.public_key.strip() == public_key.strip():
                return k
            if fingerprint and k.fingerprint == fingerprint:
                return k

        return self._client.ssh_keys.create(name=name, public_key=public_key)

    def create_server(
        self,
        name: str,
        region: str,
        plan_id: str,
        ssh_public_key: str,
    ) -> ProvisionedServer:
        ssh_key = self._ensure_ssh_key(ssh_public_key, f"safeclaw-{name}")
        server_type = ServerType(name=plan_id)
        location = Location(name=region)
        image = Image(name="ubuntu-22.04")

        response = self._client.servers.create(
            name=name,
            server_type=server_type,
            image=image,
            location=location,
            ssh_keys=[ssh_key],
            user_data=None,
            start_after_create=True,
        )
        server = response.server
        ipv4 = server.public_net.ipv4.ip if server.public_net.ipv4 else None
        if not ipv4:
            raise RuntimeError("Hetzner server created without IPv4 address")

        plan = next((p for p in HETZNER_PLANS if p.id == plan_id), HETZNER_PLANS[0])
        logger.info("hetzner_server_created", server_id=str(server.id), ip=ipv4)
        return ProvisionedServer(
            server_id=str(server.id),
            ip_address=ipv4,
            monthly_cost_usd=plan.monthly_cost_usd,
        )

    def delete_server(self, server_id: str) -> None:
        server = self._client.servers.get_by_id(int(server_id))
        if server:
            server.delete()

    def get_server_ip(self, server_id: str) -> str | None:
        server = self._client.servers.get_by_id(int(server_id))
        if server and server.public_net.ipv4:
            return server.public_net.ipv4.ip
        return None

    def get_estimated_monthly_spend(self) -> float:
        servers = self._client.servers.get_all()
        total = 0.0
        for s in servers:
            st = s.server_type.name if s.server_type else "cx22"
            plan = next((p for p in HETZNER_PLANS if p.id == st), HETZNER_PLANS[0])
            total += plan.monthly_cost_usd
        return total
