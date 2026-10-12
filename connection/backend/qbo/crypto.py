"""Fernet (AES-128-CBC + HMAC-SHA256, authenticated) encryption for tokens at rest.

The key comes only from settings.FERNET_KEY (environment / connection/.secrets/backend.env). It is never
stored in the database or in Git, so a copy of db.sqlite3 alone does not reveal any token.
"""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

__all__ = ["encrypt", "decrypt", "InvalidToken"]


def _fernet():
    return Fernet(settings.FERNET_KEY.encode())


def encrypt(plaintext):
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext):
    """Raises InvalidToken if the ciphertext was tampered with or the key is wrong."""
    if not ciphertext:
        return ""
    return _fernet().decrypt(ciphertext.encode()).decode()
