from __future__ import annotations

import os
from dataclasses import dataclass


class SettingsError(ValueError):
    """Raised when required startup settings are invalid."""


@dataclass(frozen=True)
class Settings:
    service_name: str
    app_version: str
    environment: str
    api_prefix: str


def load_settings() -> Settings:
    service_name = os.getenv("SERVICE_NAME", "care-orchestration-api").strip()
    app_version = os.getenv("APP_VERSION", "0.1.0").strip()
    environment = os.getenv("APP_ENV", "dev").strip().lower()
    api_prefix = os.getenv("API_PREFIX", "/api/v1").strip()

    allowed_environments = {"dev", "test", "prod"}
    if environment not in allowed_environments:
        raise SettingsError(
            f"Invalid APP_ENV '{environment}'. Allowed values: {sorted(allowed_environments)}"
        )

    if not service_name:
        raise SettingsError("SERVICE_NAME cannot be empty")

    if not app_version:
        raise SettingsError("APP_VERSION cannot be empty")

    if not api_prefix.startswith("/"):
        raise SettingsError("API_PREFIX must start with '/'")

    return Settings(
        service_name=service_name,
        app_version=app_version,
        environment=environment,
        api_prefix=api_prefix,
    )
