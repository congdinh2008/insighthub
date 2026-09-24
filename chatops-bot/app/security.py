"""Slack HMAC authentication for every HTTP request including URL challenge."""

import hashlib
import hmac
import time
from collections.abc import Mapping


def verify_request(body: bytes, headers: Mapping[str, str], secret: str,
                   now: int | None = None) -> bool:
    if not secret or len(body) > 64 * 1024:
        return False
    normalized = {key.lower(): value for key, value in headers.items()}
    timestamp = normalized.get("x-slack-request-timestamp", "")
    signature = normalized.get("x-slack-signature", "")
    if not timestamp.isascii() or not timestamp.isdecimal() or len(timestamp) > 12:
        return False
    if len(signature) != 67 or not signature.startswith("v0="):
        return False
    if abs((int(time.time()) if now is None else now) - int(timestamp)) > 300:
        return False
    base = b"v0:" + timestamp.encode("ascii") + b":" + body
    expected = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
