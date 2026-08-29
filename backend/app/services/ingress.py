"""Pre-model ingress guards (mvp-spec.md §16). The brief is untrusted input.

Char caps are enforced by the Pydantic request schema; this adds the
instruction-like-pattern scrub before the text reaches the provider.
"""

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    re.compile(r"ignore (all |any |the )?(previous|above|prior) (instructions|prompt)", re.I),
    re.compile(r"disregard (the )?(system|previous) (prompt|instructions|message)", re.I),
    re.compile(r"(reveal|print|show|output|repeat) (me )?(your |the )?(system )?(prompt|instructions)", re.I),
    re.compile(r"you are now (a|an|in) ", re.I),
    re.compile(r"</?(system|assistant|user)>", re.I),
]


def scrub(text: str) -> tuple[str, list[str]]:
    """Return (cleaned_text, flags). Matched spans are replaced with [removed]."""
    flags: list[str] = []
    cleaned = text
    for pat in _INJECTION_PATTERNS:
        if pat.search(cleaned):
            flags.append(pat.pattern)
            cleaned = pat.sub("[removed]", cleaned)
    return cleaned, flags
