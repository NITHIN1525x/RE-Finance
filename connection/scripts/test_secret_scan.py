"""Tests for connection/scripts/secret_scan using FAKE secrets generated at runtime.

The fake values are random strings shaped like real ones. They are built in memory, never stored in
this file, so the scanner does not flag its own test suite and no real credential is ever used.

Run:  python connection/scripts/test_secret_scan.py
"""
import base64
import os
import random
import shutil
import string
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SCANNER = SCRIPTS / "secret_scan"
HOOKS_DIR = SCRIPTS.parent.parent / ".githooks"
rng = random.Random(1234)  # deterministic fakes
ALNUM = string.ascii_letters + string.digits


def rand(n, alphabet=ALNUM):
    return "".join(rng.choice(alphabet) for _ in range(n))


def b64url(n):
    return rand(n, ALNUM + "-_")


# Fake values in the SHAPE of each secret type.
FAKES = {
    "refresh_token": "AB" + "11" + rand(46),
    "access_token": "eyJ" + b64url(30) + ".." + b64url(60) + "." + b64url(40),
    "fernet_key": base64.urlsafe_b64encode(bytes(rng.randrange(256) for _ in range(32))).decode(),
    "fernet_ciphertext": "gAAAAA" + b64url(120),
    "django_key": rand(50, ALNUM + "!@%^*-_"),
    "client_secret": rand(40),
}


def run_scan(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCANNER), *args], capture_output=True, text=True, cwd=cwd)


class SecretScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def assert_detects(self, filename, text, expected_rule, secret):
        p = self.write(filename, text)
        r = run_scan(str(p))
        self.assertEqual(r.returncode, 1, f"not detected ({expected_rule}): {r.stdout}")
        self.assertIn(expected_rule, r.stdout)
        # The core safety property: the secret value never appears in the report.
        self.assertNotIn(secret, r.stdout + r.stderr)

    def test_refresh_token(self):
        s = FAKES["refresh_token"]
        self.assert_detects("cfg.txt", f"QUICKBOOKS_REFRESH_TOKEN={s}\n", "intuit-token", s)

    def test_access_token_in_json(self):
        s = FAKES["access_token"]
        self.assert_detects("resp.json", f'{{"access_token": "{s}"}}\n', "jwt-or-access-token", s)

    def test_fernet_key_assignment(self):
        s = FAKES["fernet_key"]
        self.assert_detects("settings.txt", f"FERNET_KEY={s}\n", "FERNET", s)

    def test_bare_fernet_key_in_code(self):
        s = FAKES["fernet_key"]
        self.assert_detects("crypto.py", f'cipher = Fernet(b"{s}")  # encrypt\n', "fernet-key-shape", s)

    def test_fernet_ciphertext(self):
        s = FAKES["fernet_ciphertext"]
        self.assert_detects("dump.sql", f"INSERT INTO t VALUES ('{s}');\n", "fernet-ciphertext", s)

    def test_django_secret_key(self):
        s = FAKES["django_key"]
        self.assert_detects("settings.py", f"SECRET_KEY = '{s}'\n", "credential-assignment:SECRET_KEY", s)

    def test_client_secret(self):
        s = FAKES["client_secret"]
        self.assert_detects("notes.md", f"QUICKBOOKS_CLIENT_SECRET={s}\n", "CLIENT_SECRET", s)

    def test_url_with_embedded_token_is_still_detected(self):
        s = FAKES["refresh_token"]
        self.assert_detects("cfg.py", f'CALLBACK_URL = "https://example.com/cb?refresh_token={s}"\n', "intuit-token", s)

    def test_url_with_credentials_is_detected(self):
        s = FAKES["client_secret"]
        self.assert_detects("cfg.py", f'DATABASE_PASSWORD = "postgres://admin:{s}@db.example.com/x"\n', "PASSWORD", s)  # secret-scan: allow (fixture; value injected at runtime)

    def test_forbidden_env_filename(self):
        p = self.write("backend/.env", "DJANGO_DEBUG=true\n")
        r = run_scan(str(p))
        self.assertEqual(r.returncode, 1)
        self.assertIn("forbidden-file:real-env-file", r.stdout)

    def test_placeholders_and_code_refs_are_clean(self):
        clean = (
            "QUICKBOOKS_CLIENT_ID=\n"
            "QUICKBOOKS_CLIENT_SECRET=your_client_secret_here\n"
            "QUICKBOOKS_REFRESH_TOKEN=<redacted>\n"
            "FERNET_KEY=<generated-by-init_secrets>\n"
            'SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]\n'
            "key = settings.FERNET_KEY\n"
            "const token = process.env.QUICKBOOKS_REFRESH_TOKEN;\n"
            "QUICKBOOKS_DISABLE_WRITE=true\n"
            "conn.token_owner = QBOConnection.Owner.MCP\n"
            'TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"\n'
            "token: `oauth.platform.intuit.com/oauth2/v1/tokens/bearer`\n"
        )
        p = self.write("app.env.example", clean)
        r = run_scan(str(p))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_allow_pragma(self):
        s = FAKES["client_secret"]
        p = self.write("doc.md", f"CLIENT_SECRET={s}  # secret-scan: allow (documented fake)\n")
        self.assertEqual(run_scan(str(p)).returncode, 0)

    def test_pre_commit_hook_blocks_secret_and_allows_clean(self):
        """End to end: a throwaway git repo using this repo's hook."""
        repo = self.tmp / "repo"
        repo.mkdir()
        git = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "test@example.invalid")
        git("config", "user.name", "secret-scan test")
        git("config", "core.hooksPath", str(HOOKS_DIR))

        (repo / "leak.py").write_text(f'QUICKBOOKS_REFRESH_TOKEN = "{FAKES["refresh_token"]}"\n')
        git("add", "leak.py")
        r = git("commit", "-q", "-m", "should be blocked")
        self.assertNotEqual(r.returncode, 0, "hook allowed a secret")
        self.assertNotIn(FAKES["refresh_token"], r.stdout + r.stderr)

        git("rm", "-q", "--cached", "leak.py")
        (repo / "leak.py").unlink()
        (repo / "ok.py").write_text('token = os.environ["QUICKBOOKS_REFRESH_TOKEN"]\n')
        git("add", "ok.py")
        r = git("commit", "-q", "-m", "clean commit")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
