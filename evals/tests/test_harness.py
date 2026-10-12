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


if __name__ == "__main__":
    unittest.main(verbosity=2)
