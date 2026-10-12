from qbo import mcp_store, tokens
from qbo.crypto import decrypt
from qbo.models import AuditLog, QBOConnection

from .helpers import QboTestCase, fake_refresh_token


class TokenLifecycleTests(QboTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice")
        self.c = self.make_client("abc-inc-sandbox", self.user)
        self.client.force_login(self.user)

    def refreshes(self):
        return len(self.intuit.refresh_tokens_used)

    def test_valid_cached_access_token_does_not_refresh(self):
        conn = self.make_connection(self.c, access_valid=True)
        tokens.get_access_token(conn, "alice")
        self.assertEqual(self.refreshes(), 0)

    def test_expired_access_token_refreshes_once_and_stores_rotated_token(self):
        old = fake_refresh_token()
        conn = self.make_connection(self.c, refresh_token=old, access_valid=False)
        tokens.get_access_token(conn, "alice")
        tokens.get_access_token(conn, "alice")          # second call uses the fresh cached token
        self.assertEqual(self.intuit.refresh_tokens_used, [old])
        conn.refresh_from_db()
        self.assertEqual(decrypt(conn.encrypted_refresh_token), self.intuit.issued_refresh_tokens[-1])
        self.assertNotEqual(decrypt(conn.encrypted_refresh_token), old)
        self.assertTrue(AuditLog.objects.filter(action="refresh", detail__contains="rotated").exists())

    def test_invalid_grant_marks_refresh_required_and_persists(self):
        conn = self.make_connection(self.c, access_valid=False)
        self.intuit.refresh_status, self.intuit.refresh_error = 400, "invalid_grant"
        with self.assertRaises(tokens.TokenUnavailable) as ctx:
            tokens.get_access_token(conn, "alice")
        self.assertEqual(ctx.exception.code, "refresh_required")
        conn.refresh_from_db()   # status change must survive (not rolled back with the transaction)
        self.assertEqual(conn.status, QBOConnection.Status.REFRESH_REQUIRED)
        self.assertTrue(AuditLog.objects.filter(action="refresh", success=False).exists())

    def test_transient_failure_keeps_status(self):
        conn = self.make_connection(self.c, access_valid=False)
        self.intuit.refresh_status = 503
        resp = self.client.post("/api/qbo/abc-inc-sandbox/test")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["error"], "transient")
        conn.refresh_from_db()
        self.assertEqual(conn.status, QBOConnection.Status.CONNECTED)

    def test_django_never_refreshes_a_checked_out_connection(self):
        conn = self.make_connection(self.c, access_valid=False, owner=QBOConnection.Owner.MCP)
        resp = self.client.post("/api/qbo/abc-inc-sandbox/test")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"], "checked_out")
        self.assertEqual(self.refreshes(), 0)
        with self.assertRaises(tokens.TokenUnavailable):
            tokens.refresh_now(conn, "alice")
        self.assertEqual(self.refreshes(), 0)

    def test_checked_out_connection_can_still_use_valid_cached_access_token(self):
        self.make_connection(self.c, access_valid=True, owner=QBOConnection.Owner.MCP)
        self.assertEqual(self.client.post("/api/qbo/abc-inc-sandbox/test").status_code, 200)
        self.assertEqual(self.refreshes(), 0)

    def test_test_endpoint_returns_company_and_pnl_summary(self):
        self.make_connection(self.c)
        body = self.client.post("/api/qbo/abc-inc-sandbox/test").json()
        self.assertEqual(body["environment"], "sandbox")
        self.assertEqual(body["company"]["name"], "Sandbox Company_US_1")
        self.assertEqual(body["profit_and_loss"]["totals"], {"total_income": "1000.50", "total_expenses": "400.00",
                                                              "net_income": "600.50"})
        self.assertTrue(all("sandbox-quickbooks.api.intuit.com" in u for u in self.intuit.urls("GET")))

    def test_test_endpoint_retries_once_after_401(self):
        self.make_connection(self.c, access_valid=True)
        self.intuit.api_status["/companyinfo/"] = 401
        resp = self.client.post("/api/qbo/abc-inc-sandbox/test")
        self.assertEqual(resp.status_code, 502)            # still 401 after one forced refresh
        self.assertEqual(self.refreshes(), 1)

    def test_not_connected_returns_409(self):
        self.assertEqual(self.client.post("/api/qbo/abc-inc-sandbox/test").status_code, 409)
        self.assertEqual(self.client.post("/api/qbo/abc-inc-sandbox/disconnect").status_code, 409)


class DisconnectTests(QboTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("alice")
        self.c = self.make_client("abc-inc-sandbox", self.user)
        self.client.force_login(self.user)

    def assert_wiped(self, conn):
        conn.refresh_from_db()
        self.assertEqual(conn.status, QBOConnection.Status.DISCONNECTED)
        self.assertEqual(conn.encrypted_refresh_token, "")
        self.assertEqual(conn.encrypted_access_token, "")
        self.assertEqual(conn.token_owner, QBOConnection.Owner.DJANGO)

    def test_disconnect_revokes_and_wipes(self):
        rt = fake_refresh_token()
        conn = self.make_connection(self.c, refresh_token=rt)
        resp = self.client.post("/api/qbo/abc-inc-sandbox/disconnect")
        self.assertEqual(resp.json()["revoked_at_intuit"], True)
        self.assertEqual(self.intuit.revoked_tokens, [rt])
        self.assert_wiped(conn)
        self.assertTrue(AuditLog.objects.filter(action="disconnect", success=True).exists())

    def test_disconnect_still_wipes_when_revoke_fails(self):
        conn = self.make_connection(self.c)
        self.intuit.revoke_status = 500
        resp = self.client.post("/api/qbo/abc-inc-sandbox/disconnect")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["revoked_at_intuit"], False)
        self.assert_wiped(conn)
        self.assertTrue(AuditLog.objects.filter(action="disconnect", success=False, detail__contains="FAILED").exists())

    def test_disconnect_of_checked_out_connection_revokes_latest_store_token_and_wipes_store(self):
        conn = self.make_connection(self.c, owner=QBOConnection.Owner.MCP)
        rotated_by_mcp = fake_refresh_token()
        mcp_store.write_checked_out(conn.realm_id, rotated_by_mcp)
        self.client.post("/api/qbo/abc-inc-sandbox/disconnect")
        self.assertEqual(self.intuit.revoked_tokens, [rotated_by_mcp])
        store = mcp_store.read_store()
        self.assertEqual(store["QUICKBOOKS_REFRESH_TOKEN"], "")
        self.assertEqual(store["QUICKBOOKS_CLIENT_SECRET"], "")
        self.assert_wiped(conn)

    def test_reconnect_after_disconnect_is_allowed_for_same_realm(self):
        conn = self.make_connection(self.c)
        self.client.post("/api/qbo/abc-inc-sandbox/disconnect")
        other = self.make_client("other", self.make_user("bob"))
        # A disconnected row no longer claims the realm (conditional unique constraint).
        self.make_connection(other, realm=conn.realm_id)
