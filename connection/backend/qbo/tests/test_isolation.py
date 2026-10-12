"""Client A's user must not be able to read or act on client B in any way."""
from qbo import audit
from qbo.crypto import decrypt
from qbo.models import QBOConnection
from qbo.views import PENDING_KEY

from .helpers import QboTestCase


class IsolationTests(QboTestCase):
    def setUp(self):
        super().setUp()
        self.alice, self.bob = self.make_user("alice"), self.make_user("bob")
        self.a = self.make_client("client-a", self.alice)
        self.b = self.make_client("client-b", self.bob)
        self.conn_a = self.make_connection(self.a)
        self.conn_b = self.make_connection(self.b)
        self.b_refresh_token = decrypt(self.conn_b.encrypted_refresh_token)
        audit.record("test_connection", "bob", True, self.b, "B-only event")
        audit.record("test_connection", "alice", True, self.a, "A-only event")
        self.client.force_login(self.alice)

    def test_client_list_only_shows_own_clients(self):
        slugs = [c["slug"] for c in self.client.get("/api/clients/").json()["clients"]]
        self.assertEqual(slugs, ["client-a"])

    def test_cannot_test_other_clients_connection(self):
        resp = self.client.post("/api/qbo/client-b/test")
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn(self.conn_b.realm_id, "".join(self.intuit.urls()))   # no API call for B's realm

    def test_cannot_disconnect_other_client(self):
        self.assertEqual(self.client.post("/api/qbo/client-b/disconnect").status_code, 404)
        self.conn_b.refresh_from_db()
        self.assertEqual(self.conn_b.status, "connected")
        self.assertEqual(decrypt(self.conn_b.encrypted_refresh_token), self.b_refresh_token)
        self.assertEqual(self.intuit.revoked_tokens, [])

    def test_cannot_start_oauth_for_other_client(self):
        resp = self.client.get("/api/qbo/connect", {"client": "client-b"})
        self.assertIn("reason=unknown_client", resp["Location"])
        self.assertIsNone(self.client.session.get(PENDING_KEY))

    def test_audit_is_scoped(self):
        details = [e["detail"] for e in self.client.get("/api/audit/").json()["entries"]]
        self.assertIn("A-only event", details)
        self.assertNotIn("B-only event", details)
        self.assertEqual(self.client.get("/api/audit/", {"client": "client-b"}).status_code, 404)

    def test_realm_comes_from_stored_connection_not_request(self):
        # A user-supplied realm is ignored: the call must go to A's stored realm only.
        resp = self.client.post(f"/api/qbo/client-a/test?realm_id={self.conn_b.realm_id}",
                                {"realm_id": self.conn_b.realm_id})
        self.assertEqual(resp.status_code, 200)
        urls = " ".join(self.intuit.urls("GET"))
        self.assertIn(f"/v3/company/{self.conn_a.realm_id}/", urls)
        self.assertNotIn(self.conn_b.realm_id, urls)

    def test_unauthenticated_requests_are_refused(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/clients/").status_code, 403)
        self.assertEqual(self.client.post("/api/qbo/client-a/test").status_code, 403)
        self.assertEqual(self.client.get("/api/audit/").status_code, 403)

    def test_post_requires_csrf_token(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.force_login(self.alice)
        self.assertEqual(csrf_client.post("/api/qbo/client-a/disconnect").status_code, 403)
        self.conn_a.refresh_from_db()
        self.assertEqual(self.conn_a.status, QBOConnection.Status.CONNECTED)
