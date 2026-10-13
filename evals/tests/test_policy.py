"""Tests for the resampling regression policy (evals/policy.py). No Claude calls.

Run:  .claude/skills/monthly-trend-analysis/.venv/Scripts/python -m unittest discover -s evals/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import policy as P  # noqa: E402


def claims(**statuses):
    return [{"id": k, "status": v, "kind": "required"} for k, v in statuses.items()]


def result(det="PASS", **claim_statuses):
    return {"execution": [{"id": "X1", "status": det}], "structured": [{"id": "S1", "status": "PASS"}],
            "provenance": [{"id": "P1", "status": "PASS"}], "commentary": claims(**claim_statuses)}


class FlipDetectionTests(unittest.TestCase):
    def test_pass_to_fail_is_a_flip(self):
        self.assertEqual(P.flipped_claims(claims(R1="FAIL", F1="PASS"), {"R1": "PASS", "F1": "PASS"}), ["R1"])

    def test_fail_that_was_already_failing_is_not_a_flip(self):
        self.assertEqual(P.flipped_claims(claims(R1="FAIL"), {"R1": "FAIL"}), [])

    def test_claim_missing_from_baseline_counts_as_a_flip(self):
        self.assertEqual(P.flipped_claims(claims(R9="FAIL"), {"R1": "PASS"}), ["R9"])
        self.assertEqual(P.flipped_claims(claims(R1="FAIL"), None), ["R1"])     # no baseline at all

    def test_blocked_is_not_a_flip(self):
        self.assertEqual(P.flipped_claims(claims(R1="BLOCKED"), {"R1": "PASS"}), [])


class ShouldResampleTests(unittest.TestCase):
    def test_commentary_flip_with_clean_deterministic_checks_resamples(self):
        self.assertTrue(P.should_resample(result(R1="FAIL"), {"R1": "PASS"}))

    def test_deterministic_failure_blocks_without_resampling(self):
        self.assertFalse(P.should_resample(result(det="FAIL", R1="FAIL"), {"R1": "PASS"}))

    def test_no_flip_no_resample(self):
        self.assertFalse(P.should_resample(result(R1="PASS"), {"R1": "PASS"}))


class JudgeTests(unittest.TestCase):
    def judge(self, *per_sample):
        return P.judge_claims([claims(R1=s) for s in per_sample])["R1"]

    def test_zero_failures_passes(self):
        j = self.judge("PASS", "PASS", "PASS", "PASS")
        self.assertEqual((j["status"], j["pass_rate"]), ("PASS", "4/4"))

    def test_one_failure_is_unstable_not_blocking(self):
        j = self.judge("FAIL", "PASS", "PASS", "PASS")
        self.assertEqual((j["status"], j["pass_rate"]), ("UNSTABLE", "3/4"))

    def test_two_or_more_failures_block(self):
        self.assertEqual(self.judge("FAIL", "PASS", "FAIL", "PASS")["status"], "FAIL")
        self.assertEqual(self.judge("FAIL", "FAIL", "FAIL", "FAIL")["pass_rate"], "0/4")

    def test_blocked_sample_never_counts_as_pass(self):
        self.assertEqual(self.judge("PASS", "BLOCKED", "PASS", "PASS")["status"], "BLOCKED")
        self.assertEqual(self.judge("FAIL", "BLOCKED", "PASS", "PASS")["status"], "UNSTABLE")   # one real fail

    def test_evidence_kept_per_sample(self):
        j = P.judge_claims([[{"id": "R1", "status": "FAIL", "evidence": "missing"}],
                            [{"id": "R1", "status": "PASS", "evidence": "ok"}]])["R1"]
        self.assertEqual([e["evidence"] for e in j["evidence"]], ["missing", "ok"])


class CaseVerdictTests(unittest.TestCase):
    def test_unstable_claim_gives_unstable_case(self):
        samples = [result(R1="FAIL"), result(R1="PASS"), result(R1="PASS"), result(R1="PASS")]
        self.assertEqual(P.case_verdict(samples, P.judge_claims([s["commentary"] for s in samples])), "UNSTABLE")

    def test_deterministic_failure_in_any_resample_blocks(self):
        samples = [result(R1="FAIL"), result(det="FAIL", R1="PASS"), result(R1="PASS"), result(R1="PASS")]
        self.assertEqual(P.case_verdict(samples, P.judge_claims([s["commentary"] for s in samples])), "FAIL")

    def test_clean_case(self):
        samples = [result(R1="PASS")]
        self.assertEqual(P.case_verdict(samples, P.judge_claims([s["commentary"] for s in samples])), "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
