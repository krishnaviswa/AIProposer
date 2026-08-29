"""Storage port. Wave 3 only has the local-disk impl; PDFs are stubbed and the
real renderer + signed URLs are Wave 4. S3/Supabase Storage is roadmap."""

from __future__ import annotations

from app.config import get_settings
from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider


def validate_startup_config() -> None:
    name = get_settings().storage_provider
    if name != "local":
        raise RuntimeError(f"STORAGE_PROVIDER={name!r} is not available in this build (Wave 4).")


def get_storage_provider() -> StorageProvider:
    validate_startup_config()
    return LocalStorageProvider()


__all__ = ["StorageProvider", "get_storage_provider", "validate_startup_config"]
