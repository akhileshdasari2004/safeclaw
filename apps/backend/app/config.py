"""Application configuration with environment validation."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/safeclaw"
    )
    database_url_sync: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/safeclaw"
    )

    jwt_secret: str = Field(
        default="dev-only-change-in-production-min-32-chars!!",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    encryption_key: str = Field(
        default="dev-only-change-in-production-encryption-key!!",
        description="Fernet key or 32-byte secret for encrypting SSH keys at rest",
    )

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_starter: str = ""
    stripe_price_id_pro: str = ""

    stripe_success_url: str = "http://localhost:3000/dashboard?checkout=success"
    stripe_cancel_url: str = "http://localhost:3000/pricing?checkout=cancelled"

    resend_api_key: str = ""
    resend_from_email: str = "SafeClaw <onboarding@resend.dev>"

    hetzner_api_token: str = ""
    digitalocean_api_token: str = ""

    ssh_connect_timeout: int = 30
    ssh_command_timeout: int = 300
    provision_max_retries: int = 3
    provision_poll_interval: int = 10

    rate_limit_per_minute: int = 60
    cors_origins: str = "http://localhost:3000"

    alerts_poll_interval_seconds: int = 3600
    alert_cooldown_hours: int = 24

    openclaw_image: str = "ghcr.io/openclaw/openclaw:latest"
    openclaw_port: int = 18789

    @field_validator("jwt_secret", "encryption_key", mode="before")
    @classmethod
    def strip_secrets(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
