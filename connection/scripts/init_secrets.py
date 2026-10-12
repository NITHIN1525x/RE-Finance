#!/usr/bin/env python
"""Create connection/.secrets/ with owner-only permissions and bootstrap the env files.

- Generates DJANGO_SECRET_KEY and FERNET_KEY directly into backend.env (never printed).
- Leaves QUICKBOOKS_CLIENT_ID / QUICKBOOKS_CLIENT_SECRET empty for a human to fill in.
- Writes a placeholder mcp-server.env (sandbox + read-only flags, no credentials).
- Never overwrites an existing file, so re-running is safe.

Why a directory-level lock: the official MCP server persists rotated refresh tokens with
write-temp-then-rename. On Windows a renamed file keeps the ACL it was created with, which is
inherited from its DIRECTORY, so a per-file ACL would be silently lost on the first rotation.
Locking the directory (inheritable, owner-only) keeps every future file owner-only too.

Usage:
    python connection/scripts/init_secrets.py           # create/lock (idempotent)
    python connection/scripts/init_secrets.py --check   # verify permissions only
"""
import argparse
import base64
import os
import secrets
import subprocess
import sys
from pathlib import Path

SECRETS_DIR = Path(__file__).resolve().parent.parent / ".secrets"
BACKEND_ENV = SECRETS_DIR / "backend.env"
MCP_ENV = SECRETS_DIR / "mcp-server.env"


def backend_env_content():
    # Fernet.generate_key() is exactly urlsafe_b64encode(os.urandom(32)); stdlib avoids a dependency here.
    fernet_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    django_key = secrets.token_urlsafe(50)
    return (
        "# Real secrets. Git-ignored. Owner-only permissions. Do not copy elsewhere.\n"
        f"DJANGO_SECRET_KEY={django_key}\n"
        "DJANGO_DEBUG=true\n"
        "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n"
        f"FERNET_KEY={fernet_key}\n"
        "\n"
        "# Paste your Intuit app's DEVELOPMENT keys below (no quotes, no spaces).\n"
        "QUICKBOOKS_CLIENT_ID=\n"
        "QUICKBOOKS_CLIENT_SECRET=\n"
        "\n"
        "QUICKBOOKS_ENVIRONMENT=sandbox\n"
        "QUICKBOOKS_REDIRECT_URI=http://localhost:8000/api/qbo/callback\n"
        "FRONTEND_URL=http://localhost:5173\n"
    )


MCP_ENV_PLACEHOLDER = (
    "# Generated token store for the official MCP server. Overwritten by `manage.py export_mcp_env`.\n"
    "# Empty credentials on purpose: the server cannot start until a client is exported.\n"
    "QUICKBOOKS_CLIENT_ID=\n"
    "QUICKBOOKS_CLIENT_SECRET=\n"
    "QUICKBOOKS_REFRESH_TOKEN=\n"
    "QUICKBOOKS_REALM_ID=\n"
    "QUICKBOOKS_ENVIRONMENT=sandbox\n"
    "QUICKBOOKS_DISABLE_WRITE=true\n"
    "QUICKBOOKS_DISABLE_UPDATE=true\n"
    "QUICKBOOKS_DISABLE_DELETE=true\n"
)


def current_user_sid():
    out = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=True)
    return out.stdout.strip().split(",")[-1].strip('"')


def lock_directory(path):
    """Owner-only: chmod 700 on POSIX; on Windows replace the ACL with a single inheritable owner ACE."""
    if os.name != "nt":
        os.chmod(path, 0o700)
        for f in path.iterdir():
            os.chmod(f, 0o600)
        return
    sid = current_user_sid()
    # /inheritance:r drops the ACEs inherited from E:\ (Authenticated Users: Modify, Users: Read).
    # (OI)(CI)F makes the owner ACE inherit to files created later, including the MCP server's temp+rename writes.
    subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F"],
                   capture_output=True, text=True, check=True)
    # Re-apply to existing children so they also drop any explicit/legacy ACEs.
    for f in path.iterdir():
        subprocess.run(["icacls", str(f), "/reset"], capture_output=True, text=True, check=True)


def check_permissions(path):
    """Return a list of problems (empty == OK). Prints principals, never file contents."""
    problems = []
    if os.name != "nt":
        for p in [path, *path.iterdir()]:
            mode = p.stat().st_mode & 0o777
            if mode & 0o077:
                problems.append(f"{p.name}: mode {oct(mode)} is readable by group/others")
        return problems
    sid = current_user_sid()
    for p in [path, *path.iterdir()]:
        out = subprocess.run(["icacls", str(p)], capture_output=True, text=True, check=True).stdout
        # icacls prints one ACE per line; ignore the trailing summary line.
        aces = [l.replace(str(p), "").strip() for l in out.splitlines()
                if ":" in l and "Successfully processed" not in l]
        principals = {a.split(":")[0] for a in aces if a}
        me = subprocess.run(["whoami"], capture_output=True, text=True).stdout.strip().lower()
        others = {pr for pr in principals if pr.lower() != me and pr != sid}
        if others:
            problems.append(f"{p.name}: also accessible by {sorted(others)}")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="only verify permissions")
    args = parser.parse_args()

    if not args.check:
        SECRETS_DIR.mkdir(exist_ok=True)
        lock_directory(SECRETS_DIR)  # lock BEFORE writing secrets so they are never briefly world-readable
        for path, content in ((BACKEND_ENV, None), (MCP_ENV, MCP_ENV_PLACEHOLDER)):
            if path.exists():
                print(f"kept existing   {path}")
                continue
            body = backend_env_content() if content is None else content
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", newline="\n") as fh:
                fh.write(body)
            print(f"created         {path}")
        lock_directory(SECRETS_DIR)

    problems = check_permissions(SECRETS_DIR)
    if problems:
        for p in problems:
            print(f"PERMISSION PROBLEM: {p}", file=sys.stderr)
        sys.exit(1)
    print(f"permissions OK  {SECRETS_DIR} (owner-only)")


if __name__ == "__main__":
    main()
