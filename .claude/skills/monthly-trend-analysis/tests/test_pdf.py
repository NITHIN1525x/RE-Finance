"""Tests for the optional PDF report (scripts/render_pdf.py, scripts/trends/pdf.py).

The expected values are computed HERE from the JSON with the Markdown report's formatters, independently of the
PDF module's own table-building code, then looked up in the text extracted from the generated PDF.
Needs reportlab (requirements.txt) and pypdf (requirements-dev.txt); skipped with a clear reason otherwise.
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]          # <repo>/.claude/skills/monthly-trend-analysis
sys.path.insert(0, str(SKILL / "scripts"))

try:
    import pypdf
    from trends import pdf as P
    HAVE_PDF = True
except ImportError as exc:  # pragma: no cover
    HAVE_PDF, WHY = False, str(exc)
from trends.report import money, mom_cell, pct  # noqa: E402

import run_trends  # noqa: E402

ABC = next(iter(sorted((REPO / "data").glob("ABC Inc*.xlsx"))), None)
BLUEBIRD = SKILL / "tests" / "test_data" / "bluebird-bakery.xlsx"
NUMBER = re.compile(r"\(?[+\-]?\d[\d,]*(?:\.\d+)?%?\)?")


def norm(text):
    return " ".join(text.split())


def render(workbook, out):
    """Engine run (numbers only) + PDF, both into a temp folder. Returns (analysis, pdf_path, page_texts)."""
    assert run_trends.main([str(workbook), "--out-dir", str(out)]) == 0
    src = next(Path(out).glob("*-trends.json"))
    analysis = json.loads(src.read_text(encoding="utf-8"))
    pdf_path = P.render_pdf(analysis, src.with_suffix(".md").read_text(encoding="utf-8"), Path(out) / "r.pdf")
    pages = [norm(p.extract_text()) for p in pypdf.PdfReader(str(pdf_path)).pages]
    return analysis, pdf_path, pages


def expected_rows(a):
    """{row text as printed} for the revenue-stream and expense-category tables, from the JSON alone."""
    def cells(block, name):
        yoy = pct(block["yoy_pct"]) if block.get("yoy_pct") is not None else "n/a"
        ttm = money(block["ttm"]) if block.get("ttm") is not None else "n/a"
        return norm(" ".join([name, money(block["latest"]), money(block["prior"]), mom_cell(block), yoy, ttm]))
    rows = [cells(s, s["name"]) for s in a["revenue"]["streams"]]
    rows.append(cells(a["revenue"]["total"], "Total revenue"))
    for c in a["operating_expenses"]["categories"]:
        name = c["name"] + (" (non-operating)" if c.get("non_operating") and "non-operating" not in c["name"] else "")
        rows.append(cells(c, name))
    rows.append(cells(a["operating_expenses"]["total"], a["operating_expenses"]["total"]["name"]))
    return rows


@unittest.skipUnless(HAVE_PDF, "reportlab / pypdf not installed: pip install -r requirements.txt -r requirements-dev.txt")
class PdfReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.runs = {}
        for key, wb in (("abc", ABC), ("bluebird", BLUEBIRD)):
            if wb is None:
                continue
            cls.runs[key] = render(wb, Path(cls.tmp.name) / key)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pdf_created_for_both_workbooks(self):
        self.assertEqual(sorted(self.runs), ["abc", "bluebird"])
        for key, (_, path, pages) in self.runs.items():
            self.assertTrue(path.read_bytes().startswith(b"%PDF"), key)
            self.assertTrue(4 <= len(pages) <= 7, f"{key}: {len(pages)} pages")
            self.assertIn("DRAFT for reviewer", pages[0])

    def test_every_table_row_matches_the_json(self):
        for key, (a, _, pages) in self.runs.items():
            text = " ".join(pages)
            for row in expected_rows(a):
                self.assertIn(row, text, f"{key}: row not printed as expected: {row}")

    def test_no_table_number_that_is_not_from_the_json(self):
        for key, (a, _, pages) in self.runs.items():
            page = next(p for p in pages if "Revenue streams" in p and "Operating expenses by category" in p)
            allowed = {tok for row in expected_rows(a) for tok in NUMBER.findall(row)}
            allowed |= {str(len(a["meta"]["months"]))}                                  # "(only 9 months)"
            allowed |= {m.split()[-1] for m in a["meta"]["month_labels"]}                # years in "Latest (Jun 2026)"
            allowed |= {f"{m.split()[-1]})" for m in a["meta"]["month_labels"]}
            allowed |= {str(pages.index(page) + 1)}                                      # the footer's page number
            allowed |= set(NUMBER.findall(Path(a["meta"]["source_file"].replace("\\", "/")).name))   # "(1) (1).xlsx"
            stray = [tok for tok in NUMBER.findall(page) if tok not in allowed]
            self.assertEqual(stray, [], f"{key}: numbers on the tables page that are not from the JSON")

    def test_key_figures_match_the_json(self):
        for key, (a, _, pages) in self.runs.items():
            rev, opex, ni = a["revenue"]["total"], a["operating_expenses"]["total"], a["net_income"]
            for value in (money(rev["latest"]), money(rev["prior"]), mom_cell(rev), money(opex["latest"]),
                          money(ni["latest"]), pct(a["gross_margin"]["monthly"][-1]["gm_pct"], signed=False)):
                self.assertIn(value, pages[0], f"{key}: key figure {value} missing from page 1")

    def test_opex_is_labelled_with_the_engines_field_name(self):
        for key, (a, _, pages) in self.runs.items():
            total = a["operating_expenses"]["total"]
            self.assertEqual(total["name"], "Total operating expenses (as exported)")
            self.assertIn(norm(f"{total['name']} {money(total['latest'])}"), pages[0], key)   # key-figures row
            self.assertNotIn("Operating expenses (as exported)", " ".join(pages).replace(total["name"], ""), key)

    def test_bluebird_says_ttm_is_not_available(self):
        a, _, pages = self.runs["bluebird"]
        text = " ".join(pages)
        self.assertFalse(a["meta"]["ttm_available"])
        self.assertIn("not available (only 9 months)", pages[0])
        self.assertIn("TTM gross margin: not available (only 9 months)", text)
        self.assertNotIn("TTM gross margin %", text)          # no TTM line drawn from missing values

    def test_abc_has_ttm_and_yoy(self):
        a, _, pages = self.runs["abc"]
        self.assertIn(money(a["revenue"]["total"]["ttm"]), pages[0])
        self.assertIn(pct(a["revenue"]["total"]["yoy_pct"]), pages[0])
        self.assertNotIn("not available (only", " ".join(pages))

    def test_symbols_the_builtin_fonts_cannot_draw_are_written_as_text(self):
        for key, (_, _, pages) in self.runs.items():
            text = " ".join(pages)
            self.assertNotIn("→", text, key)
            self.assertNotIn("Δ", text, key)

    def test_reproducible_bytes(self):
        a, path, _ = self.runs["bluebird"]
        again = P.render_pdf(a, None, Path(self.tmp.name) / "again.pdf")
        md_less = P.render_pdf(a, None, Path(self.tmp.name) / "again2.pdf")
        self.assertEqual(again.read_bytes(), md_less.read_bytes())

    def test_commentary_is_copied_verbatim_and_labelled(self):
        src = REPO / "trend-reports" / "abc-inc-2026-06-trends.json"
        md = src.with_suffix(".md").read_text(encoding="utf-8")
        out = P.render_pdf(json.loads(src.read_text(encoding="utf-8")), md, Path(self.tmp.name) / "c.pdf")
        text = norm(" ".join(p.extract_text() for p in pypdf.PdfReader(str(out)).pages))
        self.assertIn("DRAFT commentary for reviewer", text)
        first_bullet = md.split("## 1. Commentary (draft)", 1)[1].strip().splitlines()[0]
        words = norm(re.sub(r"[*`]", "", first_bullet[2:]))[:80]
        self.assertIn(words, text)

    def test_numbers_only_report_says_no_commentary(self):
        _, _, pages = self.runs["abc"]
        self.assertIn("No commentary has been written for this report yet", " ".join(pages))

    def test_default_output_folder_is_demo_output(self):
        import render_pdf
        src = next((Path(self.tmp.name) / "bluebird").glob("*-trends.json"))
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as work:
            os.chdir(work)
            try:
                self.assertEqual(render_pdf.main([str(src)]), 0)
                self.assertTrue((Path(work) / "demo-output" / src.with_suffix(".pdf").name).is_file())
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
