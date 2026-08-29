"""Live Claude adapter (ADR-002).

- Structured output via `client.messages.parse(output_format=...)` — the schema
  has NO amount field, so the model literally cannot return money (mvp-spec.md §9, §16).
- System prompt is cached (`cache_control: ephemeral`).
- No streaming (mvp-spec.md §4). `max_tokens` capped at `AI_MAX_TOKENS` (2000).
- Any refusal / truncation / SDK error becomes AIGenerationError → 502, 0 quota.
"""

from __future__ import annotations

from decimal import Decimal

import anthropic
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.ai.base import (
    AIGenerationError,
    AIProvider,
    ProposalCopyResult,
    ProposalPromptInput,
    TokenUsage,
)
from app.services.ai.prompts import SYSTEM_PROMPT, build_user_payload

# $ / 1M tokens, for the loaded-cost estimate we store on every call. Not billing.
_MODEL_RATES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
}


class _TimelineItem(BaseModel):
    label: str
    detail: str


class _PricingJustification(BaseModel):
    label: str
    justification: str  # NOTE: no amount / price / currency field, by design.


class _ProposalCopySchema(BaseModel):
    executive_summary: str = Field(min_length=1)
    scope_of_work: list[str] = Field(min_length=1)
    timeline: list[_TimelineItem]
    pricing: list[_PricingJustification]
    terms: list[str]
    followup_email: str = Field(min_length=1)


def _estimate_cost_usd(model: str, usage: TokenUsage) -> Decimal:
    rate_in, rate_out = _MODEL_RATES.get(model, (2.0, 10.0))
    cents = usage.prompt_tokens * rate_in + usage.completion_tokens * rate_out
    return (Decimal(cents) / Decimal(1_000_000)).quantize(Decimal("0.000001"))


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise AIGenerationError("ANTHROPIC_API_KEY is not configured")
        self._model = settings.ai_model
        self._max_tokens = settings.ai_max_tokens
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,  # mvp-spec.md §16: no retry storm
        )

    async def generate_proposal_copy(self, payload: ProposalPromptInput) -> ProposalCopyResult:
        try:
            response = await self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=[
                    {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
                ],
                messages=[{"role": "user", "content": build_user_payload(payload)}],
                output_format=_ProposalCopySchema,
            )
        except anthropic.APIError as exc:
            raise AIGenerationError(f"claude call failed: {exc}") from exc

        if response.stop_reason == "refusal":
            raise AIGenerationError("model refused the request")
        if response.stop_reason == "max_tokens":
            raise AIGenerationError("model output was truncated (max_tokens)")

        parsed = response.parsed_output
        if parsed is None:
            raise AIGenerationError("model did not return a valid structured object")

        u = response.usage
        usage = TokenUsage(
            prompt_tokens=(u.input_tokens or 0)
            + (getattr(u, "cache_read_input_tokens", 0) or 0)
            + (getattr(u, "cache_creation_input_tokens", 0) or 0),
            completion_tokens=u.output_tokens or 0,
        )

        return ProposalCopyResult(
            executive_summary=parsed.executive_summary,
            scope_of_work=list(parsed.scope_of_work),
            timeline=[{"label": t.label, "detail": t.detail} for t in parsed.timeline],
            terms=list(parsed.terms),
            followup_email=parsed.followup_email,
            pricing_justifications={p.label: p.justification for p in parsed.pricing},
            usage=usage,
            estimated_cost_usd=_estimate_cost_usd(self._model, usage),
            provider="anthropic",
            raw={"model": self._model, "stop_reason": response.stop_reason},
        )
