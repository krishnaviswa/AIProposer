"""Local-disk storage for Compose / dev. Not used for real PDF delivery in
Wave 3 — the PDF endpoint is a stub."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class LocalStorageProvider:
    name = "local"

    def __init__(self) -> None:
        self.root = Path(get_settings().storage_local_path)
        self.root.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    async def signed_url(self, key: str, ttl_seconds: int = 300) -> str:
        # Compose serves this path via StaticFiles; no real signing locally.
        return f"/uploads/{key}"
