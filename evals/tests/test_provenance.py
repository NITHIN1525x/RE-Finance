"""Unit tests for the number-provenance check (evals/provenance.py). Deterministic, no Claude calls.

Run:  .claude/skills/monthly-trend-analysis/.venv/Scripts/python -m unittest discover -s evals/tests -v
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))
import provenance as P  # noqa: E402

BASELINE_CASE = EVALS / "baseline" / "history" / "v1" / "clean-run-20261012" / "a_abc_jun2026_core"   # frozen v1 artifacts


def statuses(text, pool_values=(), report=""):
    analysis = {"values": list(pool_values)}
    return [(f["text"], f["status"], f.get("rule")) for f in P.check(text, analysis, report)["numbers"]]


class ParsingTests(unittest.TestCase):
    def first(self, text):
        return P.parse(next(P.numbers_in(text)))

    def test_amounts_and_implied_precision(self):
        self.assertEqual(self.first("(330,756)"), (330756.0, 0.5, "amount"))
        self.assertEqual(self.first("700"), (700.0, 50.0, "amount"))          # 'roughly 700' -> +/-50
        self.assertEqual(self.first("1,250"), (1250.0, 5.0, "amount"))
        self.assertEqual(self.first("2,200.00"), (2200.0, 0.005, "amount"))

    def test_percentages_and_scale_suffixes(self):
        self.assertEqual(self.first("-6.0%"), (6.0, 0.05, "percent"))
        self.assertEqual(self.first("+3.1 pp"), (3.1, 0.05, "percent"))
        value, half, kind = self.first("1.87M")
        self.assertAlmostEqual(value, 1_870_000)
        self.assertAlmostEqual(half, 5_000)

    def test_numbers_inside_identifiers_are_not_extracted(self):
        self.assertEqual([m.group(0) for m in P.numbers_in("Q3 D-04 X5 v2 S1")], [])


class IgnoreRuleTests(unittest.TestCase):
    def rules(self, text):
        return [(t, r) for t, s, r in statuses(text) if s == "IGNORED"]

    def test_year(self):
        self.assertIn(("2026", "year"), self.rules("In Jun 2026 revenue was flat."))

    def test_dates(self):
        self.assertEqual(self.rules("covering Oct 1-12, 2026"), [("1", "date_day"), ("12", "date_day"), ("2026", "year")])
        self.assertIn(("30", "date_day"), self.rules("as at 30 Jun 2026"))

    def test_counts_and_spans(self):
        self.assertIn(("6", "count"), self.rules("negative for 6 consecutive months"))
        self.assertIn(("15", "count"), self.rules("15 subtotal rows were checked"))
        self.assertEqual(self.rules("posted in only 2 of 18 months"), [("2", "n_of_m"), ("18", "count")])
        self.assertIn(("6", "span"), self.rules("vs the prior 6-month average"))

    def test_references(self):
        self.assertIn(("8", "reference"), self.rules("see section 8 for details"))

    def test_financial_figures_are_never_ignored(self):
        # A plain integer with no count noun / date / reference context must be CHECKED, not ignored.
        self.assertEqual(statuses("costs rose by 400 this month"), [("400", "UNMATCHED", None)])


class MatchingTests(unittest.TestCase):
    def test_exact_and_honest_rounding_match(self):
        pool = [195898.16, -5.9768, 70.1516]
        self.assertTrue(all(s == "MATCHED" for _, s, _ in statuses("195,898, -6.0%, 70.2%, about 196,000", pool)))

    def test_721_roughly_700_is_within_the_rounding_policy(self):
        # Ruling D-40: 700 vs 721.0033 is -2.9%, inside the 5% band, and within the +/-50 precision of '700'.
        self.assertEqual(statuses("averaging roughly 700-1,250", [721.0033, 1250.0])[:2],
                         [("700", "MATCHED", None), ("1,250", "MATCHED", None)])

    def test_wrong_precision_fails(self):
        # 195,900.00 claims cent precision, but the true value is 195,898.16.
        self.assertEqual(statuses("Revenue was 195,900.00.", [195898.16])[0][1], "UNMATCHED")

    def test_rounding_beyond_policy_fails(self):
        # 300,000 is within its own precision (+/-50,000) of 330,756, but 9.3% off: outside the 5% policy band.
        self.assertEqual(statuses("a loss of about 300,000", [330756.08])[0][1], "UNMATCHED")

    def test_percentage_band(self):
        self.assertEqual(statuses("down 6%", [5.4])[0][1], "UNMATCHED")       # 0.6 > half-unit 0.5
        self.assertEqual(statuses("down 6%", [5.6])[0][1], "MATCHED")

    def test_magnitudes_are_compared_sign_in_words(self):
        self.assertEqual(statuses("cash fell 215,543", [-215543.33])[0][1], "MATCHED")

    def test_report_text_counts_as_output(self):
        self.assertEqual(statuses("averaged 721", [], report="it averaged 721 over the prior 6 months")[0][1], "MATCHED")

    def test_unmatched_is_reported_with_its_sentence(self):
        r = P.check("Revenue rose. Margin hit 61.7% in June. Costs fell.", {"x": [70.15]}, "")
        bad = [f for f in r["numbers"] if f["status"] == "UNMATCHED"]
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual([(f["text"], f["sentence"]) for f in bad], [("61.7%", "Margin hit 61.7% in June.")])

    def test_known_limitation_round_numbers_can_collide(self):
        # Documented limitation (DECISIONS_LOG D-44): a ROUND number can match an unrelated value in the output.
        # Provenance proves a figure exists in the output, not that it is attached to the right label.
        self.assertEqual(statuses("software rose about 2,000", [2000.0])[0][1], "MATCHED")


@unittest.skipUnless(BASELINE_CASE.is_dir(), "baseline artifacts not present")
class BaselineArtifactTests(unittest.TestCase):
    def setUp(self):
        out = BASELINE_CASE / "skill_output"
        self.analysis = json.loads(next(out.glob("*-trends.json")).read_text(encoding="utf-8"))
        self.md = next(out.glob("*-trends.md")).read_text(encoding="utf-8")
        self.commentary = (BASELINE_CASE / "commentary.md").read_text(encoding="utf-8")

    def test_saved_baseline_commentary_passes(self):
        self.assertEqual(P.check(self.commentary, self.analysis, self.md)["status"], "PASS")

    def test_planted_fabrication_in_real_commentary_is_caught(self):
        planted = self.commentary + "\n- Combined COGS and opex came to 526,654.24 in Jun 2026."
        r = P.check(planted, self.analysis, self.md)
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual([f["text"] for f in r["numbers"] if f["status"] == "UNMATCHED"], ["526,654.24"])

    def test_run_dir_missing_artifacts_is_blocked(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "case_x" / "skill_output").mkdir(parents=True)
        self.assertEqual(P.check_run_dir(tmp)["case_x"]["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
