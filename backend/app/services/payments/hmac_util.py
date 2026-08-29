"""HMAC-SHA256 webhook signing/verification. Shared by the mock provider now
and the real Razorpay provider in Wave 4."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def sign_body(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def signatures_match(secret: str, body: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign_body(secret, body), signature or "")


def loads_json(body: bytes) -> dict[str, Any]:
    return json.loads(body.decode("utf-8"))
