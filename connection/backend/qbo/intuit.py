"""Thin Intuit OAuth 2.0 + QuickBooks Accounting API client (plain `requests`).

OAuth endpoints come from Intuit's discovery documents (verified 2026-10-12). They are the SAME for
sandbox and production, so the sandbox guard cannot rely on them. It is enforced on the accounting
API host instead: every API URL must be on SANDBOX_API_HOST, or ProductionAccessRefused is raised
before any network call.
"""
import base64
import logging
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

log = logging.getLogger("qbo")

AUTHORIZATION_ENDPOINT = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
REVOCATION_ENDPOINT = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
ACCOUNTING_SCOPE = "com.intuit.quickbooks.accounting"   # least privilege: no OpenID/profile/payments scopes

SANDBOX_API_HOST = "sandbox-quickbooks.api.intuit.com"
SANDBOX_API_BASE = f"https://{SANDBOX_API_HOST}"
MINOR_VERSION = "75"
TIMEOUT = 15  # seconds


class ProductionAccessRefused(RuntimeError):
    """Raised when anything tries to call a non-sandbox QuickBooks API host."""


class IntuitError(Exception):
    """Safe-to-display error. `kind` drives connection status; messages never contain token values."""

    def __init__(self, kind, message, status_code=None):
        super().__init__(message)
        self.kind = kind            # "invalid_grant" | "invalid_client" | "transient" | "api"
        self.status_code = status_code


def assert_sandbox_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != SANDBOX_API_HOST:
        raise ProductionAccessRefused(f"Refusing QuickBooks API call to non-sandbox host {parsed.hostname!r}")


def credentials_configured():
    return bool(settings.QUICKBOOKS_CLIENT_ID and settings.QUICKBOOKS_CLIENT_SECRET)


def authorization_url(state):
    query = urlencode({
        "client_id": settings.QUICKBOOKS_CLIENT_ID,
        "response_type": "code",
        "scope": ACCOUNTING_SCOPE,
        "redirect_uri": settings.QUICKBOOKS_REDIRECT_URI,
        "state": state,
    })
    return f"{AUTHORIZATION_ENDPOINT}?{query}"


@sensitive_variables("auth")
def _basic_auth_header():
    auth = f"{settings.QUICKBOOKS_CLIENT_ID}:{settings.QUICKBOOKS_CLIENT_SECRET}".encode()
    return {"Authorization": "Basic " + base64.b64encode(auth).decode(), "Accept": "application/json"}


def _post_token_endpoint(data):
    try:
        resp = requests.post(TOKEN_ENDPOINT, data=data, headers=_basic_auth_header(), timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise IntuitError("transient", f"Could not reach Intuit token endpoint ({exc.__class__.__name__})")
    if resp.status_code == 200:
        return resp.json()
    # Only the OAuth error *code* is surfaced (a fixed vocabulary), never the response body.
    code = ""
    try:
        code = str(resp.json().get("error", ""))[:40]
    except ValueError:
        pass
    if resp.status_code == 400 and code == "invalid_grant":
        raise IntuitError("invalid_grant", "Intuit rejected the grant (expired, revoked or already used)", 400)
    if resp.status_code == 401 or code == "invalid_client":
        raise IntuitError("invalid_client", "Intuit rejected the app credentials (check client ID/secret)", resp.status_code)
    if resp.status_code >= 500 or resp.status_code == 429:
        raise IntuitError("transient", f"Intuit token endpoint unavailable (HTTP {resp.status_code})", resp.status_code)
    raise IntuitError("api", f"Token request failed (HTTP {resp.status_code}{', ' + code if code else ''})", resp.status_code)


def _token_set(payload):
    """Normalise a token response; expiries come from Intuit's own fields, not assumptions."""
    now = timezone.now()
    return {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "access_expires_at": now + timedelta(seconds=int(payload.get("expires_in", 3600))),
        "refresh_expires_at": (now + timedelta(seconds=int(payload["x_refresh_token_expires_in"])))
        if payload.get("x_refresh_token_expires_in") else None,
    }


@sensitive_variables("code", "payload")
def exchange_code(code):
    payload = _post_token_endpoint({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.QUICKBOOKS_REDIRECT_URI,
    })
    return _token_set(payload)


@sensitive_variables("refresh_token", "payload")
def refresh(refresh_token):
    payload = _post_token_endpoint({"grant_type": "refresh_token", "refresh_token": refresh_token})
    return _token_set(payload)


@sensitive_variables("token")
def revoke(token):
    """Revoking the refresh token revokes the whole grant at Intuit. Returns True on success."""
    try:
        resp = requests.post(REVOCATION_ENDPOINT, json={"token": token}, headers=_basic_auth_header(), timeout=TIMEOUT)
    except requests.RequestException:
        return False
    return resp.status_code == 200


@sensitive_variables("access_token")
def api_get(realm_id, path, access_token, params=None):
    """GET {SANDBOX_API_BASE}/v3/company/{realm_id}/{path}. The realm always comes from the stored
    connection, never from the request."""
    if not str(realm_id).isdigit():
        raise IntuitError("api", "Stored realm ID is malformed")
    url = f"{SANDBOX_API_BASE}/v3/company/{realm_id}/{path}"
    assert_sandbox_url(url)   # hard guard, evaluated on the final URL
    query = {"minorversion": MINOR_VERSION, **(params or {})}
    try:
        resp = requests.get(url, params=query, timeout=TIMEOUT, headers={
            "Authorization": f"Bearer {access_token}", "Accept": "application/json"})
    except requests.RequestException as exc:
        raise IntuitError("transient", f"Could not reach QuickBooks sandbox API ({exc.__class__.__name__})")
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code == 401:
        raise IntuitError("unauthorized", "QuickBooks rejected the access token", 401)
    if resp.status_code == 403:
        raise IntuitError("api", "QuickBooks refused access to this company (is it a sandbox company?)", 403)
    if resp.status_code >= 500 or resp.status_code == 429:
        raise IntuitError("transient", f"QuickBooks sandbox API unavailable (HTTP {resp.status_code})", resp.status_code)
    raise IntuitError("api", f"QuickBooks API request failed (HTTP {resp.status_code})", resp.status_code)
