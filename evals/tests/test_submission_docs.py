"""Tests for scripts/build_submission.py and the generated files in submission/ (no network, no Claude).

The key guard: every submission/Task 3.N.md must equal a fresh render of evals/goldens/cases.json, so the case
files can never drift from the single source of truth. If this fails, run: python scripts/build_submission.py
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import build_submission as b  # noqa: E402


class Task3CaseFilesMatchCasesJson(unittest.TestCase):
    def test_each_case_file_equals_a_fresh_render(self):
        cases, facts = b.load_cases(), b.load_facts()
        for n, case in b.case_files(cases):
            path = b.SUBMISSION / f"Task 3.{n}.md"
            self.assertTrue(path.is_file(), f"{path.name} missing; run python scripts/build_submission.py")
            self.assertEqual(path.read_text(encoding="utf-8"), b.case_doc(n, case, cases, facts),
                             f"{path.name} no longer matches cases.json; run python scripts/build_submission.py")

    def test_no_missing_or_extra_case_files(self):
        expected = {f"Task 3.{n}.md" for n, _ in b.case_files(b.load_cases())}
        actual = {p.name for p in b.SUBMISSION.glob("Task 3.*.md")}
        self.assertEqual(actual, expected)

    def test_mapping_is_case_order_a_to_h(self):
        letters = [case["id"].split("_", 1)[0] for _, case in b.case_files(b.load_cases())]
        self.assertEqual(letters, list("abcdefgh"))


try:
    b.pdf_renderer()
    HAVE_REPORTLAB = True
except ValueError:
    HAVE_REPORTLAB = False


@unittest.skipUnless(HAVE_REPORTLAB, "ReportLab not installed (skill requirements.txt)")
class Task2PdfMatchesItsSource(unittest.TestCase):
    def test_committed_pdf_equals_a_fresh_render_of_the_task2_source(self):
        response = (b.SUBMISSION / "Task 2 response.md").read_text(encoding="utf-8")
        source = re.search(r"\| Source report \| `([^`]+)`", response).group(1)
        info = b.report_info(b.REPO / source)
        with tempfile.TemporaryDirectory() as d:
            fresh = b.build_task2_pdf(info, target=Path(d) / "fresh.pdf")
            self.assertEqual(b.TASK2_PDF.read_bytes(), fresh.read_bytes(),
                             "submission/Task 2 report.pdf is stale; run scripts/build_submission.py")


class PassRates(unittest.TestCase):
    def test_only_executed_checks_count(self):
        self.assertEqual(b.rate(["PASS", "FAIL", "SKIP", None, "NOT RUN", "BLOCKED", "UNSTABLE"]), (1, 4))
        self.assertEqual(b.fmt_rate([]), "none executed")
        self.assertEqual(b.fmt_rate(["PASS", "PASS", "FAIL"]), "2/3 (67%)")

    def test_task3_response_total_matches_run_score(self):
        run_dir, current = b.default_run()
        score = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))["score"]
        doc = b.run_doc(run_dir, current)
        self.assertIn(f"**{score['PASS']}/{score['total']} (", doc)


def fake_report(folder, name, generated_at, complete=True):
    md = Path(folder) / f"{name}-trends.md"
    md.write_text("# r\n" + ("- bullet\n" if complete else f"{b.NARRATIVE_MARKER} fill me -->\n"), encoding="utf-8")
    md.with_suffix(".json").write_text(json.dumps({"meta": {
        "generated_at": generated_at, "source_file": r"C:\Users\someone\data\Book.xlsx", "company": "X",
        "latest_month": "Jun 2026", "ttm_window": "Jul 2025 - Jun 2026", "ttm_available": True, "months": ["2026-06"]}}),
        encoding="utf-8")
    return md


class Task2Source(unittest.TestCase):
    def test_picks_newest_complete_and_skips_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            fake_report(d, "old", "2026-10-12T00:00:00+00:00")
            fake_report(d, "newer-but-empty", "2026-10-14T00:00:00+00:00", complete=False)
            fake_report(d, "new", "2026-10-13T00:00:00+00:00")
            pick = b.choose_task2(b.task2_candidates([d]), existing_at=None)
            self.assertEqual(pick["md_path"].name, "new-trends.md")

    def test_never_downgrades_to_an_older_report(self):
        with tempfile.TemporaryDirectory() as d:
            fake_report(d, "old", "2026-10-12T00:00:00+00:00")
            with self.assertRaises(ValueError):
                b.choose_task2(b.task2_candidates([d]), existing_at="2026-10-13T00:00:00+00:00")

    def test_explicit_source_must_be_complete(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                b.choose_task2([], None, explicit=fake_report(d, "empty", "2026-10-13T00:00:00+00:00", complete=False))

    def test_header_has_file_name_only_and_model_not_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            doc = b.task2_doc(b.report_info(fake_report(d, "r", "2026-10-13T00:00:00+00:00")))
        self.assertIn("`Book.xlsx`", doc)
        self.assertNotIn("someone", doc)
        self.assertIn("model not recorded", doc)


def evidence(**over):
    ev = {"run_at": "2026-10-13T00:00:00+00:00", "client": "c", "tools": ["get_company_info", "search_accounts"],
          "company": {"name": "Sandbox Co", "country": "US"},
          "net_income_latest_complete_month": {"month": "Sep 2026", "start": "2026-09-01", "end": "2026-09-30", "value": 12.5},
          "django_test": {"realm_hint": "123456789012345"},
          "results": [{"status": "PASS", "check": c, "detail": ""} for c in (
              "get_company_info", "get_profit_and_loss (12 months, by month)", "No create/update/delete tools registered",
              "Write tool 'create_customer' rejected")]}
    ev.update(over)
    return ev


class Task1Response(unittest.TestCase):
    def test_failed_run_is_rejected(self):
        with self.assertRaises(ValueError):
            b.task1_doc(evidence(), smoke_exit=1)
        with self.assertRaises(ValueError):
            b.task1_doc(evidence(net_income_latest_complete_month=None), smoke_exit=0)

    def test_realm_never_more_than_four_characters(self):
        doc = b.task1_doc(evidence(), smoke_exit=0)
        self.assertIn("1234…", doc)
        self.assertNotIn("12345", doc)
        self.assertIn("Sep 2026", doc)

    def test_django_skip_is_explained(self):
        ev = evidence()
        ev["results"].append({"status": "SKIP", "check": "Django /api/qbo/<slug>/test", "detail": "checked out"})
        self.assertIn(b.DJANGO_SKIP_REASON, b.task1_doc(ev, smoke_exit=0))
        self.assertNotIn(b.DJANGO_SKIP_REASON, b.task1_doc(evidence(), smoke_exit=0))

    def test_previous_file_kept_when_build_fails(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "Task 1 response.md"
            target.write_text("previous", encoding="utf-8")

            def failing():
                raise ValueError("smoke test failed")
            with self.assertRaises(ValueError):
                b.publish(target, failing)
            self.assertEqual(target.read_text(encoding="utf-8"), "previous")
            self.assertEqual([p.name for p in Path(d).iterdir()], ["Task 1 response.md"])   # no temp file left


if __name__ == "__main__":
    unittest.main(verbosity=2)
