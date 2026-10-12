#!/usr/bin/env python
"""Compare two eval runs case by case and check by check (verdicts, structured actual values, check sets, cost).

Usage:  python evals/compare_runs.py <old_run_dir> <new_run_dir>
Prints:
  - per case: status old -> new; checks added/removed; verdict flips; structured checks whose ACTUAL value changed
  - P1 provenance (for an old run without P1, uses <old_run_dir>/../provenance_addendum_v1.json if present)
  - run cost and score for both
Exit 0 always (it reports; the human decides whether a difference is expected).
"""
import json
import sys
from pathlib import Path


def load(run_dir):
    return json.loads((Path(run_dir) / "results.json").read_text(encoding="utf-8"))


def checks(case):
    out = {}
    for group in ("execution", "structured", "provenance", "commentary"):
        for c in case.get(group, []):
            out[f"{group}:{c['id']}"] = c
    return out


def main(old_dir, new_dir):
    old, new = load(old_dir), load(new_dir)
    addendum = Path(old_dir).parent / "provenance_addendum_v1.json"
    old_p1 = json.loads(addendum.read_text(encoding="utf-8")) if addendum.is_file() else {}
    new_cases = {c["id"]: c for c in new["cases"]}
    print(f"OLD {Path(old_dir).name}: score {old['score']['PASS']}/{old['score']['total']}, "
          f"cases {old['score']['cases_passed']}/{old['score']['cases_total']}, cost ${old.get('cost', {}).get('total_usd', 'n/a')}")
    print(f"NEW {Path(new_dir).name}: score {new['score']['PASS']}/{new['score']['total']}, "
          f"cases {new['score']['cases_passed']}/{new['score']['cases_total']}, cost ${new.get('cost', {}).get('total_usd', 'n/a')}, "
          f"contamination: {len(new.get('harness_contamination', [])) or 'none'}")
    changed_cases = []
    for oc in old["cases"]:
        nc = new_cases.get(oc["id"])
        if nc is None:
            print(f"\n{oc['id']}: REMOVED in new run")
            changed_cases.append(oc["id"])
            continue
        a, b = checks(oc), checks(nc)
        added, removed = sorted(set(b) - set(a)), sorted(set(a) - set(b))
        flips = [f"{k} {a[k]['status']}->{b[k]['status']}" for k in sorted(set(a) & set(b)) if a[k]["status"] != b[k]["status"]]
        value_changes = [f"{k}: {json.dumps(a[k].get('actual'), default=str)[:80]} -> {json.dumps(b[k].get('actual'), default=str)[:80]}"
                         for k in sorted(set(a) & set(b)) if k.startswith("structured:")
                         and json.dumps(a[k].get("actual"), sort_keys=True, default=str) != json.dumps(b[k].get("actual"), sort_keys=True, default=str)]
        p1_old = old_p1.get(oc["id"], {}).get("status", "n/a (no P1 in old run)") if "provenance:P1" not in a else a["provenance:P1"]["status"]
        p1_new = b.get("provenance:P1", {}).get("status", "n/a")
        # P1 becoming live (old run predates it) is expected everywhere; it is shown above but is not a "difference".
        new_only_p1 = "provenance:P1" not in a
        added_real = [k for k in added if not (new_only_p1 and k == "provenance:P1")]
        differs = oc["status"] != nc["status"] or added_real or removed or flips or value_changes
        if differs:
            changed_cases.append(oc["id"])
        print(f"\n{oc['id']}: {oc['status']} -> {nc['status']}{'' if differs else '  (no change in verdicts or structured values)'}")
        print(f"   P1 provenance: {p1_old} -> {p1_new}")
        for label, items in (("checks added", added), ("checks removed", removed), ("verdict flips", flips),
                             ("structured value changes", value_changes)):
            if items:
                print(f"   {label}:")
                for it in items:
                    print(f"      {it}")
    print(f"\ncases with any difference (excluding P1 being newly live): {changed_cases or 'none'}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
