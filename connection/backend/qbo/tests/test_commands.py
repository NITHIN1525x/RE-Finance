import os
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command

from qbo import mcp_store, tokens
from qbo.crypto import decrypt
from qbo.models import AuditLog, Client, QBOConnection

from .helpers import QboTestCase, fake_realm, fake_refresh_token


def run(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


class CreateClientTests(QboTestCase):
    def test_creates_client_with_member(self):
        self.make_user("alice")
        run("create_client", "--name", "ABC Inc (sandbox)", "--slug", "abc-inc-sandbox", "--member", "alice")
        client = Client.objects.get(slug="abc-inc-sandbox")
        self.assertEqual([u.username for u in client.members.all()], ["alice"])
        self.assertTrue(AuditLog.objects.filter(action="create_client", actor__startswith="cli:").exists())

    def test_unknown_member_is_an_error(self):
        with self.assertRaises(CommandError):
            run("create_client", "--name", "X", "--member", "nobody")
        self.assertFalse(Client.objects.exists())


class McpLeaseTests(QboTestCase):
    def setUp(self):
        super().setUp()
        self.a = self.make_client("client-a", self.make_user("alice"))
        self.conn = self.make_connection(self.a, access_valid=False)

    def export(self, slug="client-a"):
        return run("export_mcp_env", "--client", slug)

    def test_export_writes_store_and_transfers_ownership(self):
        out = self.export()
        store = mcp_store.read_store()
        self.conn.refresh_from_db()
        self.assertEqual(self.conn.token_owner, QBOConnection.Owner.MCP)
        self.assertEqual(store["QUICKBOOKS_REALM_ID"], self.conn.realm_id)
        self.assertEqual(store["QUICKBOOKS_REFRESH_TOKEN"], self.intuit.issued_refresh_tokens[-1])   # fresh token
        self.assertEqual(store["QUICKBOOKS_ENVIRONMENT"], "sandbox")
        for flag in ("QUICKBOOKS_DISABLE_WRITE", "QUICKBOOKS_DISABLE_UPDATE", "QUICKBOOKS_DISABLE_DELETE"):
            self.assertEqual(store[flag], "true")
        self.assertNotIn(store["QUICKBOOKS_REFRESH_TOKEN"], out)                 # never printed
        self.assertIn(self.conn.realm_hint, out)
        self.assertNotIn(self.conn.realm_id, out)
        self.assertTrue(AuditLog.objects.filter(action="mcp_checkout", success=True).exists())
        if os.name != "nt":
            self.assertEqual(os.stat(mcp_store.store_path()).st_mode & 0o777, 0o600)

    def test_after_export_django_refuses_to_refresh(self):
        self.export()
        used = len(self.intuit.refresh_tokens_used)
        self.conn.refresh_from_db()
        with self.assertRaises(tokens.TokenUnavailable):
            tokens.refresh_now(self.conn, "alice")
        self.assertEqual(len(self.intuit.refresh_tokens_used), used)

    def test_only_one_client_can_be_checked_out(self):
        b = self.make_client("client-b")
        self.make_connection(b)
        self.export()
        with self.assertRaises(CommandError):
            self.export("client-b")
        self.assertEqual(mcp_store.read_store()["QUICKBOOKS_REALM_ID"], self.conn.realm_id)

    def test_export_refuses_disconnected_client(self):
        self.conn.status = QBOConnection.Status.DISCONNECTED
        self.conn.save()
        with self.assertRaises(CommandError):
            self.export()

    @mock.patch("qbo.mcp_store.running_mcp_server_processes", return_value=[])
    def test_sync_imports_rotated_token_and_wipes_store(self, _):
        self.export()
        rotated = fake_refresh_token()
        mcp_store.write_checked_out(self.conn.realm_id, rotated)       # simulate the server rotating it
        out = run("sync_mcp_tokens", "--client", "client-a")
        self.conn.refresh_from_db()
        self.assertEqual(self.conn.token_owner, QBOConnection.Owner.DJANGO)
        self.assertEqual(decrypt(self.conn.encrypted_refresh_token), rotated)
        self.assertEqual(mcp_store.read_store()["QUICKBOOKS_REFRESH_TOKEN"], "")
        self.assertNotIn(rotated, out)
        self.assertTrue(AuditLog.objects.filter(action="mcp_checkin", detail__contains="rotated").exists())

    @mock.patch("qbo.mcp_store.running_mcp_server_processes", return_value=[4242])
    def test_sync_refuses_while_mcp_server_running(self, _):
        self.export()
        with self.assertRaises(CommandError):
            run("sync_mcp_tokens", "--client", "client-a")
        self.conn.refresh_from_db()
        self.assertEqual(self.conn.token_owner, QBOConnection.Owner.MCP)

    @mock.patch("qbo.mcp_store.running_mcp_server_processes", return_value=None)
    def test_sync_refuses_when_process_state_unknown(self, _):
        self.export()
        with self.assertRaises(CommandError):
            run("sync_mcp_tokens", "--client", "client-a")

    @mock.patch("qbo.mcp_store.running_mcp_server_processes", return_value=[])
    def test_sync_refuses_token_from_another_company(self, _):
        self.export()
        mcp_store.write_checked_out(fake_realm(), fake_refresh_token())
        before = self.conn.encrypted_refresh_token
        with self.assertRaises(CommandError):
            run("sync_mcp_tokens", "--client", "client-a")
        self.conn.refresh_from_db()
        self.assertEqual(self.conn.token_owner, QBOConnection.Owner.MCP)
        self.assertNotEqual(before, "")
