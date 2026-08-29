"""Email provider contract (verify links, receipts). Not exercised in Wave 3."""

from __future__ import annotations

from typing import Protocol


class EmailProvider(Protocol):
    name: str

    async def send(self, *, to: str, subject: str, body: str) -> None: ...
