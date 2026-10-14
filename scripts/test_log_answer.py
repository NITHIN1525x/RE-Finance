"""Tests for scripts/log_answer.py. Works on a temporary log file; never touches submission/ or real secrets.

Run:  python scripts/test_log_answer.py
"""
import random
import shutil
import string
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import log_answer as L  # noqa: E402

rng = random.Random(7)
GOOD = {"question": "What was net income in Sep 2026?", "source": "QuickBooks sandbox via MCP",
        "answer": "Net income in Sep 2026 was 1,680.78 (sandbox P&L, by month).", "figures": ["1,680.78"]}


class LogAnswerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "Q&A log.md"
        self.log.write_text(L.HEADER + "\n_No entries yet._\n", encoding="utf-8")
        self.no_secrets = self.tmp / "no-secrets"            # empty dir: the known-value check finds nothing

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def add(self, entry, minute=0):
        return L.append(entry, self.log, now=datetime(2026, 10, 13, 12, minute, tzinfo=timezone.utc),
                        secrets_dir=self.no_secrets)

    def test_entry_has_all_fields_and_replaces_placeholder(self):
        self.add(GOOD)
        text = self.log.read_text(encoding="utf-8")
        for part in ("**Question:** What was net income in Sep 2026?", "**Data source:** QuickBooks sandbox via MCP",
                     "> Net income in Sep 2026 was 1,680.78", "- 1,680.78", "2026-10-13 12:00 UTC"):
            self.assertIn(part, text)
        self.assertNotIn("_No entries yet", text)

    def test_newest_first(self):
        self.add(GOOD, minute=1)
        self.add({**GOOD, "question": "Second question?"}, minute=2)
        text = self.log.read_text(encoding="utf-8")
        self.assertLess(text.index("Second question?"), text.index("What was net income"))

    def test_figures_must_appear_in_the_answer(self):
        with self.assertRaises(ValueError):
            self.add({**GOOD, "figures": ["1,680.78", "2,000.00"]})

    def test_unknown_source_is_refused(self):
        with self.assertRaises(ValueError):
            self.add({**GOOD, "source": "my memory"})

    def test_secret_like_text_is_refused_and_file_untouched(self):
        before = self.log.read_text(encoding="utf-8")
        token = "AB11" + "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(46))   # fake shape
        realm = "".join(rng.choice(string.digits) for _ in range(16))
        for bad in (f"the refresh token is {token}", f"company {realm}", "realm 9341", "see connection/.secrets/x"):
            with self.assertRaises(ValueError) as ctx:
                self.add({**GOOD, "answer": GOOD["answer"] + " " + bad})
            self.assertNotIn(token, str(ctx.exception))
            self.assertNotIn(realm, str(ctx.exception))
        self.assertEqual(self.log.read_text(encoding="utf-8"), before)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["Q&A log.md"])   # no temp files left

    def test_known_secret_value_is_refused(self):
        secrets = self.tmp / ".secrets"
        secrets.mkdir()
        value = "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(32))
        (secrets / "backend.env").write_text(f"QUICKBOOKS_CLIENT_SECRET={value}\n", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            L.append({**GOOD, "answer": GOOD["answer"] + " " + value}, self.log, secrets_dir=secrets)
        self.assertNotIn(value, str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
