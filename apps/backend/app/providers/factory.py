from app.config import get_settings
from app.providers.base import CloudProviderBase
from app.providers.digitalocean import DigitalOceanProvider
from app.providers.hetzner import HetznerProvider


def get_provider(name: str) -> CloudProviderBase:
    settings = get_settings()
    if name == "hetzner":
        if not settings.hetzner_api_token:
            raise ValueError("HETZNER_API_TOKEN not configured")
        return HetznerProvider(settings.hetzner_api_token)
    if name == "digitalocean":
        if not settings.digitalocean_api_token:
            raise ValueError("DIGITALOCEAN_API_TOKEN not configured")
        return DigitalOceanProvider(settings.digitalocean_api_token)
    raise ValueError(f"Unknown provider: {name}")
