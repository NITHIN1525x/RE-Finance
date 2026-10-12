"""The token store file handed to the official MCP server (QUICKBOOKS_TOKEN_STORE_PATH).

It lives in connection/.secrets/, which carries an inheritable owner-only ACL (Windows) or chmod 700
(POSIX), so both our writes and the MCP server's own temp-file+rename rotations stay owner-only.
Format matches what the server parses with dotenv (verified in quickbooks-client.ts @ 31a1dd5).
"""
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.views.decorators.debug import sensitive_variables

READ_ONLY_FLAGS = {
    # The server only honours the exact lowercase string "true" (register-tool.ts).
    "QUICKBOOKS_DISABLE_WRITE": "true",
    "QUICKBOOKS_DISABLE_UPDATE": "true",
    "QUICKBOOKS_DISABLE_DELETE": "true",
}

PLACEHOLDER_HEADER = (
    "# Generated token store for the official MCP server. Managed by `manage.py export_mcp_env` /\n"
    "# `sync_mcp_tokens`. Do not edit by hand. Empty credentials = nothing checked out.\n"
)


def store_path():
    return Path(settings.MCP_TOKEN_STORE_PATH)


def _write_atomic(content):
    """Temp file in the SAME directory + rename, so the result inherits the directory's owner-only ACL."""
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    if os.name != "nt":
        os.chmod(path, 0o600)


@sensitive_variables("refresh_token", "lines")
def write_checked_out(realm_id, refresh_token):
    lines = [
        PLACEHOLDER_HEADER.rstrip("\n").replace("Empty credentials = nothing checked out.", "CHECKED OUT."),
        f"QUICKBOOKS_CLIENT_ID={settings.QUICKBOOKS_CLIENT_ID}",
        f"QUICKBOOKS_CLIENT_SECRET={settings.QUICKBOOKS_CLIENT_SECRET}",
        f"QUICKBOOKS_REFRESH_TOKEN={refresh_token}",
        f"QUICKBOOKS_REALM_ID={realm_id}",
        "QUICKBOOKS_ENVIRONMENT=sandbox",
        *(f"{k}={v}" for k, v in READ_ONLY_FLAGS.items()),
    ]
    _write_atomic("\n".join(lines) + "\n")


def write_placeholder():
    lines = [
        "QUICKBOOKS_CLIENT_ID=",
        "QUICKBOOKS_CLIENT_SECRET=",
        "QUICKBOOKS_REFRESH_TOKEN=",
        "QUICKBOOKS_REALM_ID=",
        "QUICKBOOKS_ENVIRONMENT=sandbox",
        *(f"{k}={v}" for k, v in READ_ONLY_FLAGS.items()),
    ]
    _write_atomic(PLACEHOLDER_HEADER + "\n".join(lines) + "\n")


def read_store():
    """Parse the store like dotenv does for our simple KEY=VALUE format. Returns {} if missing."""
    path = store_path()
    if not path.is_file():
        return {}
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def running_mcp_server_processes():
    """Best-effort: command lines that look like the official server or our launcher. Returns a list
    of PIDs (never command lines, which could in theory carry arguments we do not want to print)."""
    markers = ("quickbooks-online-mcp-server", "mcp_launch")
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
                 "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"],
                capture_output=True, text=True, timeout=20).stdout
        else:
            out = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None   # unknown: callers must treat this as "cannot confirm stopped"
    pids = []
    for line in out.splitlines():
        if any(m in line for m in markers):
            pid = line.strip().split(None, 1)[0]
            if pid.isdigit() and int(pid) != os.getpid():
                pids.append(int(pid))
    return pids
