"""Test settings: ephemeral keys, in-memory DB, temp token store. Never reads connection/.secrets/."""
import base64
import os
import secrets
import tempfile
from pathlib import Path

os.environ["QBO_BACKEND_ENV_FILE"] = os.devnull            # do not load the real backend.env
os.environ["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(50)
os.environ["FERNET_KEY"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
os.environ["QUICKBOOKS_CLIENT_ID"] = "test-client-id"
os.environ["QUICKBOOKS_CLIENT_SECRET"] = "test-client-secret"
os.environ["QUICKBOOKS_ENVIRONMENT"] = "sandbox"
os.environ["DJANGO_DB_PATH"] = ":memory:"
os.environ["MCP_TOKEN_STORE_PATH"] = str(Path(tempfile.mkdtemp(prefix="qbo-test-")) / "mcp-server.env")

from .settings import *  # noqa: E402,F401,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]   # fast tests only
