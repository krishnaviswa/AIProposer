"""Storage provider contract."""

from __future__ import annotations

from typing import Protocol


class StorageProvider(Protocol):
    name: str

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store bytes, return the storage key."""

    async def signed_url(self, key: str, ttl_seconds: int = 300) -> str:
        """Return a short-lived URL for the object."""
