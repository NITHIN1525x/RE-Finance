from django.core.management.base import BaseCommand, CommandError

from qbo import audit, mcp_store, tokens
from qbo.models import Client


class Command(BaseCommand):
    help = ("CHECK IN a connection from the MCP server: import the (possibly rotated) refresh token, encrypt it, "
            "wipe the token store and make Django the refresh-token owner again. The MCP server must be stopped.")

    def add_arguments(self, parser):
        parser.add_argument("--client", required=True, help="Client slug")
        parser.add_argument("--force", action="store_true",
                            help="Skip the running-process check (only if you are sure no MCP server is running)")

    def handle(self, *args, **opts):
        client = Client.objects.filter(slug=opts["client"]).select_related("connection").first()
        conn = getattr(client, "connection", None) if client else None
        if conn is None:
            raise CommandError("Client not found or never connected.")
        if not opts["force"]:
            # A running server still holds the token in memory and would keep refreshing it:
            # checking in now would create two owners of one rotating token.
            pids = mcp_store.running_mcp_server_processes()
            if pids is None:
                raise CommandError("Could not check for a running MCP server. Stop it (exit Claude Code), then re-run with --force.")
            if pids:
                raise CommandError(f"MCP server appears to be running (PID {', '.join(map(str, pids))}). "
                                   "Exit Claude Code (or disable the server with /mcp), then re-run.")
        try:
            rotated = tokens.checkin_from_mcp(conn, audit.cli_actor())
        except tokens.TokenUnavailable as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(
            f"Checked in '{client.slug}' (realm {conn.realm_hint}). Owner is Django again; token store wiped. "
            + ("The MCP server had rotated the refresh token; the new one is stored encrypted." if rotated
               else "Refresh token was not rotated during checkout.")))
