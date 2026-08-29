"""AI port. Routers/services call get_ai_provider(), never a concrete class.

Wave 3: the only implementation is MockAIProvider. A real provider is Wave 4 —
AI_PROVIDER != "mock" fails validate_startup_config() at boot on purpose, so a
half-configured deploy can't silently reach for a model that isn't wired.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.ai.base import AIGenerationError, AIProvider, ProposalCopyResult, TokenUsage
from app.services.ai.mock import MockAIProvider

REGISTERED_PROVIDERS = ("mock",)


def validate_startup_config() -> None:
    name = get_settings().ai_provider.strip().lower()
    if name not in REGISTERED_PROVIDERS:
        raise RuntimeError(
            f"AI_PROVIDER={name!r} is not available in this build. Real providers land in Wave 4; "
            f"registered now: {', '.join(REGISTERED_PROVIDERS)}."
        )


def get_ai_provider() -> AIProvider:
    validate_startup_config()
    return MockAIProvider()


__all__ = [
    "AIGenerationError",
    "AIProvider",
    "ProposalCopyResult",
    "TokenUsage",
    "get_ai_provider",
    "validate_startup_config",
]
