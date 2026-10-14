"""Shared helpers for the stretch-goal scripts (D-36 / D-62). Throwaway tooling: nothing in Tasks 1-4 imports it.

Rules kept here so every script follows them:
- Sandbox only: every API call goes to SANDBOX_API_HOST; anything else raises.
- Secrets never printed: tokens live only in memory and in owner-only files under connection/.secrets/ (deleted after
  revocation); realm IDs are shown as their first 4 characters and compared only by hash.
- Grants are short-lived and separate from the demo connection: each script gets its own OAuth grant for the NEW
  sandbox company, revokes it at the end and confirms the revocation (a refresh must fail with invalid_grant).
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SECRETS = REPO / "connection" / ".secrets"
DEMO_STORE = SECRETS / "mcp-server.env"            # the demo connection's store: only ever READ, for a realm hash
OUT = REPO / "demo-output" / "stretch"               # git-ignored working folder for evidence and intermediate files
COMPANY_RECORD = OUT / "stretch-company.json"        # name, realm hint and realm HASH of the stretch company

# Same values Django uses (connection/backend/qbo/intuit.py), copied rather than imported so nothing there changes.
AUTHORIZATION_ENDPOINT = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
REVOCATION_ENDPOINT = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
ACCOUNTING_SCOPE = "com.intuit.quickbooks.accounting"
SANDBOX_API_HOST = "sandbox-quickbooks.api.intuit.com"
MINOR_VERSION = "75"

CALLBACK_PORT = 8765
CALLBACK_PATH = "/stretch/callback"
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"


class StretchError(Exception):
    """A stop condition. The message never contains a secret."""


# ------------------------------------------------------------------------------------------------ secrets on disk
def read_env(path):
    values = {}
    if not Path(path).is_file():
        return values
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def write_secret_file(path, values, header):
    """Owner-only file in connection/.secrets/ (inherits the folder's ACL on Windows; chmod 600 elsewhere)."""
    path = Path(path)
    if path.parent.resolve() != SECRETS.resolve():
        raise StretchError("refusing to write a token file outside connection/.secrets/")
    text = f"# {header}\n" + "".join(f"{k}={v}\n" for k, v in values.items())
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)
    if os.name != "nt":
        os.chmod(path, 0o600)


def delete_secret_file(path):
    path = Path(path)
    if path.exists():
        path.unlink()
    return not path.exists()


def app_credentials():
    """The Intuit app's client ID and secret, from the same file Django reads. Never printed."""
    env = read_env(SECRETS / "backend.env")
    cid, secret = env.get("QUICKBOOKS_CLIENT_ID"), env.get("QUICKBOOKS_CLIENT_SECRET")
    if not cid or not secret:
        raise StretchError("the Intuit app credentials are not configured in connection/.secrets/backend.env")
    return cid, secret


# ------------------------------------------------------------------------------------------------ realm handling
def realm_hash(realm):
    return hashlib.sha256(str(realm).encode()).hexdigest()


def realm_hint(realm):
    return f"{str(realm)[:4]}…"


def demo_realm_hash():
    """Hash of the demo connection's realm, read from its store WITHOUT changing anything. None if not checked out."""
    realm = read_env(DEMO_STORE).get("QUICKBOOKS_REALM_ID")
    return realm_hash(realm) if realm else None


# ------------------------------------------------------------------------------------------------ HTTP
def _request(method, url, *, headers=None, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            parsed = json.loads(body) if body else {}
        except ValueError:
            parsed = {"raw": body.decode("utf-8", "replace")[:300]}
        return exc.code, parsed


def _basic(cid, secret):
    return "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode()


def token_request(form):
    cid, secret = app_credentials()
    return _request("POST", TOKEN_ENDPOINT, data=urllib.parse.urlencode(form).encode(),
                    headers={"Authorization": _basic(cid, secret), "Accept": "application/json",
                             "Content-Type": "application/x-www-form-urlencoded"})


def revoke(refresh_token):
    """Revoke the grant and confirm it: a refresh with the same token must now fail with invalid_grant."""
    cid, secret = app_credentials()
    status, _ = _request("POST", REVOCATION_ENDPOINT, data=json.dumps({"token": refresh_token}).encode(),
                         headers={"Authorization": _basic(cid, secret), "Accept": "application/json",
                                  "Content-Type": "application/json"})
    if status != 200:
        raise StretchError(f"revocation returned HTTP {status}")
    status, body = token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})
    confirmed = status == 400 and body.get("error") == "invalid_grant"
    if not confirmed:
        raise StretchError(f"revocation NOT confirmed: a refresh returned HTTP {status} ({body.get('error')})")
    return True


class Sandbox:
    """Minimal QuickBooks API client bound to ONE sandbox realm. Refuses any other host."""

    def __init__(self, realm, access_token):
        self.realm, self.access_token = str(realm), access_token

    def call(self, method, path, *, params=None, body=None):
        query = {"minorversion": MINOR_VERSION, **(params or {})}
        url = f"https://{SANDBOX_API_HOST}/v3/company/{self.realm}/{path.lstrip('/')}?{urllib.parse.urlencode(query)}"
        if urllib.parse.urlparse(url).hostname != SANDBOX_API_HOST:
            raise StretchError("refusing a QuickBooks call to a non-sandbox host")
        headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        status, parsed = _request(method, url, headers=headers, data=data)
        if status >= 400:
            fault = (parsed.get("Fault") or {}).get("Error") or [{}]
            raise StretchError(f"QuickBooks {method} {path.split('?')[0]} -> HTTP {status}: "
                               f"{fault[0].get('Message', '')} {fault[0].get('Detail', '')}".strip())
        return parsed

    def query(self, sql):
        return self.call("GET", "query", params={"query": sql}).get("QueryResponse", {})

    def company_name(self):
        return self.call("GET", f"companyinfo/{self.realm}")["CompanyInfo"]["CompanyName"]


# ------------------------------------------------------------------------------------------------ OAuth sign-in
def interactive_grant(purpose, timeout=900):
    """Open Intuit's sign-in page in the user's browser and wait for the callback on localhost:8765.

    Returns {"realm", "access_token", "refresh_token"}. The authorization URL (which carries the app's client ID) is
    not printed: the browser is opened directly, and a copy is written to connection/.secrets/ for manual use.
    """
    cid, _ = app_credentials()
    state = secrets.token_urlsafe(24)
    url = AUTHORIZATION_ENDPOINT + "?" + urllib.parse.urlencode({
        "client_id": cid, "response_type": "code", "scope": ACCOUNTING_SCOPE, "redirect_uri": REDIRECT_URI,
        "state": state})
    url_file = SECRETS / "stretch-auth-url.txt"
    write_secret_file(url_file, {"URL": url}, f"Intuit sign-in link for the stretch {purpose} grant; deleted after use")
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != CALLBACK_PATH:
                self.send_response(404)
                self.end_headers()
                return
            q = dict(urllib.parse.parse_qsl(parsed.query))
            ok = q.get("state") == state and "code" in q and "realmId" in q
            result.update(q if ok else {"error": q.get("error") or "state mismatch or missing code"})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Signed in. You can close this tab and return to Claude Code." if ok else "Sign-in failed; see Claude Code."
            self.wfile.write(f"<html><body><p>{msg}</p></body></html>".encode())

        def log_message(self, *args):  # keep the code and realm out of any log
            pass

    server = http.server.HTTPServer(("localhost", CALLBACK_PORT), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    print(f"[stretch] Opened Intuit's sign-in page in your browser for the {purpose} grant "
          "(a copy of the link is in connection/.secrets/stretch-auth-url.txt). Waiting up to 15 minutes…", flush=True)
    webbrowser.open(url)
    thread.join(timeout)
    server.server_close()
    delete_secret_file(url_file)
    if "code" not in result:
        raise StretchError(f"sign-in did not complete ({result.get('error', 'timed out')})")
    status, tokens = token_request({"grant_type": "authorization_code", "code": result["code"],
                                    "redirect_uri": REDIRECT_URI})
    if status != 200 or "refresh_token" not in tokens:
        raise StretchError(f"token exchange failed (HTTP {status}, {tokens.get('error')})")
    return {"realm": result["realmId"], "access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"]}


def check_company(grant, expect_company):
    """Sandbox company named as expected, and NOT the demo connection's company. Returns its name."""
    if demo_realm_hash() is not None and realm_hash(grant["realm"]) == demo_realm_hash():
        raise StretchError("this is the DEMO company (abc-inc-sandbox). Refusing: the stretch must use a NEW sandbox")
    name = Sandbox(grant["realm"], grant["access_token"]).company_name()   # succeeds only on the sandbox host
    print(f"[stretch] Company name read back from QuickBooks: {name!r} (expected exactly {expect_company!r}: "
          f"{'match' if name == expect_company else 'NO MATCH, stopping'})", flush=True)
    if name != expect_company:
        raise StretchError(f"signed in to company {name!r}, expected {expect_company!r}")
    return name
