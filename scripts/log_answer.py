#!/usr/bin/env python
"""Append one question-and-answer entry to submission/Q&A log.md (newest first). Used by the /log-answer command.

Reads ONE JSON object on stdin:
    {"question": "...", "source": "QuickBooks sandbox via MCP", "answer": "...", "figures": ["1,680.78", ...]}

Refuses the entry, and leaves the file untouched, if:
  - a field is missing, or the source is not one of SOURCES;
  - a key figure does not appear word for word in the answer (figures must be cited, never added);
  - the text looks like a secret: the repo's secret scanner (token/key shapes, credential assignments, and the
    real values in connection/.secrets/*.env, reported by key name only), a realm-ID-like number (12+ digits, or
    "realm" next to a number), or any mention of the .secrets folder.
On refusal it prints the rule names only, never the matched text. The file is written atomically (temp + rename).

Usage:  python scripts/log_answer.py < entry.json      (exit 0 written, 1 refused, 2 bad input)
"""
import importlib.machinery
import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOG = REPO / "submission" / "Q&A log.md"
MARKER = "<!-- entries: newest first. Append with /log-answer (scripts/log_answer.py); do not edit by hand. -->"
SOURCES = ("QuickBooks sandbox via MCP", "ABC workbook via the skill",
           "QuickBooks sandbox via MCP + ABC workbook via the skill")
HEADER = f"""# Questions & answers log

Questions asked during the demo and the answers given, newest first. Each entry records when it was answered,
the data source, the answer as given, and the figures it cites. Entries are appended by the `/log-answer` command
and checked before writing: no tokens, secrets or realm IDs, and every key figure must appear in the answer.

{MARKER}
"""
EXTRA_RULES = [
    ("realm-id-like-number", re.compile(r"(?<![\d,.])\d{12,}(?![\d,.])")),
    ("realm-mention-with-number", re.compile(r"(?i)realm\W{0,12}\d")),
    ("secrets-folder", re.compile(r"(?i)\.secrets")),
]


def _scanner():
    path = REPO / "connection" / "scripts" / "secret_scan"
    loader = importlib.machinery.SourceFileLoader("secret_scan", str(path))
    spec = importlib.util.spec_from_loader("secret_scan", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def secret_findings(text, secrets_dir=None):
    """Rule names only (never the matched text)."""
    scan = _scanner()
    known = scan.load_known_values(secrets_dir or scan.DEFAULT_SECRETS_DIR)
    rules = [rule for _, _, rule, _ in scan.scan_text("entry", text) + scan.scan_known("entry", text, known)]
    rules += [name for name, rx in EXTRA_RULES if rx.search(text)]
    return sorted(set(rules))


def clean(text):
    """Keep the log well-formed: no HTML comments (they could break the marker), trimmed whitespace."""
    return str(text).replace("<!--", "").replace("-->", "").strip()


def validate(entry, secrets_dir=None):
    missing = [k for k in ("question", "source", "answer", "figures") if not entry.get(k)]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")
    if entry["source"] not in SOURCES:
        raise ValueError(f"source must be one of: {'; '.join(SOURCES)}")
    if not isinstance(entry["figures"], list) or not all(isinstance(f, str) and f.strip() for f in entry["figures"]):
        raise ValueError("figures must be a non-empty list of strings")
    absent = [f for f in entry["figures"] if f.strip() not in entry["answer"]]
    if absent:
        raise ValueError(f"{len(absent)} key figure(s) do not appear word for word in the answer; only cite figures the answer gives")
    found = secret_findings("\n".join([entry["question"], entry["answer"], *entry["figures"]]), secrets_dir)
    if found:
        raise ValueError(f"refused: possible secret or identifier ({', '.join(found)}); nothing was written")


def render(entry, when):
    question = " ".join(clean(entry["question"]).split())
    title = question if len(question) <= 90 else question[:87].rstrip() + "…"
    answer = "\n".join(f"> {line}" if line.strip() else ">" for line in clean(entry["answer"]).splitlines())
    figures = "\n".join(f"- {clean(f)}" for f in entry["figures"])
    return (f"## {when} · {title.lstrip('#').strip()}\n\n"
            f"**Answered:** {when}\n\n"
            f"**Question:** {question}\n\n"
            f"**Data source:** {entry['source']}\n\n"
            f"**Answer:**\n\n{answer}\n\n"
            f"**Key figures cited:**\n\n{figures}\n")


def append(entry, log_path=LOG, now=None, secrets_dir=None):
    validate(entry, secrets_dir)
    when = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")
    current = log_path.read_text(encoding="utf-8") if log_path.is_file() else HEADER
    if MARKER not in current:
        raise ValueError(f"{log_path.name} has no entry marker; refusing to rewrite it")
    head, tail = current.split(MARKER, 1)
    body = tail.strip()
    body = "" if body.startswith("_No entries yet") else body
    text = f"{head}{MARKER}\n\n{render(entry, when)}" + (f"\n{body}\n" if body else "")
    fd, tmp = tempfile.mkstemp(dir=log_path.parent, prefix=".tmp-qa-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, log_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return when


def main():
    try:
        entry = json.load(sys.stdin)
        if not isinstance(entry, dict):
            raise ValueError("expected one JSON object")
    except ValueError as exc:
        print(f"log_answer: bad input ({exc})", file=sys.stderr)
        return 2
    try:
        when = append(entry)
    except ValueError as exc:
        print(f"log_answer: NOT logged. {exc}", file=sys.stderr)
        return 1
    print(f"log_answer: logged entry at {when} to submission/{LOG.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
