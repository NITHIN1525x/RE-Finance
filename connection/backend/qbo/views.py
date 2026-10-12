"""HTTP API for the Connection Console.

Isolation rules applied everywhere:
- the client is always resolved through qbo.access (membership-scoped; 404 otherwise);
- the realm ID is always read from the stored connection, never accepted from the request;
- responses carry no token values and at most the first four characters of the realm ID.
"""
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.debug import sensitive_variables
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import audit, intuit, reports, tokens
from .access import audit_for, clients_for, get_client_for
from .models import QBOConnection

log = logging.getLogger("qbo")

PENDING_KEY = "qbo_oauth_pending"
STATE_TTL = timedelta(minutes=10)
# The callback only ever sends these fixed reason codes back to the browser (no reflected text).
REASONS = {"invalid_state", "state_expired", "unknown_client", "denied", "missing_params", "not_configured",
           "checked_out", "realm_in_use", "different_company", "token_exchange_failed", "not_sandbox_company",
           "verify_failed"}


def _frontend(status, client=None, reason=None):
    params = {"qbo": status}
    if client:
        params["client"] = client
    if reason:
        params["reason"] = reason if reason in REASONS else "error"
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}/?{urlencode(params)}")


def client_summary(client):
    conn = getattr(client, "connection", None)
    data = {"name": client.name, "slug": client.slug, "environment": "sandbox", "connected": False}
    if conn is None:
        data["status"] = "not_connected"
        return data
    now = timezone.now()
    data.update({
        "connected": conn.status != QBOConnection.Status.DISCONNECTED and bool(conn.encrypted_refresh_token),
        "status": conn.status,
        "realm_hint": conn.realm_hint,
        "token_owner": conn.token_owner,
        "checked_out_at": conn.checked_out_at,
        "last_refreshed_at": conn.last_refreshed_at,
        "access_token_expires_at": conn.access_token_expires_at,
        "access_token_valid": bool(conn.access_token_expires_at and conn.access_token_expires_at > now),
        "refresh_token_expires_at": conn.refresh_token_expires_at,
        "refresh_token_days_left": (conn.refresh_token_expires_at - now).days if conn.refresh_token_expires_at else None,
    })
    return data


# --- session / identity -------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def me(request):
    """Also sets the csrftoken cookie the SPA echoes back in X-CSRFToken."""
    if not request.user or not request.user.is_authenticated:
        return Response({"authenticated": False, "login_url": settings.LOGIN_URL})
    return Response({"authenticated": True, "username": request.user.get_username(),
                     "credentials_configured": intuit.credentials_configured()})


# --- read endpoints -------------------------------------------------------------------------

@api_view(["GET"])
def client_list(request):
    clients = clients_for(request.user).select_related("connection").order_by("name")
    return Response({"clients": [client_summary(c) for c in clients]})


@api_view(["GET"])
def audit_list(request):
    qs = audit_for(request.user)
    slug = request.query_params.get("client")
    if slug:
        qs = qs.filter(client=get_client_for(request.user, slug))
    try:
        limit = max(1, min(int(request.query_params.get("limit", 25)), 100))
    except ValueError:
        limit = 25
    rows = qs.select_related("client")[:limit]
    return Response({"entries": [
        {"timestamp": r.timestamp, "client": r.client_slug, "action": r.action, "actor": r.actor,
         "success": r.success, "detail": r.detail} for r in rows]})


# --- OAuth ----------------------------------------------------------------------------------

@require_GET
@login_required
def oauth_connect(request):
    slug = request.GET.get("client", "")
    actor = audit.actor_for_request(request)
    try:
        client = get_client_for(request.user, slug)
    except Http404:
        return _frontend("error", reason="unknown_client")
    if not intuit.credentials_configured():
        audit.record("oauth_start", actor, False, client, "Intuit client ID/secret not configured")
        return _frontend("error", client.slug, "not_configured")
    conn = getattr(client, "connection", None)
    if conn and conn.token_owner == QBOConnection.Owner.MCP:
        # Re-authorising while the MCP server holds the live token would create a second owner.
        audit.record("oauth_start", actor, False, client, "Refused: connection is checked out to the MCP server")
        return _frontend("error", client.slug, "checked_out")
    state = secrets.token_urlsafe(32)
    request.session[PENDING_KEY] = {"state": state, "client": client.slug, "user_id": request.user.pk,
                                    "issued_at": timezone.now().isoformat()}
    audit.record("oauth_start", actor, True, client, "Redirected to Intuit authorization (accounting scope)")
    return HttpResponseRedirect(intuit.authorization_url(state))


@require_GET
@sensitive_variables("code", "token_set")
def oauth_callback(request):
    actor = audit.actor_for_request(request)
    pending = request.session.pop(PENDING_KEY, None)      # one-time: a state can never be replayed
    state = request.GET.get("state", "")
    if (not pending or not state or not secrets.compare_digest(state, pending.get("state", ""))
            or not request.user.is_authenticated or pending.get("user_id") != request.user.pk):
        audit.record("oauth_callback", actor, False, None, "Rejected: missing, mismatched or replayed OAuth state")
        return _frontend("error", reason="invalid_state")
    if timezone.now() - datetime.fromisoformat(pending["issued_at"]) > STATE_TTL:
        audit.record("oauth_callback", actor, False, None, "Rejected: OAuth state expired")
        return _frontend("error", reason="state_expired")
    try:
        client = get_client_for(request.user, pending["client"])
    except Http404:
        return _frontend("error", reason="unknown_client")

    if request.GET.get("error"):
        audit.record("oauth_callback", actor, False, client, "Authorization not granted at Intuit")
        return _frontend("error", client.slug, "denied")
    code, realm_id = request.GET.get("code", ""), request.GET.get("realmId", "")
    if not code or not realm_id.isdigit():
        audit.record("oauth_callback", actor, False, client, "Callback missing code or realmId")
        return _frontend("error", client.slug, "missing_params")

    existing = getattr(client, "connection", None)
    if existing and existing.token_owner == QBOConnection.Owner.MCP:
        audit.record("oauth_callback", actor, False, client, "Refused: connection is checked out to the MCP server")
        return _frontend("error", client.slug, "checked_out")
    active = Q(realm_id=realm_id) & ~Q(status=QBOConnection.Status.DISCONNECTED)
    if QBOConnection.objects.filter(active).exclude(client=client).exists():
        audit.record("oauth_callback", actor, False, client, "Refused: company already connected to another client")
        return _frontend("error", client.slug, "realm_in_use")
    if existing and existing.status != QBOConnection.Status.DISCONNECTED and existing.realm_id != realm_id:
        audit.record("oauth_callback", actor, False, client, "Refused: a different company is connected; disconnect first")
        return _frontend("error", client.slug, "different_company")

    try:
        token_set = intuit.exchange_code(code)
    except intuit.IntuitError as exc:
        audit.record("oauth_callback", actor, False, client, f"Token exchange failed: {exc}")
        return _frontend("error", client.slug, "token_exchange_failed")

    # Sandbox guard, part 3: the company must answer on the sandbox API host before we keep anything.
    try:
        intuit.api_get(realm_id, f"companyinfo/{realm_id}", token_set["access_token"])
    except (intuit.IntuitError, intuit.ProductionAccessRefused) as exc:
        intuit.revoke(token_set["refresh_token"])
        audit.record("oauth_callback", actor, False, client, f"Sandbox verification failed, grant revoked: {exc}")
        reason = "not_sandbox_company" if getattr(exc, "status_code", None) in (401, 403) else "verify_failed"
        return _frontend("error", client.slug, reason)

    conn = existing or QBOConnection(client=client)
    conn.realm_id = realm_id
    conn.token_owner = QBOConnection.Owner.DJANGO
    conn.checked_out_at = None
    tokens.store_token_set(conn, token_set)
    conn.save()
    audit.record("oauth_callback", actor, True, client,
                 f"Connected sandbox company {conn.realm_hint}; verified on {intuit.SANDBOX_API_HOST}")
    return _frontend("connected", client.slug)


# --- actions --------------------------------------------------------------------------------

def _connection_or_409(client):
    conn = getattr(client, "connection", None)
    if conn is None or conn.status == QBOConnection.Status.DISCONNECTED:
        return None, Response({"error": "not_connected", "message": "This client is not connected to QuickBooks."}, status=409)
    return conn, None


@api_view(["POST"])
@sensitive_variables("access_token")
def test_connection(request, slug):
    client = get_client_for(request.user, slug)
    actor = audit.actor_for_request(request)
    conn, error = _connection_or_409(client)
    if error:
        return error
    try:
        access_token = tokens.get_access_token(conn, actor)
        try:
            company = intuit.api_get(conn.realm_id, f"companyinfo/{conn.realm_id}", access_token)
        except intuit.IntuitError as exc:
            if exc.kind != "unauthorized" or conn.token_owner != QBOConnection.Owner.DJANGO:
                raise
            access_token = tokens.locked_refresh(conn, actor, force=True)   # token revoked early: retry once
            company = intuit.api_get(conn.realm_id, f"companyinfo/{conn.realm_id}", access_token)
        start, end = reports.last_12_months()
        pnl = intuit.api_get(conn.realm_id, "reports/ProfitAndLoss", access_token,
                             {"start_date": start.isoformat(), "end_date": end.isoformat()})
    except tokens.TokenUnavailable as exc:
        audit.record("test_connection", actor, False, client, str(exc))
        return Response({"error": exc.code, "message": str(exc)}, status=exc.http_status)
    except intuit.IntuitError as exc:
        audit.record("test_connection", actor, False, client, str(exc))
        return Response({"error": exc.kind, "message": str(exc)}, status=502)

    conn.refresh_from_db()
    result = {
        "client": client.slug,
        "realm_hint": conn.realm_hint,
        "environment": "sandbox",
        "api_host": intuit.SANDBOX_API_HOST,
        "company": reports.summarize_company(company),
        "profit_and_loss": reports.summarize_pnl(pnl),
        "connection": client_summary(client),
    }
    audit.record("test_connection", actor, True, client, "CompanyInfo and Profit & Loss retrieved from sandbox")
    return Response(result)


@api_view(["POST"])
def disconnect(request, slug):
    client = get_client_for(request.user, slug)
    conn, error = _connection_or_409(client)
    if error:
        return error
    revoked = tokens.disconnect(conn, audit.actor_for_request(request))
    return Response({"disconnected": True, "revoked_at_intuit": revoked, "connection": client_summary(client)})
