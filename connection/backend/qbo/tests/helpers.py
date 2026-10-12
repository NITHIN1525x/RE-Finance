"""Shared fixtures. All Intuit/QuickBooks HTTP traffic is faked at the `requests` layer, so the real
token, refresh, revoke and sandbox-guard code paths run. Fake token values are generated at runtime
(random, never real, and never literals the secret scanner would flag)."""
import secrets
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from qbo import tokens
from qbo.models import Client, QBOConnection


def fake_refresh_token():
    return "AB11" + secrets.token_hex(23)


def fake_access_token():
    return "eyJ" + secrets.token_urlsafe(30) + "." + secrets.token_urlsafe(80) + "." + secrets.token_urlsafe(30)


def fake_realm():
    return str(9130000000000000000 + secrets.randbelow(10 ** 15))


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code, self._payload = status_code, payload or {}

    def json(self):
        return self._payload


class FakeIntuit:
    """Programmable stand-in for Intuit's token, revoke and sandbox accounting endpoints."""

    def __init__(self):
        self.calls = []                 # (method, url) tuples, never bodies
        self.refresh_status = 200
        self.refresh_error = None
        self.rotate = True
        self.revoke_status = 200
        self.api_status = {}            # path fragment -> status code
        self.company_name = "Sandbox Company_US_1"
        self.issued_refresh_tokens = []
        self.revoked_tokens = []
        self.refresh_tokens_used = []

    def token_payload(self, refresh_token=None):
        rt = refresh_token or fake_refresh_token()
        self.issued_refresh_tokens.append(rt)
        return {"access_token": fake_access_token(), "refresh_token": rt, "expires_in": 3600,
                "x_refresh_token_expires_in": 8726400, "token_type": "bearer"}

    def post(self, url, data=None, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url))
        if url.endswith("/tokens/bearer"):
            if data["grant_type"] == "authorization_code":
                return FakeResponse(200, self.token_payload())
            self.refresh_tokens_used.append(data["refresh_token"])
            if self.refresh_status != 200:
                return FakeResponse(self.refresh_status, {"error": self.refresh_error or "server_error"})
            return FakeResponse(200, self.token_payload(None if self.rotate else data["refresh_token"]))
        if url.endswith("/tokens/revoke"):
            self.revoked_tokens.append(json["token"])
            return FakeResponse(self.revoke_status)
        raise AssertionError(f"unexpected POST {url}")

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url))
        for fragment, status in self.api_status.items():
            if fragment in url:
                return FakeResponse(status, {"Fault": {"Error": [{"Message": "denied"}]}})
        if "/companyinfo/" in url:
            return FakeResponse(200, {"CompanyInfo": {"CompanyName": self.company_name, "Country": "US"}})
        if "/reports/ProfitAndLoss" in url:
            return FakeResponse(200, {
                "Header": {"StartPeriod": params["start_date"], "EndPeriod": params["end_date"], "Currency": "USD",
                           "ReportBasis": "Accrual"},
                "Rows": {"Row": [
                    {"type": "Section", "group": "Income", "Summary": {"ColData": [{"value": "Total Income"}, {"value": "1000.5"}]}},
                    {"type": "Section", "group": "Expenses", "Summary": {"ColData": [{"value": "Total Expenses"}, {"value": "400"}]}},
                    {"type": "Section", "group": "NetIncome", "Summary": {"ColData": [{"value": "Net Income"}, {"value": "600.5"}]}},
                ]}})
        raise AssertionError(f"unexpected GET {url}")

    def urls(self, method=None):
        return [u for m, u in self.calls if method is None or m == method]


class QboTestCase(TestCase):
    """Fresh temp MCP token store and a patched `requests` for every test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qbo-store-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        override = override_settings(MCP_TOKEN_STORE_PATH=self.tmp / "mcp-server.env")
        override.enable()
        self.addCleanup(override.disable)
        self.intuit = FakeIntuit()
        for name in ("post", "get"):
            patcher = mock.patch(f"qbo.intuit.requests.{name}", side_effect=getattr(self.intuit, name))
            patcher.start()
            self.addCleanup(patcher.stop)
        tokens._locks.clear()

    # --- builders ---------------------------------------------------------------------------
    def make_user(self, username):
        return get_user_model().objects.create_user(username=username, password="unused-in-tests-123")

    def make_client(self, slug, *members):
        client = Client.objects.create(name=slug.replace("-", " ").title(), slug=slug)
        client.members.add(*members)
        return client

    def make_connection(self, client, realm=None, refresh_token=None, access_token=None,
                        access_valid=True, owner=QBOConnection.Owner.DJANGO):
        conn = QBOConnection(client=client, realm_id=realm or fake_realm(), token_owner=owner)
        tokens.store_token_set(conn, {
            "access_token": access_token or fake_access_token(),
            "refresh_token": refresh_token or fake_refresh_token(),
            "access_expires_at": timezone.now() + (timedelta(minutes=50) if access_valid else timedelta(minutes=-1)),
            "refresh_expires_at": timezone.now() + timedelta(days=100),
        })
        conn.save()
        return conn
