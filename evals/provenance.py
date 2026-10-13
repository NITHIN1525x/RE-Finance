#!/usr/bin/env python
"""Number-provenance check: every number cited in a run's commentary must come from THAT run's own output.

Deterministic, no model calls. For each number in the commentary:
  - IGNORED  if an explicit rule below says it is not a financial figure (years, dates, counts, references);
  - MATCHED  if some value in the run's own *-trends.json (any numeric field, any depth) or *-trends.md (any
             number in the report text, EXCLUDING the commentary itself) is consistent with it under the
             rounding policy. The skill writes its commentary into the report, so without that exclusion every
             commentary number would match itself and the check could never fail (DECISIONS_LOG D-57/D-58);
  - UNMATCHED otherwise. Any UNMATCHED number fails the check, reported with the sentence it appeared in.

Matching rule (the rounding policy from goldens/cases.json, made precise for a large candidate pool):
  the stated number x must be a plausible rounding of a candidate v at the precision x is written in,
  i.e. ||x| - |v|| <= half a unit of x's last significant digit (1,045 -> 0.5; 700 -> 50; 70.2 -> 0.05;
  1.87M -> 5,000), AND inside the policy band (<= 5% of |v| for amounts, <= 0.5 percentage points for
  percentages). Magnitudes are compared because prose carries the sign in words ("down 215,543"); whether a
  direction is right is the grader's job, not this check's.

Usage:  python evals/provenance.py <run_dir> [--out FILE]      (run_dir = evals/runs/<id> or evals/baseline/<id>)
"""
import argparse
import json
import re
import sys
from pathlib import Path

POLICY_REL = 0.05      # amounts: within 5% relative
POLICY_PP = 0.5        # percentages: within 0.5 percentage points

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
COUNT_NOUNS = (r"(?:months?|weeks?|days?|years?|quarters?|lines?|accounts?|streams?|rows?|checks?|categor(?:y|ies)|"
               r"items?|sections?|subtotals?|mismatch(?:es)?|cases?|bullets?|flags?|warnings?|columns?|groups?|"
               r"times|periods?|entries|records?|companies|clients?|consecutive)")
# The only words allowed between a count and its noun. Deliberately short: anything else means the number is checked.
COUNT_DESCRIPTORS = (r"(?:consecutive|subtotal|expense|revenue|negative|positive|calendar|detail|summary|separate|"
                     r"new|vanished|flagged|unmapped|zero|non-zero|prior|full|reporting|data-quality)")

# Explicit, documented ignore rules. Each is (id, description, test(match, text) -> bool).
IGNORE_RULES = [
    ("year", "4-digit year 1990-2100 written without separators, sign, decimals or unit (e.g. 2026)",
     lambda m, t: _plain_int(m) and 1990 <= int(m.group("int")) <= 2100),
    ("date_day", "day of month next to a month name (e.g. 'Oct 1-12', '30 Jun 2026', 'Jun 30')",
     lambda m, t: _plain_int(m) and 1 <= int(m.group("int")) <= 31 and (
         re.search(rf"{MONTHS}\s*$", t[max(0, m.start() - 12):m.start()], re.I) is not None or
         re.match(rf"\s*(?:[-–]\s*\d{{1,2}},?\s*)?{MONTHS}", t[m.end():m.end() + 14], re.I) is not None or
         re.search(rf"{MONTHS}\s+\d{{1,2}}\s*[-–]\s*$", t[max(0, m.start() - 12):m.start()], re.I) is not None)),
    ("count", "an integer followed by a count noun, optionally with ONE whitelisted descriptor in between "
              "(e.g. '6 consecutive months', '15 subtotal rows', '4 expense lines'). Not 'N this month': "
              "words like this/last/per/a are not descriptors, so '400 this month' is checked as a figure",
     lambda m, t: _plain_int(m) and re.match(rf"\s+(?:{COUNT_DESCRIPTORS}\s+)?{COUNT_NOUNS}\b", t[m.end():m.end() + 40],
                                            re.I) is not None),
    ("n_of_m", "'N of M' counts (e.g. '2 of 18 months', '17 of 18')",
     lambda m, t: _plain_int(m) and (re.match(r"\s+of\s+\d", t[m.end():m.end() + 8]) is not None or
                                    re.search(r"\d+\s+of\s+$", t[max(0, m.start() - 10):m.start()]) is not None)),
    ("span", "a period length written as 'N-month' / 'N-day' / 'N-year' (e.g. 'prior 6-month average')",
     lambda m, t: _plain_int(m) and re.match(r"-(?:month|week|day|year|quarter)\b", t[m.end():m.end() + 9], re.I) is not None),
    ("reference", "a section/step/decision reference (e.g. 'section 8', '§8', 'D-04')",
     lambda m, t: re.search(r"(?:section|§|step|table|D-)\s*$", t[max(0, m.start() - 9):m.start()], re.I) is not None),
]

NUM_RE = re.compile(
    r"(?<![\w.])(?<![A-Za-z]-)(?P<open>\()?(?P<sign>[+\-−])?(?P<cur>\$)?"   # (?<![A-Za-z]-): skip ids like D-04
    r"(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?P<dec>\.\d+)?"
    r"(?P<suffix>\s?(?:%|pp\b|percentage points?\b|[kK]\b|M\b|million\b|bn\b|billion\b))?(?P<close>\))?"
    r"(?![\w])")
SCALE = {"k": 1e3, "K": 1e3, "M": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}


def _plain_int(m):
    return m.group("dec") is None and m.group("suffix") is None and "," not in m.group("int") and m.group("sign") is None \
        and m.group("open") is None


def parse(m):
    """-> (magnitude, half_unit, kind) for a regex match."""
    digits = m.group("int").replace(",", "")
    dec = m.group("dec") or ""
    suffix = (m.group("suffix") or "").strip()
    value = float(digits + dec)
    if dec:
        unit = 10 ** -(len(dec) - 1)
    else:
        trailing = len(digits) - len(digits.rstrip("0")) if digits.strip("0") else 0
        unit = 10 ** trailing
    kind = "percent" if suffix in ("%", "pp") or suffix.startswith("percentage") else "amount"
    scale = SCALE.get(suffix, 1)
    return value * scale, unit * scale / 2, kind


def numbers_in(text):
    for m in NUM_RE.finditer(text):
        yield m


def sentence_of(text, pos):
    """The sentence (or bullet) containing position pos."""
    starts = [0] + [x.end() for x in re.finditer(r"(?<=[.!?])\s+(?=[A-Z(*])|\n", text)]
    start = max(s for s in starts if s <= pos)
    end_m = re.compile(r"(?<=[.!?])\s+(?=[A-Z(*])|\n").search(text, pos)
    return " ".join(text[start:end_m.start() if end_m else len(text)].split())


COMMENTARY_HEADING = "## 1. Commentary (draft)"   # the skill's report layout (also used by run_evals.commentary_of)
FLAGS_HEADING = "### Flags raised"                # engine-written flags start here: deterministic, so they stay


def without_commentary(report_md, commentary=None):
    """The report with the model-written commentary removed, so it can't vouch for its own numbers (D-58).

    Removes the text between the commentary heading and the engine's flags heading, and also any report LINE that
    is identical to a commentary line (covers a report laid out differently). Whole lines only, so engine sentences
    that merely contain a commentary phrase stay in the pool."""
    text = report_md or ""
    start = text.find(COMMENTARY_HEADING)
    if start >= 0:
        end = text.find(FLAGS_HEADING, start)
        text = text[:start + len(COMMENTARY_HEADING)] + "\n\n" + (text[end:] if end >= 0 else "")
    own = {line.strip() for line in (commentary or "").splitlines() if line.strip()}
    if own:
        text = "\n".join(line for line in text.splitlines() if line.strip() not in own)
    return text


def candidates(analysis, report_md):
    """All numbers the run itself produced: every numeric JSON leaf, plus every number in the report text.
    Callers pass the report WITHOUT the commentary (see without_commentary)."""
    out = []

    def walk(x, path):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            out.append((abs(float(x)), "json:" + path))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
    walk(analysis, "")
    for m in numbers_in(report_md):
        value, _, _ = parse(m)
        out.append((value, f"report:'{report_md[max(0, m.start() - 25):m.end() + 5].strip()}'"))
    return out


def check(commentary, analysis, report_md):
    """-> {'status': PASS|FAIL, 'numbers': [...]} for one commentary."""
    pool = candidates(analysis, without_commentary(report_md, commentary))
    findings = []
    for m in numbers_in(commentary):
        text = m.group(0)
        rule = next((rid for rid, _, test in IGNORE_RULES if test(m, commentary)), None)
        entry = {"text": text.strip(), "sentence": sentence_of(commentary, m.start())}
        if rule:
            findings.append({**entry, "status": "IGNORED", "rule": rule})
            continue
        value, half_unit, kind = parse(m)
        band = POLICY_PP if kind == "percent" else None
        best = None
        for v, src in pool:
            diff = abs(value - v)
            within_band = diff <= POLICY_PP if band else diff <= POLICY_REL * abs(v) + 1e-9
            if diff <= half_unit + 1e-9 and within_band and (best is None or diff < best[0]):
                best = (diff, v, src)
        if best:
            findings.append({**entry, "status": "MATCHED", "value": value, "matched_value": round(best[1], 6),
                             "source": best[2]})
        else:
            findings.append({**entry, "status": "UNMATCHED", "value": value, "kind": kind})
    unmatched = [f for f in findings if f["status"] == "UNMATCHED"]
    return {"status": "FAIL" if unmatched else "PASS", "unmatched": len(unmatched),
            "matched": sum(f["status"] == "MATCHED" for f in findings),
            "ignored": sum(f["status"] == "IGNORED" for f in findings), "numbers": findings}


def check_run_dir(run_dir):
    """Apply the check to every case folder in a saved run (commentary.md + skill_output/*-trends.{json,md})."""
    results = {}
    for case_dir in sorted(p for p in Path(run_dir).iterdir() if (p / "skill_output").is_dir()):
        jsons = sorted((case_dir / "skill_output").glob("*-trends.json"))
        mds = sorted((case_dir / "skill_output").glob("*-trends.md"))
        comm = (case_dir / "commentary.md").read_text(encoding="utf-8") if (case_dir / "commentary.md").is_file() else ""
        if len(jsons) != 1 or len(mds) != 1 or not comm.strip() or comm.strip() == "(no commentary)":
            results[case_dir.name] = {"status": "BLOCKED", "reason": "missing saved commentary or skill output"}
            continue
        results[case_dir.name] = check(comm, json.loads(jsons[0].read_text(encoding="utf-8")),
                                       mds[0].read_text(encoding="utf-8"))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--out")
    args = ap.parse_args()
    res = check_run_dir(args.run_dir)
    for case, r in res.items():
        print(f"{case}: {r['status']}" + (f" (matched {r['matched']}, ignored {r['ignored']}, UNMATCHED {r['unmatched']})"
                                          if "numbers" in r else f" ({r.get('reason')})"))
        for f in r.get("numbers", []):
            if f["status"] == "UNMATCHED":
                print(f"   UNMATCHED {f['text']!r}: {f['sentence']}")
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    sys.exit(1 if any(r["status"] == "FAIL" for r in res.values()) else 0)


if __name__ == "__main__":
    main()
