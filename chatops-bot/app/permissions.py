"""3-tier permission system for InsightHub ChatOps Bot."""
import logging
import secrets
import time
from enum import Enum

logger = logging.getLogger("chatops-bot.permissions")

TOKEN_TTL_SECONDS = 60

_token_store: dict[str, tuple[str, float]] = {}


class PermissionTier(str, Enum):
    READ = "read"           # auto-allowed: queries, status checks
    WRITE = "write"         # ask-confirm + token: scale, restart
    DESTRUCTIVE = "destructive"  # always deny: delete, drop


# Keyword classification
_DESTRUCTIVE_KEYWORDS = ("delete", "drop", "terminate", "destroy", "purge", "wipe")
_WRITE_KEYWORDS = ("scale", "restart", "stop", "start", "update", "redeploy", "rollback", "patch")


def classify_intent(question: str) -> PermissionTier:
    """Classify question into a permission tier."""
    q = question.lower()
    if any(kw in q for kw in _DESTRUCTIVE_KEYWORDS):
        return PermissionTier.DESTRUCTIVE
    if any(kw in q for kw in _WRITE_KEYWORDS):
        return PermissionTier.WRITE
    return PermissionTier.READ


def issue_confirmation_token(user_id: str) -> str:
    """Issue a one-time confirmation token (TTL = TOKEN_TTL_SECONDS)."""
    token = secrets.token_urlsafe(16)
    _token_store[token] = (user_id, time.monotonic() + TOKEN_TTL_SECONDS)
    logger.info("Issued confirmation token for user %s", user_id)
    return token


def validate_confirmation_token(token: str, user_id: str) -> bool:
    """Validate and consume a confirmation token. Returns True if valid."""
    entry = _token_store.get(token)
    if not entry:
        return False
    stored_user, expires_at = entry
    if stored_user != user_id or time.monotonic() > expires_at:
        _token_store.pop(token, None)
        return False
    _token_store.pop(token, None)
    return True
