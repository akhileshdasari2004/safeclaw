from app.config import get_settings
from app.providers.base import CloudProviderBase
from app.providers.digitalocean import DigitalOceanProvider
from app.providers.hetzner import HetznerProvider
from app.providers.resilient import ResilientCloudProvider


def get_provider(name: str, *, resilient: bool = True) -> CloudProviderBase:
    settings = get_settings()
    if name == "hetzner":
        if not settings.hetzner_api_token:
            raise ValueError("HETZNER_API_TOKEN not configured")
        inner: CloudProviderBase = HetznerProvider(settings.hetzner_api_token)
    elif name == "digitalocean":
        if not settings.digitalocean_api_token:
            raise ValueError("DIGITALOCEAN_API_TOKEN not configured")
        inner = DigitalOceanProvider(settings.digitalocean_api_token)
    else:
        raise ValueError(f"Unknown provider: {name}")
    return ResilientCloudProvider(inner) if resilient else inner
