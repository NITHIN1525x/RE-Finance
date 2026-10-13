#!/usr/bin/env python
"""Claude Code PreToolUse hook: block any tool call that names a .secrets/ path (DECISIONS_LOG D-53).

Wired in .claude/settings.json. Claude reads the hook's JSON on stdin; exit code 2 blocks the call and
shows stderr to Claude. Read/Edit/Write/Grep/Glob are blocked when a path argument names .secrets; Bash and
PowerShell are blocked when the command text does. So an ad-hoc diagnostic can't open the secret files
and echo their content into the session.

Not blocked, by design: vetted tools that locate the folder themselves and never print values, such as
Django settings, connection/scripts/secret_scan (location + rule only) and
connection/scripts/rotate_django_secret. A person can still inspect .secrets directly.

Limits: it guards against accidents, not a determined bypass (a path built at runtime isn't seen). If
Python can't start, Claude Code treats the hook error as non-blocking, so it fails open.
"""
import json
import re
import sys

SECRETS = re.compile(r"(^|[\\/\s\"'=`(])\.secrets([\\/\s\"'`)]|$)")
PATH_KEYS = ("file_path", "path", "notebook_path", "pattern", "glob")
SHELL_TOOLS = {"Bash", "PowerShell"}

MESSAGE = ("Blocked by guard_secrets_hook (DECISIONS_LOG D-53): this call names connection/.secrets/. "
           "Don't read or print secret files. To look for secrets, run connection/scripts/secret_scan "
           "(it reports location + rule only); to rotate the Django key, connection/scripts/rotate_django_secret.")


def blocked(event):
    tool = event.get("tool_name", "")
    args = event.get("tool_input") or {}
    if tool in SHELL_TOOLS:
        return bool(SECRETS.search(str(args.get("command", ""))))
    return any(SECRETS.search(str(args.get(k, ""))) for k in PATH_KEYS)


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # not a hook payload; nothing to judge
    if blocked(event):
        print(MESSAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
