"""Public CLI tests against synthetic projects; no native AI sessions."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def run_cli(self, script, *arguments):
        return subprocess.run([sys.executable, "-B", str(ROOT / "validation" / script),
                               *map(str, arguments)], capture_output=True, text=True)

    def test_preview_then_install_core_without_overwriting_existing_readme(self):
        (self.project / "README.md").write_text("Existing product documentation\n")
        result = self.run_cli("manage.py", self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.project.iterdir()), [self.project / "README.md"])
        result = self.run_cli("manage.py", self.project, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.project / "README.md").read_text(), "Existing product documentation\n")
        self.assertTrue((self.project / "docs/PROJECT-SPEC.md").is_file())
        self.assertFalse((self.project / "DESIGN.md").exists())
        self.assertTrue((self.project / ".agent/workflow-lock.json").is_file())

    def test_task_cannot_claim_complete_without_acceptance_evidence(self):
        result = self.run_cli("tasks.py", "create", "fix-01", "--root", self.project,
                              "--title", "Fix checkout", "--objective", "Reject invalid cart",
                              "--scope", "src/cart.py", "--authorization", "User requested fix",
                              "--acceptance", "Invalid cart is rejected", "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.project / "docs/changes/fix-01/task.json"
        record = json.loads(path.read_text())
        record["status"] = "COMPLETE"
        path.write_text(json.dumps(record))
        result = self.run_cli("tasks.py", "check", "--root", self.project)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("COMPLETE", result.stdout + result.stderr)

    def test_failed_command_is_recorded_and_todo_comes_from_task(self):
        result = self.run_cli("tasks.py", "create", "failure-case", "--root", self.project,
                              "--title", "Checkout validation", "--objective", "Reject invalid cart",
                              "--scope", "src", "--authorization", "User requested fix",
                              "--acceptance", "Invalid cart is rejected", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("tasks.py", "run", "failure-case", "--root", self.project,
                              "--candidate", "synthetic-v1", "--layer", "unit", "--apply",
                              "--", sys.executable, "-c", "print('regression failure'); raise SystemExit(3)")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        record = json.loads((self.project / "docs/changes/failure-case/task.json").read_text())
        self.assertEqual(record["test_status"], "RED")
        self.assertEqual(record["status"], "PARTIAL")
        self.assertEqual(record["evidence"][0]["exit_code"], 3)
        self.assertEqual(self.run_cli("tasks.py", "check", "--root", self.project).returncode, 0)
        result = self.run_cli("tasks.py", "todo", "--root", self.project, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RED", (self.project / "TODO.md").read_text())
        self.assertEqual(self.run_cli("tasks.py", "todo", "--root", self.project, "--check").returncode, 0)

    def test_global_bootstrap_shares_one_version_and_preserves_conflicting_rules(self):
        result = self.run_cli("adapters.py", "global", "--home", self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.project.iterdir()), [])
        (self.project / ".codex").mkdir()
        existing = self.project / ".codex/AGENTS.md"
        existing.write_text("Keep personal rules\n")
        result = self.run_cli("adapters.py", "global", "--home", self.project, "--apply")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(existing.read_text(), "Keep personal rules\n")
        self.assertFalse((self.project / ".claude").exists())
        existing.unlink()
        result = self.run_cli("adapters.py", "global", "--home", self.project, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MANUAL", result.stdout)
        self.assertTrue((self.project / ".gemini/GEMINI.md").is_file())
        self.assertFalse((self.project / ".hermes/SOUL.md").exists())
        self.assertEqual(len(list((self.project / ".config/sumulige-coding-agent-workflow/versions").glob("*/AGENTS.md"))), 1)

    def test_installed_registry_profile_checks_documents_and_detects_rule_drift(self):
        result = self.run_cli("manage.py", self.project, "--profile", "registry", "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.project / "docs/REGISTRY.md").exists())
        result = self.run_cli("manage.py", self.project, "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.project / "docs/PROJECT-SPEC.md").write_text("# Approved product\n")
        self.assertEqual(self.run_cli("manage.py", self.project, "--check").returncode, 0)
        with (self.project / "AGENTS.md").open("a") as output:
            output.write("\nLocal custom rule\n")
        result = self.run_cli("manage.py", self.project, "--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("drift", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
