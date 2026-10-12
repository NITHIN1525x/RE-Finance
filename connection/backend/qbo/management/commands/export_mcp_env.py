from django.core.management.base import BaseCommand, CommandError

from qbo import audit, intuit, mcp_store, tokens
from qbo.models import Client, QBOConnection


class Command(BaseCommand):
    help = ("CHECK OUT a client's connection to the official MCP server: refresh once, write the token store "
            "(owner-only), and make the MCP server the sole refresh-token owner until sync_mcp_tokens.")

    def add_arguments(self, parser):
        parser.add_argument("--client", required=True, help="Client slug")

    def handle(self, *args, **opts):
        client = Client.objects.filter(slug=opts["client"]).select_related("connection").first()
        conn = getattr(client, "connection", None) if client else None
        if conn is None or conn.status != QBOConnection.Status.CONNECTED or not conn.encrypted_refresh_token:
            raise CommandError("Client not found or not connected. Connect it in the Connection Console first.")
        if not intuit.credentials_configured():
            raise CommandError("QUICKBOOKS_CLIENT_ID/SECRET are not configured in connection/.secrets/backend.env")
        store = mcp_store.read_store()
        if store.get("QUICKBOOKS_REFRESH_TOKEN") and store.get("QUICKBOOKS_REALM_ID") != conn.realm_id:
            raise CommandError("The MCP token store holds another company's token. Run sync_mcp_tokens for that client first.")
        try:
            tokens.checkout_to_mcp(conn, audit.cli_actor())
        except tokens.TokenUnavailable as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(
            f"Checked out '{client.slug}' (realm {conn.realm_hint}) to {mcp_store.store_path()}\n"
            "Refresh-token owner is now the MCP server; Django will not refresh this connection.\n"
            "Read-only flags written: QUICKBOOKS_DISABLE_WRITE/UPDATE/DELETE=true. Start or restart Claude Code to load it.\n"
            f"To take ownership back: stop the MCP server, then `python manage.py sync_mcp_tokens --client {client.slug}`."))
