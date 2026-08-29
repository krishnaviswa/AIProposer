"""The AI provider contract and its value types.

The model produces COPY ONLY. It is never handed authority over money: the
`pricing` it returns carries a `justification` string and nothing else that the
server keeps — amounts and currency are overwritten by the pricing assembler
(mvp-spec.md §9, §16; docs/ai-touchpoints.md).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


class AIGenerationError(RuntimeError):
    """Raised when the provider cannot produce valid structured copy.

    The generation service turns this into a 502 with zero quota consumed and
    nothing persisted (mvp-spec.md §16: parse fail = no quota).
    """


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ProposalCopyResult:
    executive_summary: str
    scope_of_work: list[str]
    timeline: list[dict[str, str]]
    terms: list[str]
    followup_email: str
    # label -> justification. Amounts live server-side; this is the only pricing
    # field the model contributes.
    pricing_justifications: dict[str, str] = field(default_factory=dict)
    usage: TokenUsage = field(default_factory=TokenUsage)
    estimated_cost_usd: Decimal = Decimal("0")
    provider: str = "unknown"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProposalPromptInput:
    """Everything the provider is allowed to see. No user id, no plan, no money
    the model could echo back as authoritative."""

    service_type: str
    tone: str
    client_name: str
    client_company: str | None
    brief_text: str
    notes: str | None
    # label + currency only — NOT amounts.
    package_labels: list[str]


class AIProvider(abc.ABC):
    name: str = "unknown"

    @abc.abstractmethod
    async def generate_proposal_copy(self, payload: ProposalPromptInput) -> ProposalCopyResult: ...
