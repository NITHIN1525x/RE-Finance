#!/usr/bin/env python
"""Evaluation harness for the monthly-trend-analysis skill (Task 3).

For every E2E golden case:
  1. runs the REAL skill with `claude -p` from the repo root (stream-json captured, model pinned),
  2. execution checks (skill invoked, script ran, outputs where asked, nothing else in the repo changed),
  3. structured checks: the run's own *-trends.json / .md vs facts derived from raw workbook cells,
  4. commentary checks: a SEPARATE grader call (different pinned model, no tools, no skills, JSON schema)
     returns PASS/FAIL + evidence per required/forbidden claim. Missing/invalid grader output -> BLOCKED.
Also runs the skill's regression tests and the golden-fact consistency check, and writes one report.

Usage (repo root, skill venv):
  .claude/skills/monthly-trend-analysis/.venv/Scripts/python evals/run_evals.py [--cases a,c] [--run-id ID]
Exit code: 0 if every executed check passed, 1 if any FAIL, 2 if anything BLOCKED (and no FAIL).
"""
import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import provenance  # noqa: E402  (number-provenance check, deterministic)
EVALS = REPO / "evals"
SKILL = REPO / ".claude" / "skills" / "monthly-trend-analysis"
SKILL_PY = SKILL / (".venv/Scripts/python.exe" if platform.system() == "Windows" else ".venv/bin/python")
CLAUDE = shutil.which("claude")

SKILL_MODEL = "claude-opus-5-5"     # generator: the model a user of this repo's Claude Code session gets
GRADER_MODEL = "claude-sonnet-5-5"  # judge: deliberately a different model from the generator
SKILL_TOOLS = ["Skill", "Bash", "Read", "Edit", "Write", "Glob", "Grep"]
SKILL_BUDGET, GRADER_BUDGET = "3", "0.5"
SKILL_TIMEOUT, GRADER_TIMEOUT = 900, 300
NARRATIVE_MARKER = "<!-- NARRATIVE:"

GRADER_SCHEMA = {
    "type": "object",
    "properties": {"claims": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
                       "evidence": {"type": "string"}},
        "required": ["id", "verdict", "evidence"], "additionalProperties": False}}},
    "required": ["claims"], "additionalProperties": False,
}


# ------------------------------------------------------------------------------------------------ utilities
def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, (dict, list)):
        data = json.dumps(data, indent=2, default=str)
    path.write_text(data, encoding="utf-8", newline=chr(10))   # LF, matching .gitattributes (stable hashes)


def rel(p):
    return Path(p).resolve().relative_to(REPO).as_posix()


def repo_changes():
    """Porcelain status lines outside evals/runs (informational: recorded in the manifest)."""
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=REPO,
                         capture_output=True, text=True).stdout.splitlines()
    return sorted(l for l in out if "evals/runs/" not in l and "__pycache__" not in l)


# ------------------------------------------------------------------------------------------------ contamination guard
# git status alone is not enough: a file that is already modified can change again without its status line changing.
# So we hash the CONTENT of every tracked file and every untracked-but-not-ignored file outside evals/runs/.
def snapshot(root=REPO):
    """{relative posix path: sha256 or '<deleted>'} for tracked + untracked-not-ignored files outside evals/runs/."""
    import hashlib
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root,
                         capture_output=True, text=True, encoding="utf-8").stdout
    state = {}
    for p in sorted(set(x for x in out.split("\0") if x)):
        if p.startswith("evals/runs/") or "__pycache__" in p:
            continue
        f = Path(root) / p
        if f.is_dir():                      # submodule gitlink: track its checked-out commit instead
            head = subprocess.run(["git", "-C", str(f), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            state[p] = f"gitlink:{head}"
        elif f.is_file():
            state[p] = hashlib.sha256(f.read_bytes()).hexdigest()
        else:
            state[p] = "<deleted>"
    return state


def diff_snapshots(before, after):
    """[(path, 'modified'|'created'|'deleted')] between two snapshots."""
    changes = []
    for p in sorted(set(before) | set(after)):
        a, b = before.get(p), after.get(p)
        if a == b:
            continue
        kind = "created" if a is None else "deleted" if (b is None or b == "<deleted>") else "modified"
        changes.append((p, kind))
    return changes


def attributable_to(changes, tool_calls, root=REPO):
    """Split changes into (made by the skill run's own tool calls, not attributable). A path counts as the skill's
    if a Write/Edit targeted it or a Bash command names it (relative, absolute, or by file name)."""
    texts = []
    for t in tool_calls:
        inp = t.get("input") or {}
        texts += [str(inp.get("file_path", "")), str(inp.get("command", ""))]
    blob = "\n".join(texts).replace("\\", "/").lower()
    root_posix = str(Path(root).resolve()).replace("\\", "/").lower()
    mine, other = [], []
    for p, kind in changes:
        lp = p.lower()
        hit = lp in blob or f"{root_posix}/{lp}" in blob or ("/" in lp and lp.rsplit("/", 1)[1] in blob)
        (mine if hit else other).append((p, kind))
    return mine, other


def contamination_messages(changes, phase, started, finished):
    return [f"harness contamination: {p} {kind} during run (during {phase}, between {started} and {finished})"
            for p, kind in changes]


def fmt_fact(value):
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return json.dumps(value)


def resolve(data, path):
    """Path = list of keys / list indexes / {field: value} selectors (exactly one match required)."""
    cur = data
    for step in path:
        if isinstance(step, dict):
            if not isinstance(cur, list):
                raise LookupError(f"selector {step} applied to non-list")
            hits = [x for x in cur if all(x.get(k) == v for k, v in step.items())]
            if len(hits) != 1:
                raise LookupError(f"selector {step} matched {len(hits)} items")
            cur = hits[0]
        elif isinstance(step, int):
            cur = cur[step]
        else:
            if not isinstance(cur, dict) or step not in cur:
                raise LookupError(f"key {step!r} not found")
            cur = cur[step]
    return cur


def close(a, b, tol):
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) <= tol
    return a == b


# ------------------------------------------------------------------------------------------------ structured checks
def run_structured(checks, analysis, md, facts, tolerances):
    results = []
    flags_text = "\n".join(f["message"] for f in analysis.get("flags", []))
    for c in checks:
        res = {"id": c["id"], "desc": c["desc"], "type": c["type"]}
        try:
            expected = facts[c["fact"]]["value"] if "fact" in c else c.get("expected")
            res["source"] = ({"fact": c["fact"], **{k: facts[c["fact"]][k] for k in ("sheet", "cells", "formula")}}
                             if "fact" in c else "literal")
            tol = tolerances.get(c.get("tol"), 0.0) if isinstance(c.get("tol"), str) else (c.get("tol") or 0.0)
            if c["type"] == "value":
                actual = resolve(analysis, c["path"])
                ok = close(actual, expected, tol)
            elif c["type"] == "count":
                items = resolve(analysis, c["path"])
                if "where" in c:
                    items = [x for x in items if all(x.get(k) == v for k, v in c["where"].items())]
                actual = len(items)
                ok = actual == expected
            elif c["type"] == "all_field":
                items = resolve(analysis, c["path"])
                actual = sorted({x[c["field"]] for x in items})
                expected = c["allowed"]
                ok = set(actual) <= set(expected) and bool(items)
            elif c["type"] == "regex":
                actual = resolve(analysis, c["path"])
                expected = c["pattern"]
                ok = re.search(expected, str(actual)) is not None
            elif c["type"] in ("flag_regex", "md_regex"):
                hay = flags_text if c["type"] == "flag_regex" else md
                found = re.search(c["pattern"], hay)
                actual = found.group(0) if found else None
                expected = f"{'present' if c['present'] else 'absent'}: /{c['pattern']}/"
                ok = bool(found) == c["present"]
            else:
                raise ValueError(f"unknown check type {c['type']}")
            res.update({"expected": expected, "actual": actual, "tolerance": tol, "status": "PASS" if ok else "FAIL"})
        except (LookupError, IndexError, TypeError, KeyError) as exc:
            res.update({"status": "FAIL", "actual": None, "error": f"{type(exc).__name__}: {exc}"})
        results.append(res)
    return results


# ------------------------------------------------------------------------------------------------ skill run
def run_skill(case, prompt_template, case_dir):
    out_dir = case_dir / "skill_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = prompt_template.replace("{out_dir}", rel(out_dir))
    cmd = [CLAUDE, "-p", prompt, "--model", SKILL_MODEL, "--strict-mcp-config", "--allowedTools", *SKILL_TOOLS,
           "--no-session-persistence", "--max-budget-usd", SKILL_BUDGET, "--output-format", "stream-json", "--verbose"]
    sd = case_dir / "skill_run"
    write(sd / "prompt.txt", prompt)
    write(sd / "command.json", {"argv": ["claude", *cmd[1:]], "cwd": str(REPO), "timeout_s": SKILL_TIMEOUT})
    before = repo_changes()
    snap_before, window_start = snapshot(), now()
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                              stdin=subprocess.DEVNULL, timeout=SKILL_TIMEOUT)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code = (exc.stdout or "") if isinstance(exc.stdout, str) else "", "TIMEOUT", -1
    elapsed = round(time.time() - t0, 1)
    write(sd / "stream.jsonl", stdout)
    write(sd / "stderr.txt", stderr)
    after = repo_changes()
    snap_after, window_end = snapshot(), now()

    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    final = next((e for e in reversed(events) if e.get("type") == "result"), None)
    tool_uses = [c for e in events if isinstance(e.get("message"), dict)
                 for c in (e["message"].get("content") or []) if isinstance(c, dict) and c.get("type") == "tool_use"]
    meta = {
        "exit_code": code, "elapsed_s": elapsed,
        "model_requested": SKILL_MODEL, "model_reported": init.get("model"),
        "claude_code_version": init.get("claude_code_version"), "permission_mode": init.get("permissionMode"),
        "tools_available": init.get("tools"), "skills_available": init.get("skills"), "mcp_servers": init.get("mcp_servers"),
        "num_turns": final.get("num_turns") if final else None, "total_cost_usd": final.get("total_cost_usd") if final else None,
        "is_error": final.get("is_error") if final else None, "result_subtype": final.get("subtype") if final else None,
        "permission_denials": final.get("permission_denials") if final else None,
        "tool_calls": [{"tool": t["name"], "input": {k: (str(v)[:300]) for k, v in (t.get("input") or {}).items()}} for t in tool_uses],
        "final_message": (final or {}).get("result"),
        "repo_changes_before": before, "repo_changes_after": after,
        "skill_window": {"started": window_start, "finished": window_end},
    }
    # Content-hash diff of everything outside evals/runs/ across the skill run, split by attribution.
    changes = diff_snapshots(snap_before, snap_after)
    full_calls = [{"tool": t["name"], "input": t.get("input") or {}} for t in tool_uses]
    mine, other = attributable_to(changes, full_calls)
    meta["outside_changes"] = {"by_skill": mine, "not_attributable": other}
    write(sd / "run_meta.json", meta)
    return meta, out_dir


def execution_checks(meta, out_dir):
    infra_ok = meta["exit_code"] == 0 and meta["result_subtype"] == "success" and not meta["is_error"]
    skill_called = any(t["tool"] == "Skill" and "monthly-trend-analysis" in t["input"].get("skill", "") for t in meta["tool_calls"])
    script_ran = any(t["tool"] == "Bash" and "run_trends.py" in t["input"].get("command", "") for t in meta["tool_calls"])
    jsons, mds = sorted(out_dir.glob("*-trends.json")), sorted(out_dir.glob("*-trends.md"))
    by_skill = meta["outside_changes"]["by_skill"]
    unattributed = meta["outside_changes"]["not_attributable"]
    md = mds[0].read_text(encoding="utf-8") if len(mds) == 1 else ""
    checks = [
        ("X1", "claude -p run completed successfully", infra_ok, f"exit {meta['exit_code']}, subtype {meta['result_subtype']}"),
        ("X2", "the monthly-trend-analysis skill was invoked (Skill tool)", skill_called, ""),
        ("X3", "the skill's script run_trends.py was executed", script_ran, ""),
        ("X4", "exactly one *-trends.json and one *-trends.md written to the requested folder", len(jsons) == 1 and len(mds) == 1,
         f"{len(jsons)} json, {len(mds)} md in {rel(out_dir)}"),
        ("X5", "nothing outside evals/runs/ was modified by the skill run", not by_skill,
         "; ".join(f"{p} {k}" for p, k in by_skill) or "no changes made by the skill"),
        ("X6", "the narrative placeholder was replaced with commentary", bool(md) and NARRATIVE_MARKER not in md, ""),
    ]
    results = [{"id": i, "desc": d, "type": "execution", "status": "PASS" if ok else "FAIL", "detail": det}
               for i, d, ok, det in checks]
    if not infra_ok:                      # the CLI itself failed: nothing about the skill can be judged
        for r in results:
            r["status"] = "BLOCKED" if r["status"] == "FAIL" else r["status"]
    if unattributed and results[4]["status"] == "PASS":
        # Something else changed the repo during this skill run: X5 cannot be judged (reported as contamination).
        results[4]["status"] = "BLOCKED"
        results[4]["detail"] = ("changes during the skill run not attributable to it (see harness contamination): "
                                + "; ".join(f"{p} {k}" for p, k in unattributed))
    analysis = json.loads(jsons[0].read_text(encoding="utf-8")) if len(jsons) == 1 else None
    return results, analysis, md, infra_ok


# ------------------------------------------------------------------------------------------------ grader
def commentary_of(md):
    if "## 1. Commentary (draft)" not in md:
        return None
    body = md.split("## 1. Commentary (draft)", 1)[1].split("### Flags raised", 1)[0].strip()
    return None if (not body or NARRATIVE_MARKER in body) else body


def grade(case, commentary, facts, policy, gdir):
    rules = ([{"id": r["id"], "kind": "required", "claim": r["claim"]} for r in case["commentary"]["required"]] +
             [{"id": r["id"], "kind": "forbidden", "claim": r["claim"]} for r in case["commentary"]["forbidden"]])
    if not rules:
        return []
    fact_ids = sorted({f for r in case["commentary"]["required"] + case["commentary"]["forbidden"] for f in r.get("facts", [])})
    payload = {"rounding_policy": policy,
               "reference_facts": [{"id": f, "value": fmt_fact(facts[f]["value"]), "meaning": facts[f]["formula"],
                                    "source": f"{facts[f]['sheet']}!{','.join(facts[f]['cells'])}"} for f in fact_ids],
               "rules": rules, "commentary": commentary}
    template = (EVALS / "grader_prompt.md").read_text(encoding="utf-8")
    prompt = template.replace("{input_json}", json.dumps(payload, indent=2))
    cmd = [CLAUDE, "-p", "--model", GRADER_MODEL, "--json-schema", json.dumps(GRADER_SCHEMA), "--output-format", "json",
           "--tools", "", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence",
           "--max-budget-usd", GRADER_BUDGET]
    write(gdir / "prompt.txt", prompt)
    write(gdir / "input.json", payload)
    write(gdir / "command.json", {"argv": ["claude", *cmd[1:]], "stdin": "prompt.txt", "cwd": "(empty temp dir)"})
    raw, parsed, why = None, None, None
    try:
        with tempfile.TemporaryDirectory() as empty:          # no CLAUDE.md, no project skills, no repo context
            proc = subprocess.run(cmd, input=prompt, cwd=empty, capture_output=True, text=True, encoding="utf-8",
                                  timeout=GRADER_TIMEOUT)
        write(gdir / "raw_stdout.txt", proc.stdout)
        write(gdir / "raw_stderr.txt", proc.stderr)
        raw = json.loads(proc.stdout)
        parsed = raw.get("structured_output")
        if proc.returncode != 0 or raw.get("is_error") or not isinstance(parsed, dict):
            why = f"grader call failed (exit {proc.returncode}, is_error {raw.get('is_error')})"
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        why = f"grader unavailable: {type(exc).__name__}"
    meta = {"model_requested": GRADER_MODEL,
            "models_reported": list((raw or {}).get("modelUsage", {}).keys()),
            "total_cost_usd": (raw or {}).get("total_cost_usd"), "error": why}
    write(gdir / "grader_meta.json", meta)
    by_id = {}
    if parsed and not why:
        for c in parsed.get("claims", []):
            by_id.setdefault(c.get("id"), []).append(c)
    results = []
    for r in rules:
        got = by_id.get(r["id"], [])
        if why or len(got) != 1 or got[0].get("verdict") not in ("PASS", "FAIL") or not got[0].get("evidence", "").strip():
            results.append({**r, "status": "BLOCKED",
                            "evidence": why or f"grader returned {len(got)} verdicts for this id (need exactly 1)"})
        else:
            results.append({**r, "status": got[0]["verdict"], "evidence": got[0]["evidence"]})
    write(gdir / "parsed.json", {"meta": meta, "results": results})
    return results


# ------------------------------------------------------------------------------------------------ regression tests
def regression_tests():
    proc = subprocess.run([str(SKILL_PY), "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=SKILL,
                          capture_output=True, text=True, encoding="utf-8")
    lines = proc.stderr.splitlines()
    tests = []
    for i, l in enumerate(lines):
        m = re.match(r"^(test\S+ \(.+?\))(?:\n.*)? \.\.\. ?(.*)$", l)
        if not m:
            continue
        tail = m.group(2).strip()
        status = next((s for s in ("ok", "FAIL", "ERROR", "skipped") if tail.endswith(s) or tail.startswith(s)), None)
        if status is None and i + 1 < len(lines):      # a test printed output, so its verdict is on the next line
            nxt = lines[i + 1].strip()
            status = next((s for s in ("ok", "FAIL", "ERROR", "skipped") if nxt.startswith(s)), "unknown")
        tests.append({"test": m.group(1), "status": status})
    ran = next((l for l in lines if l.startswith("Ran ")), "Ran ? tests")
    verdict = next((l for l in reversed(lines) if l.startswith(("OK", "FAILED"))), "UNKNOWN")
    return {"summary": f"{ran} -> {verdict}", "ok": proc.returncode == 0, "tests": tests, "raw_tail": "\n".join(lines[-15:])}


# ------------------------------------------------------------------------------------------------ main
def case_status(items):
    st = [i["status"] for i in items]
    return "FAIL" if "FAIL" in st else "BLOCKED" if "BLOCKED" in st else "PASS"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", help="comma-separated case id prefixes (e.g. a,c)")
    ap.add_argument("--run-id")
    args = ap.parse_args()
    if not CLAUDE:
        sys.exit("claude CLI not found on PATH")
    spec = json.loads((EVALS / "goldens" / "cases.json").read_text(encoding="utf-8"))
    facts = json.loads((EVALS / "goldens" / "source_facts.json").read_text(encoding="utf-8"))
    cases = spec["cases"]
    if args.cases:
        wanted = [p.strip() for p in args.cases.split(",")]
        cases = [c for c in cases if any(c["id"].startswith(w) for w in wanted)]
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = EVALS / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    facts_check = subprocess.run([str(SKILL_PY), str(EVALS / "goldens" / "derive_facts.py"), "--check"], cwd=REPO,
                                 capture_output=True, text=True, encoding="utf-8")
    manifest = {"run_id": run_id, "started": now(), "git_head": head, "git_dirty": repo_changes(),
                "claude_cli": subprocess.run([CLAUDE, "--version"], capture_output=True, text=True).stdout.strip(),
                "skill_model": SKILL_MODEL, "grader_model": GRADER_MODEL, "skill_tools": SKILL_TOOLS,
                "skill_budget_usd": SKILL_BUDGET, "grader_budget_usd": GRADER_BUDGET, "python": sys.version.split()[0],
                "facts_consistent_with_workbooks": facts_check.returncode == 0, "facts_check_output": facts_check.stdout.strip(),
                "cases": [c["id"] for c in cases]}
    write(run_dir / "manifest.json", manifest)
    if facts_check.returncode != 0:
        sys.exit("source_facts.json does not match the workbooks; refusing to run (re-derive and review goldens first)")

    print(f"run {run_id} | HEAD {head} | skill model {SKILL_MODEL} | grader model {GRADER_MODEL}", flush=True)
    guard = {"snap": snapshot(), "since": now(), "entries": []}

    def guard_check(phase, attributed=()):
        """Report any change outside evals/runs/ since the previous checkpoint that a skill run did not make itself."""
        current, until = snapshot(), now()
        made_by_skill = set(map(tuple, attributed))
        changes = [c for c in diff_snapshots(guard["snap"], current) if c not in made_by_skill]
        for (path, kind), msg in zip(changes, contamination_messages(changes, phase, guard["since"], until)):
            guard["entries"].append({"path": path, "change": kind, "phase": phase, "between": [guard["since"], until],
                                     "message": msg})
            print(f"   !! {msg}", flush=True)
        guard["snap"], guard["since"] = current, until

    reg = regression_tests()
    write(run_dir / "regression_tests.json", reg)
    print(f"regression tests: {reg['summary']}", flush=True)
    guard_check("regression tests")

    results = []
    for case in cases:
        cdir = run_dir / case["id"]
        print(f"\n== {case['id']}: running skill...", flush=True)
        meta, out_dir = run_skill(case, spec["skill_prompts"][case["input"]["prompt"]], cdir)
        execs, analysis, md, infra_ok = execution_checks(meta, out_dir)
        if analysis is not None:
            structured = run_structured(case["structured"], analysis, md, facts, spec["tolerances"])
        else:
            st = "BLOCKED" if not infra_ok else "FAIL"
            structured = [{"id": c["id"], "desc": c["desc"], "type": c["type"], "status": st,
                           "error": "no analysis JSON produced"} for c in case["structured"]]
        commentary = commentary_of(md) if md else None
        write(cdir / "commentary.md", commentary or "(no commentary)")
        if not case["commentary"]["required"] and not case["commentary"]["forbidden"]:
            claims = []
        elif commentary is None:
            st = "BLOCKED" if not infra_ok else "FAIL"
            claims = [{**{"id": r["id"], "claim": r["claim"]}, "kind": k, "status": st if k == "required" else "BLOCKED",
                       "evidence": "no commentary produced by the skill run"}
                      for k in ("required", "forbidden") for r in case["commentary"][k]]
        else:
            print(f"   grading commentary with {GRADER_MODEL}...", flush=True)
            claims = grade(case, commentary, facts, spec["rounding_policy"], cdir / "grader")
        # P1: every number in the commentary must come from this run's own JSON/report (no model involved).
        if analysis is not None and commentary is not None:
            prov = provenance.check(commentary, analysis, md)
            write(cdir / "provenance.json", prov)
            bad = [f for f in prov["numbers"] if f["status"] == "UNMATCHED"]
            prov_checks = [{"id": "P1", "type": "provenance", "status": prov["status"],
                            "desc": "every number in the commentary matches a value in this run's own output",
                            "detail": f"{prov['matched']} matched, {prov['ignored']} ignored, {prov['unmatched']} unmatched",
                            "unmatched": [{"text": f["text"], "sentence": f["sentence"]} for f in bad]}]
        else:
            prov_checks = [{"id": "P1", "type": "provenance", "status": "BLOCKED" if not infra_ok else "FAIL",
                            "desc": "every number in the commentary matches a value in this run's own output",
                            "detail": "no commentary or no analysis output to check", "unmatched": []}]
        case_result = {"id": case["id"], "title": case["title"], "input": case["input"],
                       "skill_run": {k: meta[k] for k in ("model_requested", "model_reported", "claude_code_version",
                                                          "num_turns", "total_cost_usd", "elapsed_s", "permission_mode")},
                       "execution": execs, "structured": structured, "provenance": prov_checks, "commentary": claims}
        case_result["status"] = case_status(execs + structured + prov_checks + claims)
        write(cdir / "result.json", case_result)
        results.append(case_result)
        print(f"   {case_result['status']}  (exec {case_status(execs)}, structured {case_status(structured)}, "
              f"provenance {prov_checks[0]['status']}, "
              f"commentary {case_status(claims) if claims else 'n/a'})", flush=True)
        guard_check(f"case {case['id']}", attributed=meta["outside_changes"]["by_skill"])

    calibrations = []
    for case in cases:
        cal = case.get("calibration")
        if not cal:
            continue
        frozen = subprocess.run(["git", "show", f"HEAD:{cal['artifact']}"], cwd=REPO, capture_output=True, text=True,
                                encoding="utf-8").stdout
        text = commentary_of(frozen)
        cdir = run_dir / f"calibration_{case['id']}"
        write(cdir / "commentary.md", text or "(none)")
        print(f"\n== calibration for {case['id']} (frozen {cal['artifact']} @ {head})", flush=True)
        claims = grade(case, text, facts, spec["rounding_policy"], cdir / "grader") if text else []
        calibrations.append({"case": case["id"], "artifact": f"{cal['artifact']} @ {head}", "commentary": claims,
                             "status": case_status(claims) if claims else "BLOCKED"})
        write(cdir / "result.json", calibrations[-1])

    controls = []
    by_case = {c["id"]: c for c in spec["cases"]}
    for ctl in spec.get("grader_controls", {}).get("controls", []):
        case = by_case[ctl["case"]]
        print(f"\n== grader control {ctl['id']} (synthetic text, validation only)", flush=True)
        cdir = run_dir / f"grader_control_{ctl['id']}"
        write(cdir / "commentary.md", ctl["commentary"])
        claims = grade(case, ctl["commentary"], facts, spec["rounding_policy"], cdir / "grader")
        checks = [{"id": x["id"], "expected": ctl["expected"][x["id"]], "got": x["status"], "evidence": x["evidence"],
                   "agrees": x["status"] == ctl["expected"][x["id"]]} for x in claims if x["id"] in ctl["expected"]]
        controls.append({"id": ctl["id"], "case": ctl["case"], "checks": checks,
                         "status": "AGREES" if checks and all(c["agrees"] for c in checks) else
                                   "BLOCKED" if any(c["got"] == "BLOCKED" for c in checks) else "DISAGREES"})
        write(cdir / "result.json", controls[-1])
        print(f"   {controls[-1]['status']}", flush=True)

    guard_check("calibration and grader controls")

    grader_costs = [json.loads(f.read_text(encoding="utf-8")).get("total_cost_usd") or 0
                    for f in run_dir.rglob("grader_meta.json")]
    skill_cost = sum(r["skill_run"]["total_cost_usd"] or 0 for r in results)
    cost = {"skill_runs_usd": round(skill_cost, 4), "skill_runs": len(results),
            "grader_calls_usd": round(sum(grader_costs), 4), "grader_calls": len(grader_costs),
            "total_usd": round(skill_cost + sum(grader_costs), 4),
            "basis": "total_cost_usd reported by Claude Code for each call (list prices)"}
    all_checks = [c for r in results for c in r["execution"] + r["structured"] + r.get("provenance", []) + r["commentary"]]
    score = {s: sum(1 for c in all_checks if c["status"] == s) for s in ("PASS", "FAIL", "BLOCKED")}
    summary = {"manifest": {**manifest, "finished": now()}, "regression_tests": reg, "cases": results,
               "harness_contamination": guard["entries"], "cost": cost,
               "calibrations": calibrations, "grader_controls": controls, "score": {**score, "total": len(all_checks),
               "cases_passed": sum(1 for r in results if r["status"] == "PASS"), "cases_total": len(results)}}
    write(run_dir / "results.json", summary)
    write(run_dir / "report.md", render_report(summary))
    print(f"\nscore: {score['PASS']}/{len(all_checks)} checks PASS, {score['FAIL']} FAIL, {score['BLOCKED']} BLOCKED | "
          f"cases {summary['score']['cases_passed']}/{len(results)} PASS | harness contamination: "
          f"{len(guard['entries']) or 'none'} | cost ${cost['total_usd']:.2f}\nreport: {rel(run_dir / 'report.md')}")
    # 1 = a skill/eval FAIL; 3 = run contaminated (results not trustworthy as-is); 2 = BLOCKED only; 0 = clean pass
    sys.exit(1 if score["FAIL"] else 3 if guard["entries"] else 2 if score["BLOCKED"] else 0)


def render_report(s):
    m, sc = s["manifest"], s["score"]
    out = [f"# Evaluation report: run {m['run_id']}", "",
           f"- Git HEAD `{m['git_head']}`; working tree changes at start: {len(m['git_dirty'])} path(s)",
           f"- Claude Code `{m['claude_cli']}`; skill model `{m['skill_model']}`; grader model `{m['grader_model']}`",
           f"- Golden facts consistent with workbooks: **{m['facts_consistent_with_workbooks']}**",
           f"- Started {m['started']}, finished {m['finished']}", "",
           "## Summary", "",
           f"**Checks: {sc['PASS']}/{sc['total']} PASS, {sc['FAIL']} FAIL, {sc['BLOCKED']} BLOCKED. "
           f"Cases: {sc['cases_passed']}/{sc['cases_total']} PASS.**", "",
           f"Regression tests (extractor layer): **{s['regression_tests']['summary']}**", "",
           "**Harness contamination:** " + ("none (no file outside evals/runs/ changed during the run)"
                                             if not s.get("harness_contamination") else
                                             f"{len(s['harness_contamination'])} change(s); results below are not trustworthy as-is"),
           ""]
    out += [f"- `{e['message']}`" for e in s.get("harness_contamination", [])]
    if s.get("cost"):
        c = s["cost"]
        out += ["", f"Cost: ${c['total_usd']:.2f} total = ${c['skill_runs_usd']:.2f} for {c['skill_runs']} skill runs + "
                    f"${c['grader_calls_usd']:.2f} for {c['grader_calls']} grader calls ({c['basis']}).", ""]
    out += ["| Case | Status | Exec | Structured | Provenance | Commentary | Turns | Cost $ |", "|---|---|---|---|---|---|---:|---:|"]
    for r in s["cases"]:
        cnt = lambda xs: f"{sum(x['status'] == 'PASS' for x in xs)}/{len(xs)}" if xs else "n/a"
        out.append(f"| `{r['id']}` | **{r['status']}** | {cnt(r['execution'])} | {cnt(r['structured'])} | "
                   f"{cnt(r.get('provenance', []))} | "
                   f"{cnt(r['commentary'])} | {r['skill_run']['num_turns']} | {r['skill_run']['total_cost_usd'] or 0:.2f} |")
    out.append("")
    for r in s["cases"]:
        out += [f"## {r['id']}: {r['status']}", "", r["title"], "",
                f"Skill run: model `{r['skill_run']['model_reported']}`, {r['skill_run']['num_turns']} turns, "
                f"{r['skill_run']['elapsed_s']} s.", ""]
        bad = [x for x in r["execution"] if x["status"] != "PASS"]
        out.append("Execution: " + ("all PASS" if not bad else "; ".join(f"{x['id']} {x['status']}: {x['desc']} ({x['detail']})" for x in bad)))
        out += ["", "| Structured | Status | Expected | Actual | Source |", "|---|---|---|---|---|"]
        for x in r["structured"]:
            src = x.get("source")
            src = f"{src['sheet']}!{','.join(src['cells'])}" if isinstance(src, dict) else (src or "")
            out.append(f"| {x['id']} {x['desc']} | {x['status']} | {_short(x.get('expected'))} | "
                       f"{_short(x.get('actual', x.get('error')))} | {src} |")
        for x in r.get("provenance", []):
            out += ["", f"Number provenance (P1): **{x['status']}**, {x['detail']}."]
            out += [f"- UNMATCHED `{u['text']}` in: \"{u['sentence']}\"" for u in x["unmatched"]]
        if r["commentary"]:
            out += ["", "| Claim | Kind | Status | Grader evidence |", "|---|---|---|---|"]
            for x in r["commentary"]:
                out.append(f"| {x['id']}: {x['claim']} | {x['kind']} | **{x['status']}** | {x['evidence'].replace('|', '/')} |")
        out.append("")
    if s["calibrations"]:
        out += ["## Calibration (frozen Task 2 artifact; not in the score)", ""]
        for c in s["calibrations"]:
            out += [f"`{c['case']}` on `{c['artifact']}`: **{c['status']}**", "", "| Claim | Status | Evidence |", "|---|---|---|"]
            out += [f"| {x['id']} ({x['kind']}) | {x['status']} | {x['evidence'].replace('|', '/')} |" for x in c["commentary"]]
            out.append("")
    if s.get("grader_controls"):
        out += ["## Grader negative controls (synthetic text; validates the grader, not in the score)", "",
                "| Control | Rule | Expected | Grader | Agrees | Evidence |", "|---|---|---|---|---|---|"]
        for c in s["grader_controls"]:
            for x in c["checks"]:
                out.append(f"| {c['id']} | {x['id']} | {x['expected']} | {x['got']} | {'yes' if x['agrees'] else '**NO**'} | "
                           f"{x['evidence'].replace('|', '/')} |")
        out.append("")
    return "\n".join(out) + "\n"


def _short(v):
    t = json.dumps(v, default=str) if not isinstance(v, str) else v
    return (t[:90] + "…") if len(t) > 90 else t


if __name__ == "__main__":
    main()
