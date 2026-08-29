"""AI port. Routers/services call get_ai_provider(), never a concrete class.

- "mock"      — deterministic MockAIProvider (default; the only impl in CI/tests)
- "anthropic" — live Claude adapter (ADR-002), requires ANTHROPIC_API_KEY
"""

from __future__ import annotations

from app.config import get_settings
from app.services.ai.base import AIGenerationError, AIProvider, ProposalCopyResult, TokenUsage
from app.services.ai.mock import MockAIProvider

REGISTERED_PROVIDERS = ("mock", "anthropic")


def validate_startup_config() -> None:
    settings = get_settings()
    name = settings.ai_provider.strip().lower()
    if name not in REGISTERED_PROVIDERS:
        raise RuntimeError(
            f"AI_PROVIDER={name!r} is not registered. Options: {', '.join(REGISTERED_PROVIDERS)}."
        )
    if name == "anthropic" and not settings.anthropic_api_key:
        raise RuntimeError("AI_PROVIDER=anthropic requires ANTHROPIC_API_KEY.")


def get_ai_provider() -> AIProvider:
    name = get_settings().ai_provider.strip().lower()
    if name == "anthropic":
        from app.services.ai.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    return MockAIProvider()


__all__ = [
    "AIGenerationError",
    "AIProvider",
    "ProposalCopyResult",
    "REGISTERED_PROVIDERS",
    "TokenUsage",
    "get_ai_provider",
    "validate_startup_config",
]
