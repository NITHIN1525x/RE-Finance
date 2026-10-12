"""No token values (or client secret, or full realm ID) in API responses, audit rows or logs."""
import io
import logging

from django.conf import settings

from qbo import audit
from qbo.logging_filters import RedactOAuthParams, redact
from qbo.models import AuditLog
from qbo.views import PENDING_KEY

from .helpers import QboTestCase, fake_access_token, fake_realm, fake_refresh_token


class NoSecretsTests(QboTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice")
        self.c = self.make_client("abc-inc-sandbox", self.user)
        self.rt, self.at = fake_refresh_token(), fake_access_token()
        self.conn = self.make_connection(self.c, refresh_token=self.rt, access_token=self.at, access_valid=False)
        self.client.force_login(self.user)
        # Capture everything any logger emits during the test.
        self.log_buffer = io.StringIO()
        self.handler = logging.StreamHandler(self.log_buffer)
        self.handler.setLevel(logging.DEBUG)
        for name in ("", "qbo", "django", "django.request", "django.server", "urllib3"):
            lg = logging.getLogger(name)
            lg.addHandler(self.handler)
            self.addCleanup(lg.removeHandler, self.handler)

    def forbidden(self):
        values = [self.rt, self.at, self.conn.realm_id, settings.QUICKBOOKS_CLIENT_SECRET,
                  self.conn.encrypted_refresh_token, self.conn.encrypted_access_token]
        values += self.intuit.issued_refresh_tokens
        return [v for v in values if v]

    def assert_clean(self, text, where):
        for value in self.forbidden():
            self.assertNotIn(value, text, f"secret-like value leaked in {where}")

    def test_api_responses_contain_no_tokens(self):
        bodies = [
            self.client.get("/api/clients/").content.decode(),
            self.client.post("/api/qbo/abc-inc-sandbox/test").content.decode(),   # forces a refresh + rotation
            self.client.get("/api/audit/").content.decode(),
            self.client.get("/api/me/").content.decode(),
            self.client.post("/api/qbo/abc-inc-sandbox/disconnect").content.decode(),
        ]
        for i, body in enumerate(bodies):
            self.assert_clean(body, f"response #{i}")
        listing = self.client.get("/api/clients/").json()["clients"][0]
        self.assertNotIn("realm_id", listing)

    def test_realm_hint_is_at_most_four_characters(self):
        listing = self.client.get("/api/clients/").json()["clients"][0]
        self.assertEqual(listing["realm_hint"], self.conn.realm_id[:4] + "…")

    def test_audit_rows_and_logs_contain_no_tokens(self):
        self.client.post("/api/qbo/abc-inc-sandbox/test")
        self.client.get("/api/qbo/connect", {"client": "abc-inc-sandbox"})
        state = self.client.session[PENDING_KEY]["state"]
        self.client.get("/api/qbo/callback", {"state": state, "code": "AUTHCODE" + fake_refresh_token(), "realmId": fake_realm()})
        self.client.post("/api/qbo/abc-inc-sandbox/disconnect")
        rows = " ".join(f"{r.action} {r.actor} {r.detail}" for r in AuditLog.objects.all())
        self.assert_clean(rows, "audit log")
        self.assert_clean(self.log_buffer.getvalue(), "log output")

    def test_audit_detail_scrubs_token_shaped_text(self):
        row = audit.record("test", "alice", False, self.c, f"oops {self.rt} and {self.at}")
        self.assertNotIn(self.rt, row.detail)
        self.assertNotIn(self.at, row.detail)
        self.assertIn("[redacted]", row.detail)

    def test_request_log_redacts_oauth_query_parameters(self):
        code, realm = fake_refresh_token(), fake_realm()
        line = f'"GET /api/qbo/callback?code={code}&state=abc123&realmId={realm} HTTP/1.1" 302 0'
        cleaned = redact(line)
        self.assertNotIn(code, cleaned)
        self.assertNotIn(realm, cleaned)
        self.assertNotIn("abc123", cleaned)
        record = logging.LogRecord("django.server", logging.INFO, __file__, 1, "%s", (line,), None)
        RedactOAuthParams().filter(record)
        self.assertNotIn(code, record.getMessage())
