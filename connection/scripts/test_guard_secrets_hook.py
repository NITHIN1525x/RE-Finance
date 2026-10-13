"""Tests for connection/scripts/guard_secrets_hook.py (the PreToolUse guard, DECISIONS_LOG D-53).

Run:  python connection/scripts/test_guard_secrets_hook.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "guard_secrets_hook.py"


def run_hook(tool, **tool_input):
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})
    return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)


class GuardSecretsHookTests(unittest.TestCase):
    def assert_blocked(self, tool, **tool_input):
        r = run_hook(tool, **tool_input)
        self.assertEqual(r.returncode, 2, f"{tool} {tool_input} was not blocked")
        self.assertIn("D-53", r.stderr)

    def assert_allowed(self, tool, **tool_input):
        self.assertEqual(run_hook(tool, **tool_input).returncode, 0, f"{tool} {tool_input} was blocked")

    def test_blocks_the_incident_pattern(self):
        # The D-53 diagnostic: an inline Python script that opened connection/.secrets and printed context.
        self.assert_blocked("Bash", command='python - <<EOF\nPath("connection/.secrets").rglob("*")\nEOF')

    def test_blocks_shell_reads_of_secret_files(self):
        self.assert_blocked("Bash", command="cat connection/.secrets/backend.env")
        self.assert_blocked("Bash", command="strings connection/.secrets/db.sqlite3 | head")
        self.assert_blocked("PowerShell", command=r"Get-Content connection\.secrets\mcp-server.env")
        self.assert_blocked("Bash", command="ls -a connection/.secrets")

    def test_blocks_file_tools_on_secret_paths(self):
        self.assert_blocked("Read", file_path=r"E:\RE-Finance\qbo-claude-exercise\connection\.secrets\backend.env")
        self.assert_blocked("Grep", pattern="TOKEN", path="connection/.secrets")
        self.assert_blocked("Glob", pattern="connection/.secrets/*")
        self.assert_blocked("Edit", file_path="connection/.secrets/backend.env", old_string="a", new_string="b")

    def test_allows_vetted_tools_and_normal_work(self):
        self.assert_allowed("Bash", command="python connection/scripts/secret_scan --staged")
        self.assert_allowed("Bash", command="connection/backend/.venv/Scripts/python connection/scripts/rotate_django_secret")
        self.assert_allowed("Bash", command="cd connection/backend && .venv/Scripts/python manage.py check")
        self.assert_allowed("Read", file_path="connection/backend/config/settings.py")
        self.assert_allowed("Grep", pattern="SECRETS_DIR", path="connection/backend")
        self.assert_allowed("Bash", command="git status --short")

    def test_does_not_match_lookalikes(self):
        self.assert_allowed("Read", file_path="docs/secrets-handling.md")
        self.assert_allowed("Bash", command="grep -n my.secretsauce notes.txt")

    def test_non_json_input_is_ignored(self):
        r = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
