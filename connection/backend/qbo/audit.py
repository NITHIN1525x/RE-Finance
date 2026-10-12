"""Audit trail: who / when / which client / which action / success. Never token values.

`detail` is passed through a scrubber as a second line of defence: callers already only pass fixed
messages, but anything token-shaped is replaced before it is stored.
"""
import getpass
import re

from .models import AuditLog

_TOKEN_SHAPES = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_.-]{10,}"     # JWT/JWE access tokens
    r"|\bAB[0-9A-Za-z]{30,}\b"                          # Intuit refresh tokens / client IDs
    r"|gAAAAA[A-Za-z0-9_=-]{20,}"                       # Fernet ciphertext
    r"|\b[A-Za-z0-9_-]{32,}\b"                          # any other long opaque string
)


def scrub(text):
    return _TOKEN_SHAPES.sub("[redacted]", str(text or ""))[:500]


def actor_for_request(request):
    user = getattr(request, "user", None)
    return user.get_username() if user is not None and user.is_authenticated else "anonymous"


def cli_actor():
    try:
        return f"cli:{getpass.getuser()}"
    except Exception:  # noqa: BLE001 - getuser can fail in odd environments; the audit row must still be written
        return "cli:unknown"


def record(action, actor, success, client=None, detail=""):
    return AuditLog.objects.create(
        client=client,
        client_slug=client.slug if client else "",
        action=action,
        actor=actor,
        success=success,
        detail=scrub(detail),
    )
