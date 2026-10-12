import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from qbo import intuit

BACKEND_DIR = Path(__file__).resolve().parents[2]


class SandboxGuardTests(SimpleTestCase):
    def test_only_sandbox_https_host_is_allowed(self):
        intuit.assert_sandbox_url("https://sandbox-quickbooks.api.intuit.com/v3/company/1/companyinfo/1")
        for url in ("https://quickbooks.api.intuit.com/v3/company/1/companyinfo/1",     # production
                    "http://sandbox-quickbooks.api.intuit.com/v3/company/1/x",            # not https
                    "https://sandbox-quickbooks.api.intuit.com.evil.example/v3/x",
                    "https://evil.example/?h=sandbox-quickbooks.api.intuit.com"):
            with self.subTest(url=url), self.assertRaises(intuit.ProductionAccessRefused):
                intuit.assert_sandbox_url(url)

    def test_api_call_to_production_base_is_refused_before_any_network_io(self):
        with mock.patch.object(intuit, "SANDBOX_API_BASE", "https://quickbooks.api.intuit.com"), \
             mock.patch("qbo.intuit.requests.get") as get:
            with self.assertRaises(intuit.ProductionAccessRefused):
                intuit.api_get("123", "companyinfo/123", "token")
            get.assert_not_called()

    def test_malformed_realm_is_refused(self):
        with mock.patch("qbo.intuit.requests.get") as get, self.assertRaises(intuit.IntuitError):
            intuit.api_get("123/../456", "companyinfo/1", "token")
        get.assert_not_called()

    def test_settings_refuse_production_environment(self):
        env = {**os.environ, "QUICKBOOKS_ENVIRONMENT": "production", "QBO_BACKEND_ENV_FILE": os.devnull,
               "DJANGO_SECRET_KEY": "x" * 50, "FERNET_KEY": "y" * 43 + "=", "DJANGO_SETTINGS_MODULE": "config.settings"}
        proc = subprocess.run([sys.executable, "-c", "import django; django.setup()"],
                              cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("must be exactly 'sandbox'", proc.stderr)

    def test_settings_refuse_case_variants(self):
        # The official server treats anything except exactly "sandbox" as production; so do we.
        env = {**os.environ, "QUICKBOOKS_ENVIRONMENT": "Sandbox", "QBO_BACKEND_ENV_FILE": os.devnull,
               "DJANGO_SECRET_KEY": "x" * 50, "FERNET_KEY": "y" * 43 + "=", "DJANGO_SETTINGS_MODULE": "config.settings"}
        proc = subprocess.run([sys.executable, "-c", "import django; django.setup()"],
                              cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
