"""Harness-only tests: the contamination guard in evals/run_evals.py (no Claude calls, no skill involved).

Run:  .claude/skills/monthly-trend-analysis/.venv/Scripts/python -m unittest discover -s evals/tests -v
"""
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_evals", EVALS / "run_evals.py")
run_evals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_evals)


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


class ContaminationGuardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="harness-guard-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "t")
        (self.root / ".gitignore").write_text("ignored.txt\n")
        (self.root / "tracked.txt").write_text("v1\n")
        (self.root / "already_dirty.txt").write_text("committed\n")
        (self.root / "evals" / "runs").mkdir(parents=True)
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "init")
        (self.root / "already_dirty.txt").write_text("dirty before the run\n")   # modified BEFORE the run starts

    def snap(self):
        return run_evals.snapshot(self.root)

    def test_message_fires_for_a_modified_file(self):
        before = self.snap()
        (self.root / "tracked.txt").write_text("v2 (edited by the operator during the run)\n")
        changes = run_evals.diff_snapshots(before, self.snap())
        msgs = run_evals.contamination_messages(changes, "case a_abc_jun2026_core", "t0", "t1")
        self.assertEqual(msgs, ["harness contamination: tracked.txt modified during run "
                                "(during case a_abc_jun2026_core, between t0 and t1)"])

    def test_already_dirty_file_edited_again_is_caught(self):
        # git status shows ' M already_dirty.txt' before AND after, so a status-only check would miss this.
        before = self.snap()
        (self.root / "already_dirty.txt").write_text("edited again during the run\n")
        self.assertEqual(run_evals.diff_snapshots(before, self.snap()), [("already_dirty.txt", "modified")])

    def test_created_and_deleted_files_are_caught(self):
        before = self.snap()
        (self.root / "README.md").write_text("new file written during the run\n")
        (self.root / "tracked.txt").unlink()
        self.assertEqual(run_evals.diff_snapshots(before, self.snap()),
                         [("README.md", "created"), ("tracked.txt", "deleted")])

    def test_run_outputs_and_ignored_files_are_not_contamination(self):
        before = self.snap()
        (self.root / "evals" / "runs" / "out.json").write_text("{}")
        (self.root / "ignored.txt").write_text("git-ignored\n")
        self.assertEqual(run_evals.diff_snapshots(before, self.snap()), [])

    def test_skill_own_write_is_attributed_to_the_skill(self):
        changes = [("trend-reports/abc-trends.md", "modified"), ("evals/README.md", "created")]
        tool_calls = [{"tool": "Edit", "input": {"file_path": str(self.root / "trend-reports" / "abc-trends.md")}}]
        mine, other = run_evals.attributable_to(changes, tool_calls, self.root)
        self.assertEqual(mine, [("trend-reports/abc-trends.md", "modified")])     # a skill X5 FAIL
        self.assertEqual(other, [("evals/README.md", "created")])                 # harness contamination


class ComparisonFlagTests(unittest.TestCase):
    """--skill-model / --no-resample (D-64): opt-in only; with no flags a run is set up exactly like the baseline."""

    def test_defaults_reproduce_the_baseline_setup(self):
        args = run_evals.parse_args([])
        self.assertEqual(args.skill_model, "claude-opus-5-5")
        self.assertFalse(args.no_resample)
        self.assertEqual(run_evals.GRADER_MODEL, "claude-sonnet-5-5")       # the grader never changes

    def test_flags_change_only_the_skill_model_and_resampling(self):
        args = run_evals.parse_args(["--skill-model", "claude-haiku-5-5", "--no-resample"])
        self.assertEqual((args.skill_model, args.no_resample), ("claude-haiku-5-5", True))
        real = run_evals.policy.should_resample
        run_evals.policy.should_resample = lambda first, base: True        # pretend the commentary flipped
        try:
            self.assertTrue(run_evals.wants_resample(False, {}, {}))         # policy applies by default
            self.assertFalse(run_evals.wants_resample(True, {}, {}))         # one sample per case with --no-resample
        finally:
            run_evals.policy.should_resample = real


class ScriptRanCheckTests(unittest.TestCase):
    """X3 regression (D-64): a long command that names run_trends.py after character 300 still counts."""

    LONG = ('cd "E:/repo" && ls -la ' + "evals/runs/some-run/c_case/skill_output " * 8 +
            '; .venv/Scripts/python .claude/skills/monthly-trend-analysis/scripts/run_trends.py "wb.xlsx" --out-dir out')

    @staticmethod
    def out_dir():
        runs = run_evals.EVALS / "runs"                       # git-ignored; execution_checks needs a path in the repo
        runs.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runs)

    def meta(self, calls, **extra):
        return {"exit_code": 0, "result_subtype": "success", "is_error": False, "tool_calls": calls,
                "outside_changes": {"by_skill": [], "not_attributable": []}, **extra}

    def test_long_command_counts_when_judged_on_the_full_input(self):
        self.assertGreater(self.LONG.index("run_trends.py"), 300)
        full = [{"tool": "Bash", "input": {"command": self.LONG}}]
        stored = [{"tool": "Bash", "input": {"command": self.LONG[:300]}}]                  # what run_meta.json keeps
        self.assertTrue(run_evals.ran_trends_script(full))
        self.assertFalse(run_evals.ran_trends_script(stored))                             # the original bug
        with self.out_dir() as d:
            x3 = {c["id"]: c["status"] for c in run_evals.execution_checks(self.meta(stored, script_ran=True), Path(d))[0]}
        self.assertEqual(x3["X3"], "PASS")                                                # X3 uses the full-command result

    def test_a_run_that_never_called_the_script_still_fails(self):
        calls = [{"tool": "Bash", "input": {"command": "ls -la " + "x/" * 400}}]
        self.assertFalse(run_evals.ran_trends_script(calls))
        with self.out_dir() as d:
            x3 = {c["id"]: c["status"] for c in run_evals.execution_checks(self.meta(calls, script_ran=False), Path(d))[0]}
        self.assertEqual(x3["X3"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
