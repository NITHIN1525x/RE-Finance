"""Minimal KEY=VALUE loader for connection/.secrets/backend.env (no python-dotenv dependency).

Real environment variables win over the file, so a deployment can inject secrets from a secrets
manager without any file at all.
"""
import os
from pathlib import Path


def load_env_file(path):
    path = Path(path)
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)
    return True
