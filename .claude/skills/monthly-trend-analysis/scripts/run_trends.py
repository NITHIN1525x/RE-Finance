#!/usr/bin/env python
"""Monthly trend analysis for a QuickBooks-Online-style Excel export (Income Statement [+ Balance Sheet]).

Usage:
    python run_trends.py [WORKBOOK] [--out-dir DIR] [--months N] [--company NAME] [--config FILE]

    WORKBOOK  defaults to the single .xlsx in the repository's data/ folder.
Writes <out-dir>/<company>-<YYYY-MM>-trends.json (the analysis contract) and ...-trends.md (draft report),
then prints a short summary. Exit codes: 0 ok, 1 usage/input error, 2 the workbook could not be parsed.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import openpyxl  # noqa: F401
except ImportError:
    skill = HERE.parent
    print("openpyxl is not installed for this Python. Set up the skill's environment once:\n"
          f"  python -m venv \"{skill / '.venv'}\"\n"
          f"  \"{skill / '.venv'}\"/Scripts/python -m pip install -r \"{skill / 'requirements.txt'}\"   "
          "(POSIX: .venv/bin/python)\nthen re-run with that Python.", file=sys.stderr)
    sys.exit(1)

from trends import analysis, mapping, report, workbook  # noqa: E402


def default_workbook():
    """The single .xlsx under the nearest ancestor 'data/' folder (repo convention)."""
    for parent in HERE.parents:
        data = parent / "data"
        if data.is_dir():
            files = sorted(p for p in data.glob("*.xlsx") if not p.name.startswith("~$"))
            if len(files) == 1:
                return files[0]
            if files:
                sys.exit("Several workbooks in data/; pass one explicitly:\n  " + "\n  ".join(str(f) for f in files))
    sys.exit("No workbook given and no single .xlsx found in a data/ folder.")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "company"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("workbook", nargs="?", help="path to the .xlsx export (default: the one in data/)")
    p.add_argument("--out-dir", default="trend-reports", help="output folder (default: ./trend-reports)")
    p.add_argument("--months", type=int, default=6, help="months shown as columns in the wide tables (default 6)")
    p.add_argument("--company", help="override the company name read from the title rows")
    p.add_argument("--config", help="category/threshold config (default: references/category_map.json)")
    args = p.parse_args(argv)

    path = Path(args.workbook) if args.workbook else default_workbook()
    if not path.is_file():
        print(f"Workbook not found: {path}", file=sys.stderr)
        return 1
    config = mapping.load_config(args.config)

    try:
        values_wb, formulas_wb = workbook.load_workbook_pair(path)
        is_values = workbook.find_sheet(values_wb, config["sheets"]["income_statement"]) or values_wb.worksheets[0]
        bs_values = workbook.find_sheet(values_wb, config["sheets"]["balance_sheet"])
        income = workbook.parse_sheet(is_values, formulas_wb[is_values.title], config["header_label"])
        balance = (workbook.parse_sheet(bs_values, formulas_wb[bs_values.title], config["header_label"])
                   if bs_values is not None and bs_values.title != is_values.title else None)
        result = analysis.analyze(income, balance, config, path, args.company)
    except (ValueError, KeyError) as exc:
        print(f"Could not analyse {path.name}: {exc}", file=sys.stderr)
        return 2

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{slug(result['meta']['company'])}-{result['meta']['months'][-1]}-trends"
    (out / f"{stem}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / f"{stem}.md").write_text(report.render(result, args.months), encoding="utf-8")

    m = result["meta"]
    sev = {s: sum(1 for f in result["flags"] if f["severity"] == s) for s in ("high", "medium", "info")}
    bad = [c["check"] for c in result["data_quality"]["checks"] if c["status"] == "mismatch"]
    print(f"Company: {m['company']} | months: {m['month_labels'][0]} - {m['latest_month']} ({len(m['months'])}) "
          f"| balance sheet: {'yes' if result['balance_sheet'] else 'no'}")
    print(f"Flags: {sev['high']} high, {sev['medium']} medium, {sev['info']} info | data-quality mismatches: {len(bad)}")
    print(f"Report: {out / (stem + '.md')}")
    print(f"Data:   {out / (stem + '.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
