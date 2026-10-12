from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.test import override_settings
from django.utils import timezone

from qbo.crypto import decrypt
from qbo.models import AuditLog, QBOConnection
from qbo.views import PENDING_KEY

from .helpers import QboTestCase, fake_realm

FRONTEND = "http://localhost:5173"


class OAuthTests(QboTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice")
        self.client_a = self.make_client("abc-inc-sandbox", self.user)
        self.client.force_login(self.user)

    def start(self, slug="abc-inc-sandbox"):
        resp = self.client.get("/api/qbo/connect", {"client": slug})
        return resp, self.client.session.get(PENDING_KEY)

    def callback(self, **params):
        return self.client.get("/api/qbo/callback", params)

    def assert_frontend(self, resp, status, reason=None):
        self.assertEqual(resp.status_code, 302)
        url = urlparse(resp["Location"])
        self.assertEqual(f"{url.scheme}://{url.netloc}", FRONTEND)
        qs = parse_qs(url.query)
        self.assertEqual(qs["qbo"], [status])
        if reason:
            self.assertEqual(qs["reason"], [reason])

    def token_exchanges(self):
        return [u for u in self.intuit.urls("POST") if u.endswith("/tokens/bearer")]

    # --- connect --------------------------------------------------------------------------
    def test_connect_requires_login(self):
        self.client.logout()
        resp = self.client.get("/api/qbo/connect", {"client": "abc-inc-sandbox"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/api/auth/login/"))

    def test_connect_builds_intuit_url_with_state_and_accounting_scope(self):
        resp, pending = self.start()
        self.assertEqual(resp.status_code, 302)
        url = urlparse(resp["Location"])
        self.assertEqual(url.netloc, "appcenter.intuit.com")
        qs = parse_qs(url.query)
        self.assertEqual(qs["scope"], ["com.intuit.quickbooks.accounting"])
        self.assertEqual(qs["response_type"], ["code"])
        self.assertEqual(qs["redirect_uri"], ["http://localhost:8000/api/qbo/callback"])
        self.assertEqual(qs["state"], [pending["state"]])
        self.assertGreaterEqual(len(pending["state"]), 40)
        self.assertEqual(pending["client"], "abc-inc-sandbox")

    @override_settings(QUICKBOOKS_CLIENT_ID="", QUICKBOOKS_CLIENT_SECRET="")
    def test_connect_without_credentials_fails_safely(self):
        resp, pending = self.start()
        self.assert_frontend(resp, "error", "not_configured")
        self.assertIsNone(pending)

    # --- state validation -----------------------------------------------------------------
    def test_callback_without_pending_state_is_rejected(self):
        self.assert_frontend(self.callback(state="x" * 43, code="c", realmId=fake_realm()), "error", "invalid_state")
        self.assertEqual(self.token_exchanges(), [])

    def test_mismatched_state_is_rejected_and_consumed(self):
        _, pending = self.start()
        self.assert_frontend(self.callback(state="wrong" + pending["state"][5:], code="c", realmId=fake_realm()),
                             "error", "invalid_state")
        # The pending state was consumed: even the correct value no longer works afterwards.
        self.assert_frontend(self.callback(state=pending["state"], code="c", realmId=fake_realm()), "error", "invalid_state")
        self.assertEqual(self.token_exchanges(), [])
        self.assertTrue(AuditLog.objects.filter(action="oauth_callback", success=False).exists())

    def test_missing_state_is_rejected(self):
        self.start()
        self.assert_frontend(self.callback(code="c", realmId=fake_realm()), "error", "invalid_state")
        self.assertEqual(self.token_exchanges(), [])

    def test_replayed_state_is_rejected(self):
        _, pending = self.start()
        realm = fake_realm()
        self.assert_frontend(self.callback(state=pending["state"], code="c1", realmId=realm), "connected")
        self.assert_frontend(self.callback(state=pending["state"], code="c2", realmId=realm), "error", "invalid_state")
        self.assertEqual(len(self.token_exchanges()), 1)

    def test_expired_state_is_rejected(self):
        _, pending = self.start()
        session = self.client.session
        session[PENDING_KEY]["issued_at"] = (timezone.now() - timedelta(minutes=11)).isoformat()
        session.save()
        self.assert_frontend(self.callback(state=pending["state"], code="c", realmId=fake_realm()), "error", "state_expired")
        self.assertEqual(self.token_exchanges(), [])

    def test_state_bound_to_the_user_who_started_the_flow(self):
        _, pending = self.start()
        session = self.client.session
        session[PENDING_KEY]["user_id"] = self.user.pk + 999
        session.save()
        self.assert_frontend(self.callback(state=pending["state"], code="c", realmId=fake_realm()), "error", "invalid_state")
        self.assertEqual(self.token_exchanges(), [])

    def test_user_denied_at_intuit(self):
        _, pending = self.start()
        self.assert_frontend(self.callback(state=pending["state"], error="access_denied"), "error", "denied")
        self.assertEqual(self.token_exchanges(), [])

    def test_non_numeric_realm_rejected(self):
        _, pending = self.start()
        self.assert_frontend(self.callback(state=pending["state"], code="c", realmId="123abc"), "error", "missing_params")

    # --- success and sandbox verification ---------------------------------------------------
    def test_successful_callback_stores_encrypted_tokens(self):
        _, pending = self.start()
        realm = fake_realm()
        self.assert_frontend(self.callback(state=pending["state"], code="c", realmId=realm), "connected")
        conn = QBOConnection.objects.get(client=self.client_a)
        self.assertEqual(conn.realm_id, realm)
        self.assertEqual(conn.status, "connected")
        self.assertEqual(conn.token_owner, "django")
        self.assertEqual(decrypt(conn.encrypted_refresh_token), self.intuit.issued_refresh_tokens[-1])
        self.assertIsNotNone(conn.refresh_token_expires_at)
        # Company was verified on the sandbox host before anything was stored.
        self.assertTrue(any("sandbox-quickbooks.api.intuit.com" in u and "/companyinfo/" in u for u in self.intuit.urls("GET")))

    def test_company_not_reachable_on_sandbox_host_is_revoked_and_not_stored(self):
        self.intuit.api_status["/companyinfo/"] = 403
        _, pending = self.start()
        self.assert_frontend(self.callback(state=pending["state"], code="c", realmId=fake_realm()), "error", "not_sandbox_company")
        self.assertFalse(QBOConnection.objects.exists())
        self.assertEqual(self.intuit.revoked_tokens, [self.intuit.issued_refresh_tokens[-1]])

    def test_realm_already_connected_to_another_client_is_refused(self):
        other = self.make_client("other-co", self.make_user("bob"))
        realm = fake_realm()
        self.make_connection(other, realm=realm)
        _, pending = self.start()
        self.assert_frontend(self.callback(state=pending["state"], code="c", realmId=realm), "error", "realm_in_use")
        self.assertEqual(self.token_exchanges(), [])

    def test_reconnect_refused_while_checked_out_to_mcp(self):
        self.make_connection(self.client_a, owner=QBOConnection.Owner.MCP)
        resp, pending = self.start()
        self.assert_frontend(resp, "error", "checked_out")
        self.assertIsNone(pending)
