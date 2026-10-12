"""Token lifecycle with a single refresh owner per connection (DECISIONS_LOG D-08).

- token_owner == "django": only this module may call Intuit's refresh grant for the connection.
- token_owner == "mcp": the official MCP server holds the live refresh token (export_mcp_env).
  Django NEVER refreshes; it may only use a still-valid cached access token.

Concurrency inside Django: a per-connection lock plus select_for_update (a real row lock on PostgreSQL;
SQLite serialises writes anyway), with a re-check after acquiring the lock, so two simultaneous
requests cannot both spend the same rotating refresh token.
"""
import threading
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from . import audit, intuit, mcp_store
from .crypto import decrypt, encrypt
from .models import QBOConnection

REFRESH_MARGIN = timedelta(minutes=5)
_locks = {}
_locks_guard = threading.Lock()


class TokenUnavailable(Exception):
    """Safe message for the UI. `code` is a short machine-readable reason."""

    def __init__(self, code, message, http_status=409):
        super().__init__(message)
        self.code, self.http_status = code, http_status


def _lock_for(connection_id):
    with _locks_guard:
        return _locks.setdefault(connection_id, threading.RLock())   # re-entrant: checkout refreshes under the same lock


def _access_token_valid(conn):
    return bool(conn.encrypted_access_token and conn.access_token_expires_at
                and conn.access_token_expires_at > timezone.now() + REFRESH_MARGIN)


@sensitive_variables("tokens")
def store_token_set(conn, tokens):
    conn.encrypted_access_token = encrypt(tokens["access_token"])
    conn.encrypted_refresh_token = encrypt(tokens["refresh_token"])
    conn.access_token_expires_at = tokens["access_expires_at"]
    if tokens["refresh_expires_at"]:
        conn.refresh_token_expires_at = tokens["refresh_expires_at"]
    conn.last_refreshed_at = timezone.now()
    conn.status = QBOConnection.Status.CONNECTED


@sensitive_variables("refresh_token", "tokens")
def refresh_now(conn, actor, reason="refresh"):
    """Spend the refresh token once. Caller must hold the lock and be the owner. Returns the new access token."""
    if conn.token_owner != QBOConnection.Owner.DJANGO:
        raise TokenUnavailable("checked_out", "Connection is checked out to the MCP server; Django will not refresh it.")
    refresh_token = decrypt(conn.encrypted_refresh_token)
    if not refresh_token:
        raise TokenUnavailable("not_connected", "No refresh token stored. Connect QuickBooks first.")
    try:
        tokens = intuit.refresh(refresh_token)
    except intuit.IntuitError as exc:
        if exc.kind == "invalid_grant":
            conn.status = QBOConnection.Status.REFRESH_REQUIRED
            conn.encrypted_access_token = ""
            conn.save()
            audit.record(reason, actor, False, conn.client, "Refresh token rejected; reconnect required")
            raise TokenUnavailable("refresh_required", "QuickBooks authorization expired or was revoked. Reconnect.")
        if exc.kind == "invalid_client":
            conn.status = QBOConnection.Status.ERROR
            conn.save()
        audit.record(reason, actor, False, conn.client, str(exc))
        raise TokenUnavailable(exc.kind, str(exc), 502)
    rotated = tokens["refresh_token"] != refresh_token
    store_token_set(conn, tokens)
    conn.save()
    audit.record(reason, actor, True, conn.client, "Access token refreshed" + ("; refresh token rotated" if rotated else ""))
    return tokens["access_token"]


def get_access_token(conn, actor):
    """Valid access token for this connection, refreshing only if Django owns it."""
    if conn.status == QBOConnection.Status.DISCONNECTED or not conn.encrypted_refresh_token:
        raise TokenUnavailable("not_connected", "This client is not connected to QuickBooks.")
    if _access_token_valid(conn):
        return decrypt(conn.encrypted_access_token)
    if conn.token_owner == QBOConnection.Owner.MCP:
        raise TokenUnavailable(
            "checked_out",
            "The connection is checked out to the MCP server and the cached access token has expired. "
            "Stop the MCP server and run `manage.py sync_mcp_tokens` to check it back in.")
    return locked_refresh(conn, actor)


def locked_refresh(conn, actor, reason="refresh", force=False):
    """Refresh under the per-connection lock + row lock. A failure's status change and audit row are
    committed (not rolled back) before the error is re-raised."""
    failure = None
    with _lock_for(conn.pk):
        with transaction.atomic():
            locked = QBOConnection.objects.select_for_update().select_related("client").get(pk=conn.pk)
            if not force and _access_token_valid(locked):   # someone refreshed while we waited
                token = decrypt(locked.encrypted_access_token)
            else:
                try:
                    token = refresh_now(locked, actor, reason)
                except TokenUnavailable as exc:
                    failure = exc
    conn.refresh_from_db()
    if failure:
        raise failure
    return token


@sensitive_variables("refresh_token")
def checkout_to_mcp(conn, actor):
    """Hand the live refresh token to the MCP server's token store (export_mcp_env).

    Under the lock: refresh once (fresh token, validates the grant, caches an access token Django can
    still use read-only), write the store, then flip owner to MCP. From here on Django never refreshes.
    """
    other = QBOConnection.objects.filter(token_owner=QBOConnection.Owner.MCP).exclude(pk=conn.pk).select_related("client").first()
    if other:
        raise TokenUnavailable("store_busy", f"Client '{other.client.slug}' is already checked out to the local MCP "
                                             "token store. Check it back in (sync_mcp_tokens) first.")
    if conn.token_owner == QBOConnection.Owner.MCP:
        raise TokenUnavailable("checked_out", "Already checked out to the MCP server.")
    with _lock_for(conn.pk):
        locked_refresh(conn, actor, reason="mcp_checkout_refresh", force=True)
        with transaction.atomic():
            locked = QBOConnection.objects.select_for_update().select_related("client").get(pk=conn.pk)
            refresh_token = decrypt(locked.encrypted_refresh_token)
            mcp_store.write_checked_out(locked.realm_id, refresh_token)
            locked.token_owner = QBOConnection.Owner.MCP
            locked.checked_out_at = timezone.now()
            locked.save()
            audit.record("mcp_checkout", actor, True, locked.client,
                         f"Refresh-token ownership handed to MCP server store ({mcp_store.store_path().name}); read-only flags set")
    conn.refresh_from_db()


@sensitive_variables("store", "returned", "current")
def checkin_from_mcp(conn, actor):
    """Take ownership back from the MCP server (sync_mcp_tokens). Caller must ensure it is stopped.
    Returns True if the MCP server had rotated the refresh token."""
    if conn.token_owner != QBOConnection.Owner.MCP:
        raise TokenUnavailable("not_checked_out", "This connection is not checked out to the MCP server.")
    store = mcp_store.read_store()
    store_realm = store.get("QUICKBOOKS_REALM_ID", "")
    if store_realm and store_realm != conn.realm_id:
        # Never import a token that belongs to a different company into this client (isolation).
        raise TokenUnavailable("realm_mismatch", "The MCP token store belongs to a different company; refusing to import it.")
    rotated = False
    with _lock_for(conn.pk), transaction.atomic():
        locked = QBOConnection.objects.select_for_update().select_related("client").get(pk=conn.pk)
        returned = store.get("QUICKBOOKS_REFRESH_TOKEN", "")
        current = decrypt(locked.encrypted_refresh_token)
        if returned and returned != current:
            locked.encrypted_refresh_token = encrypt(returned)
            rotated = True
        mcp_store.write_placeholder()
        locked.token_owner = QBOConnection.Owner.DJANGO
        locked.checked_out_at = None
        locked.save()
        detail = ("Ownership returned to Django; MCP had rotated the refresh token (stored encrypted)" if rotated
                  else "Ownership returned to Django; refresh token unchanged" if returned
                  else "Ownership returned to Django; store held no token (kept existing encrypted token)")
        audit.record("mcp_checkin", actor, True, locked.client, detail)
    conn.refresh_from_db()
    return rotated


@sensitive_variables("token", "store", "latest")
def disconnect(conn, actor):
    """Revoke at Intuit (best effort) and always wipe local token material. Returns revoked: bool."""
    token = decrypt(conn.encrypted_refresh_token)
    if conn.token_owner == QBOConnection.Owner.MCP:
        # The MCP server may have rotated the token; the store file holds the latest one.
        store = mcp_store.read_store()
        if store.get("QUICKBOOKS_REALM_ID") == conn.realm_id and store.get("QUICKBOOKS_REFRESH_TOKEN"):
            token = store["QUICKBOOKS_REFRESH_TOKEN"]
        mcp_store.write_placeholder()
    revoked = intuit.revoke(token) if token else False
    conn.encrypted_refresh_token = ""
    conn.encrypted_access_token = ""
    conn.access_token_expires_at = None
    conn.refresh_token_expires_at = None
    conn.status = QBOConnection.Status.DISCONNECTED
    conn.token_owner = QBOConnection.Owner.DJANGO
    conn.checked_out_at = None
    conn.save()
    # success reflects the revoke: local data is always wiped, but an unrevoked grant needs follow-up.
    audit.record("disconnect", actor, revoked, conn.client,
                 "Local tokens deleted; " + ("grant revoked at Intuit" if revoked else "Intuit revoke FAILED or skipped; revoke manually"))
    return revoked
