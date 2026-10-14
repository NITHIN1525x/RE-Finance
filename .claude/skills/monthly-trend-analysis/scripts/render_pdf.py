#!/usr/bin/env python
"""Optional printable PDF of a monthly trend analysis, built from the skill's own output (OFF by default).

Usage (repo root, with the skill's venv):
    python .claude/skills/monthly-trend-analysis/scripts/render_pdf.py <...-trends.json> [--out-dir DIR]

Reads the *-trends.json (every number) and the *-trends.md next to it (the draft commentary and the reviewer
checklist), and writes <same name>.pdf into --out-dir, by default demo-output/. It never writes anywhere else unless
you pass that folder, and never writes over its inputs. run_trends.py is unchanged and never produces a PDF.

Exit codes: 0 written, 1 bad input, 2 ReportLab is not installed (pip install -r requirements.txt).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_path", help="the *-trends.json written by run_trends.py")
    ap.add_argument("--out-dir", default="demo-output", help="output folder (default: demo-output)")
    args = ap.parse_args(argv)

    try:
        from trends.pdf import render_pdf
    except ImportError as exc:
        print(f"render_pdf: ReportLab is missing ({exc}). Install: pip install -r "
              f".claude/skills/monthly-trend-analysis/requirements.txt", file=sys.stderr)
        return 2

    src = Path(args.json_path)
    if not src.is_file() or not src.name.endswith("-trends.json"):
        print(f"render_pdf: expected a *-trends.json file, got {src}", file=sys.stderr)
        return 1
    analysis = json.loads(src.read_text(encoding="utf-8"))
    md_path = src.with_suffix(".md")
    report_md = md_path.read_text(encoding="utf-8") if md_path.is_file() else None
    out = Path(args.out_dir) / src.with_suffix(".pdf").name
    if out.resolve() in (src.resolve(), md_path.resolve()):
        print("render_pdf: refusing to write over an input file", file=sys.stderr)
        return 1
    render_pdf(analysis, report_md, out)
    print(f"PDF: {out}" + ("" if report_md else "  (no .md beside the JSON: commentary and checklist marked unavailable)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
