"""Mock email provider — records sends in-process, makes no network call."""

from __future__ import annotations

import logging

logger = logging.getLogger("aiproposer.email")


class MockEmailProvider:
    name = "mock"

    #: class-level so tests can assert on what would have been sent
    sent: list[dict[str, str]] = []

    async def send(self, *, to: str, subject: str, body: str) -> None:
        MockEmailProvider.sent.append({"to": to, "subject": subject, "body": body})
        logger.info("mock email -> %s: %s", to, subject)
