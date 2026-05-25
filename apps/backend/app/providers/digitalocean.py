"""DigitalOcean provider — uses DO REST API via httpx (stable, documented)."""

from __future__ import annotations

import httpx

from app.providers.base import CloudProviderBase, PlanInfo, ProvisionedServer, RegionInfo
from app.utils.logging import get_logger

logger = get_logger(__name__)

DO_API = "https://api.digitalocean.com/v2"

DO_REGIONS = [
    RegionInfo("nyc3", "New York 3", "US"),
    RegionInfo("sfo3", "San Francisco 3", "US"),
    RegionInfo("ams3", "Amsterdam 3", "NL"),
    RegionInfo("lon1", "London 1", "GB"),
    RegionInfo("fra1", "Frankfurt 1", "DE"),
]

DO_PLANS = [
    PlanInfo("s-1vcpu-2gb", "Basic 2GB", 1, 2, 50, 12.0),
    PlanInfo("s-2vcpu-4gb", "Basic 4GB", 2, 4, 80, 24.0),
    PlanInfo("s-4vcpu-8gb", "Basic 8GB", 4, 8, 160, 48.0),
]


class DigitalOceanProvider(CloudProviderBase):
    name = "digitalocean"

    def __init__(self, api_token: str) -> None:
        self._token = api_token
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self, method: str, path: str, json: dict | None = None
    ) -> dict:
        with httpx.Client(timeout=60.0) as client:
            resp = client.request(
                method, f"{DO_API}{path}", headers=self._headers, json=json
            )
            resp.raise_for_status()
            return resp.json()

    def list_regions(self) -> list[RegionInfo]:
        return list(DO_REGIONS)

    def list_plans(self, region: str) -> list[PlanInfo]:
        _ = region
        return list(DO_PLANS)

    def _ensure_ssh_key(self, public_key: str, name: str) -> int:
        data = self._request("GET", "/account/keys")
        for key in data.get("ssh_keys", []):
            if key.get("public_key", "").strip() == public_key.strip():
                return int(key["id"])

        created = self._request(
            "POST",
            "/account/keys",
            json={"name": name, "public_key": public_key},
        )
        return int(created["ssh_key"]["id"])

    def create_server(
        self,
        name: str,
        region: str,
        plan_id: str,
        ssh_public_key: str,
    ) -> ProvisionedServer:
        key_id = self._ensure_ssh_key(ssh_public_key, f"safeclaw-{name}")
        payload = {
            "name": name,
            "region": region,
            "size": plan_id,
            "image": "ubuntu-22-04-x64",
            "ssh_keys": [key_id],
            "ipv6": False,
            "monitoring": True,
            "tags": ["safeclaw"],
        }
        result = self._request("POST", "/droplets", json=payload)
        droplet = result["droplet"]
        droplet_id = str(droplet["id"])

        # Poll for active + IP
        import time

        ip: str | None = None
        for _ in range(60):
            info = self._request("GET", f"/droplets/{droplet_id}")
            d = info["droplet"]
            if d["status"] == "active":
                networks = d.get("networks", {}).get("v4", [])
                public = [n for n in networks if n.get("type") == "public"]
                if public:
                    ip = public[0]["ip_address"]
                    break
            time.sleep(5)

        if not ip:
            raise RuntimeError("DigitalOcean droplet failed to obtain public IP")

        plan = next((p for p in DO_PLANS if p.id == plan_id), DO_PLANS[0])
        logger.info("do_droplet_created", server_id=droplet_id, ip=ip)
        return ProvisionedServer(
            server_id=droplet_id,
            ip_address=ip,
            monthly_cost_usd=plan.monthly_cost_usd,
        )

    def delete_server(self, server_id: str) -> None:
        with httpx.Client(timeout=30.0) as client:
            client.delete(
                f"{DO_API}/droplets/{server_id}",
                headers=self._headers,
            )

    def get_server_ip(self, server_id: str) -> str | None:
        info = self._request("GET", f"/droplets/{server_id}")
        networks = info["droplet"].get("networks", {}).get("v4", [])
        public = [n for n in networks if n.get("type") == "public"]
        return public[0]["ip_address"] if public else None

    def get_estimated_monthly_spend(self) -> float:
        data = self._request("GET", "/droplets")
        total = 0.0
        for d in data.get("droplets", []):
            size = d.get("size", {}).get("slug", "s-1vcpu-2gb")
            plan = next((p for p in DO_PLANS if p.id == size), DO_PLANS[0])
            total += plan.monthly_cost_usd
        return total
