"""Email port. Wave 3 only has the mock (logs, no send). Resend/Postmark is Wave 4."""

from __future__ import annotations

from app.config import get_settings
from app.services.email.base import EmailProvider
from app.services.email.mock import MockEmailProvider

REGISTERED_PROVIDERS = ("mock",)


def validate_startup_config() -> None:
    name = get_settings().email_provider.strip().lower()
    if name not in REGISTERED_PROVIDERS:
        raise RuntimeError(
            f"EMAIL_PROVIDER={name!r} is not available in this build (Wave 4). "
            f"Registered now: {', '.join(REGISTERED_PROVIDERS)}."
        )


def get_email_provider() -> EmailProvider:
    validate_startup_config()
    return MockEmailProvider()


__all__ = ["EmailProvider", "get_email_provider", "validate_startup_config"]
