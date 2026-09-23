"""Negative completion/evidence checks and interruption-safe task handoff."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        result = self.cli("create", "task-1", "--title", "Test task", "--objective", "Observed behavior",
                          "--scope", "src", "--authorization", "Explicit user request",
                          "--acceptance", "Behavior verified", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.path = self.root / "docs/changes/task-1/task.json"

    def cli(self, action, *args):
        return subprocess.run([sys.executable, "-B", str(ROOT / "validation/tasks.py"), action,
                               "--root", str(self.root), *map(str, args)], capture_output=True, text=True)

    def record(self):
        return json.loads(self.path.read_text())

    def save(self, record):
        self.path.write_text(json.dumps(record))

    def complete_fixture(self):
        log = self.root / "observed.log"
        log.write_text("Synthetic static observation for checker testing.\n")
        record = self.record()
        record.update(candidate="synthetic-candidate", status="COMPLETE", next="")
        record["evidence"] = [{"id": "observed", "candidate": "synthetic-candidate", "layer": "static",
                               "status": "VERIFIED", "command": ["manual synthetic observation"], "cwd": ".",
                               "exit_code": None, "count": None, "artifact": "observed.log",
                               "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}]
        record["acceptance"][0].update(status="VERIFIED", evidence=["observed"])
        record["review"].update(status="VERIFIED", reviewer="separate-human", reference="Synthetic review receipt",
                               candidate="synthetic-candidate")
        self.save(record)
        return record

    def test_complete_does_not_imply_release_or_test_green(self):
        record = self.complete_fixture()
        result = self.cli("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(record["release"]["status"], "UNRELEASED")
        self.assertEqual(record["test_status"], "UNTESTED")

    def test_same_implementer_cannot_supply_independent_review(self):
        record = self.complete_fixture()
        record["review"]["reviewer"] = record["implementer"]
        self.save(record)
        self.assertEqual(self.cli("check").returncode, 1)

    def test_changed_evidence_artifact_is_rejected(self):
        self.complete_fixture()
        (self.root / "observed.log").write_text("Altered observation")
        self.assertEqual(self.cli("check").returncode, 1)

    def test_old_candidate_evidence_cannot_close_new_candidate(self):
        record = self.complete_fixture()
        record["candidate"] = "different-candidate"
        self.save(record)
        self.assertEqual(self.cli("check").returncode, 1)

    def test_green_requires_actual_nonzero_test_evidence(self):
        record = self.complete_fixture()
        record["test_status"] = "GREEN"
        self.save(record)
        self.assertEqual(self.cli("check").returncode, 1)

    def test_zero_tests_never_green(self):
        result = self.cli("run", "task-1", "--candidate", "synthetic-v1", "--layer", "unit",
                          "--count", "0", "--apply", "--", sys.executable, "-c", "print('0 tests')")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.record()["test_status"], "UNTESTED")

    def test_run_preview_never_executes_or_writes(self):
        before = self.path.read_bytes()
        result = self.cli("run", "task-1", "--candidate", "synthetic-v1", "--layer", "static",
                          "--", sys.executable, "-c", "open('sentinel', 'w').write('unexpected')")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.root / "sentinel").exists())
        self.assertEqual(len(list(self.path.parent.iterdir())), 1)

    def test_missing_executable_is_unknown_not_regression_failure(self):
        result = self.cli("run", "task-1", "--candidate", "synthetic-v1", "--layer", "unit",
                          "--apply", "--", "this-command-does-not-exist-synthetic-test")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.record()["test_status"], "UNKNOWN")

    def test_timeout_is_recorded_separately(self):
        result = self.cli("run", "task-1", "--candidate", "synthetic-v1", "--layer", "unit",
                          "--timeout", "1", "--apply", "--", sys.executable, "-c", "import time; time.sleep(30)")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.record()["test_status"], "TIMEOUT")
        self.assertEqual(self.cli("check").returncode, 0)

    def test_todo_preserves_user_text_and_rejects_missing_markers(self):
        path = self.root / "TODO.md"
        path.write_text("My existing plan\n")
        self.assertEqual(self.cli("todo", "--apply").returncode, 1)
        self.assertEqual(path.read_text(), "My existing plan\n")
        path.write_text("My plan\n<!-- workflow:tasks:start -->\nstale\n<!-- workflow:tasks:end -->\nMy notes\n")
        self.assertEqual(self.cli("todo", "--check").returncode, 1)
        self.assertEqual(self.cli("todo", "--apply").returncode, 0)
        self.assertTrue(path.read_text().startswith("My plan\n"))
        self.assertTrue(path.read_text().endswith("My notes\n"))
        self.assertEqual(self.cli("todo", "--check").returncode, 0)

    def test_duplicate_json_and_path_escape_fail_without_traceback(self):
        for content in ('{"id":"x","id":"y"}', '{"schema_version":NaN}'):
            self.path.write_text(content)
            result = self.cli("check")
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)

    def test_symlink_evidence_is_not_followed(self):
        self.complete_fixture()
        log = self.root / "observed.log"
        content = log.read_bytes()
        log.unlink()
        (self.root / "other.log").write_bytes(content)
        log.symlink_to(self.root / "other.log")
        self.assertEqual(self.cli("check").returncode, 1)


if __name__ == "__main__":
    unittest.main()
