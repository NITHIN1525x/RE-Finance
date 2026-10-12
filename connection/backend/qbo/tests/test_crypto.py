import base64
import os

from cryptography.fernet import Fernet
from django.db import connection as db
from django.test import TestCase, override_settings

from qbo.crypto import InvalidToken, decrypt, encrypt

from .helpers import QboTestCase, fake_refresh_token


class FernetTests(TestCase):
    def test_round_trip(self):
        secret = fake_refresh_token()
        ciphertext = encrypt(secret)
        self.assertEqual(decrypt(ciphertext), secret)
        self.assertNotIn(secret, ciphertext)
        self.assertTrue(ciphertext.startswith("gAAAAA"))   # Fernet version byte

    def test_each_encryption_is_unique(self):
        secret = fake_refresh_token()
        self.assertNotEqual(encrypt(secret), encrypt(secret))   # random IV per message

    def test_wrong_key_is_rejected(self):
        ciphertext = encrypt(fake_refresh_token())
        other_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with override_settings(FERNET_KEY=other_key), self.assertRaises(InvalidToken):
            decrypt(ciphertext)

    def test_tampering_is_detected(self):
        ciphertext = encrypt(fake_refresh_token())
        tampered = ciphertext[:-5] + ("A" if ciphertext[-5] != "A" else "B") + ciphertext[-4:]
        with self.assertRaises(InvalidToken):
            decrypt(tampered)

    def test_empty_values(self):
        self.assertEqual(encrypt(""), "")
        self.assertEqual(decrypt(""), "")

    def test_generated_key_format_matches_fernet(self):
        # init_secrets.py generates keys with urlsafe_b64encode(os.urandom(32)); Fernet must accept that.
        Fernet(base64.urlsafe_b64encode(os.urandom(32)))


class EncryptedAtRestTests(QboTestCase):
    def test_database_holds_only_ciphertext(self):
        rt, at = fake_refresh_token(), "eyJ" + "a" * 40 + "." + "b" * 60
        client = self.make_client("abc", self.make_user("op"))
        conn = self.make_connection(client, refresh_token=rt, access_token=at)
        with db.cursor() as cur:
            cur.execute("SELECT encrypted_refresh_token, encrypted_access_token FROM qbo_qboconnection WHERE id=%s", [conn.pk])
            raw = " ".join(cur.fetchone())
        self.assertNotIn(rt, raw)
        self.assertNotIn(at, raw)
        self.assertEqual(decrypt(conn.encrypted_refresh_token), rt)
