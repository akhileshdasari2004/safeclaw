from app.providers.hetzner import HETZNER_PLANS, HETZNER_REGIONS, HetznerProvider
from app.providers.digitalocean import DO_PLANS, DO_REGIONS, DigitalOceanProvider


def test_hetzner_catalog():
    p = HetznerProvider.__new__(HetznerProvider)
    assert len(HETZNER_REGIONS) >= 3
    assert len(HETZNER_PLANS) >= 2


def test_digitalocean_catalog():
    assert len(DO_REGIONS) >= 3
    assert len(DO_PLANS) >= 2
