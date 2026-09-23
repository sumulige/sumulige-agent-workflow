"""Task v2 behavior through CLI and its documented JSON files."""
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "docs/changes/task/task.json"
        result = self.cli("create", "task", "--title", "Contract fixture", "--objective", "Check completion",
                          "--scope", ".", "--authorization", "Synthetic fixture", "--acceptance", "Behavior",
                          "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)

    def cli(self, action, *args):
        return subprocess.run([sys.executable, "-B", str(ROOT / "validation/tasks.py"), action,
                               "--root", str(self.root), *map(str, args)], capture_output=True, text=True)

    def record(self):
        return json.loads(self.path.read_text())

    def save(self, record):
        self.path.write_text(json.dumps(record))

    def run_check(self, script, layer="static", candidate="A", check_id="", count=None, timeout=5):
        args = ["task", "--candidate", candidate, "--layer", layer, "--timeout", str(timeout)]
        if check_id:
            args += ["--check-id", check_id]
        if count is not None:
            args += ["--count", str(count)]
        return self.cli("run", *args, "--apply", "--", sys.executable, "-c", script)

    def configure(self, checks, kind="maintenance", apply=True):
        (self.root / "checks.json").write_text(json.dumps(checks))
        return self.cli("contract", "task", "--kind", kind, "--basis", "Approved synthetic check scope",
                        "--checks", "checks.json", *(["--apply"] if apply else []))

    def mark_complete(self):
        record = self.record()
        passed = record["evidence"][-1]
        record.update(status="COMPLETE", next="")
        record["acceptance"][0].update(status="VERIFIED", evidence=[passed["id"]])
        record["review"].update(status="VERIFIED", reviewer="other", reference="Synthetic review",
                               candidate=record["candidate"], contract=passed["contract"])
        self.save(record)

    def check_spec(self, script="print('suite')", layer="unit", min_count=1):
        return {"id": "suite", "description": "Entire expected suite", "required": True,
                "layer": layer, "command": [sys.executable, "-c", script], "cwd": ".",
                "min_count": min_count if layer in ("unit", "integration") else None}

    def test_narrowed_command_cannot_replace_full_check_or_execute(self):
        check = self.check_spec()
        self.assertEqual(self.configure([check]).returncode, 0)
        before = {p.name: p.read_bytes() for p in self.path.parent.iterdir()}
        result = self.cli("run", "task", "--candidate", "A", "--layer", "unit", "--count", "1",
                          "--check-id", "suite", "--apply", "--", *check["command"], "-k", "one-test")
        self.assertEqual(result.returncode, 1)
        self.assertIn("differs", result.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in self.path.parent.iterdir()}, before)

    def test_failure_then_same_check_success_can_complete(self):
        script = "from pathlib import Path; raise SystemExit(0 if Path('fixed').exists() else 1)"
        self.assertEqual(self.configure([self.check_spec(script)]).returncode, 0)
        self.assertEqual(self.run_check(script, "unit", check_id="suite", count=1).returncode, 1)
        (self.root / "fixed").touch()
        self.assertEqual(self.run_check(script, "unit", check_id="suite", count=1).returncode, 0)
        self.assertEqual(self.record()["test_status"], "GREEN")
        self.mark_complete()
        self.assertEqual(self.cli("check").returncode, 0)
        self.assertEqual(len(self.record()["evidence"]), 2)

    def test_too_few_tests_cannot_satisfy_required_scope(self):
        self.assertEqual(self.configure([self.check_spec(min_count=2)]).returncode, 0)
        self.assertEqual(self.run_check("print('suite')", "unit", check_id="suite", count=1).returncode, 0)
        self.assertEqual(self.record()["test_status"], "UNTESTED")
        self.mark_complete()
        self.assertEqual(self.cli("check").returncode, 1)

    def test_contract_preview_and_change_preserve_evidence_but_invalidate_review(self):
        check = self.check_spec(layer="static")
        self.assertEqual(self.configure([check]).returncode, 0)
        self.assertEqual(self.run_check("print('suite')", check_id="suite").returncode, 0)
        self.mark_complete()
        self.assertEqual(self.cli("check").returncode, 0)
        before = self.path.read_bytes()
        self.assertEqual(self.configure([], apply=False).returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.configure([]).returncode, 0)
        record = self.record()
        self.assertEqual(record["status"], "PARTIAL")
        self.assertEqual(record["review"]["status"], "UNKNOWN")
        self.assertEqual(record["acceptance"][0]["evidence"], [])
        self.assertEqual(len(record["evidence"]), 1)
        self.mark_complete()  # Tries to reuse the old contract's evidence and review.
        self.assertEqual(self.cli("check").returncode, 1)

    def code_project(self):
        config = json.loads((ROOT / "docs/agent/project.json").read_text())
        config.update(status="configured", working_directory=".",
                      lint_command=shlex.join([sys.executable, "-c", "print('lint')"]),
                      test_command=shlex.join([sys.executable, "-c", "print('test')"]))
        location = self.root / "docs/agent/project.json"
        location.parent.mkdir(parents=True)
        location.write_text(json.dumps(config))
        result = self.cli("contract", "task", "--kind", "code", "--basis", "Configured project", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        return config, location

    def test_configured_checks_are_required_and_completed_contract_can_be_refreshed(self):
        config, location = self.code_project()
        self.assertEqual(self.run_check("print('lint')", check_id="lint").returncode, 0)
        self.mark_complete()
        self.assertEqual(self.cli("check").returncode, 1)  # Missing configured test.
        record = self.record()
        record["status"] = "PARTIAL"
        record["next"] = "Run missing test"
        self.save(record)
        self.assertEqual(self.run_check("print('test')", "unit", check_id="test", count=1).returncode, 0)
        self.mark_complete()
        self.assertEqual(self.cli("check").returncode, 0)
        config["lint_command"] = shlex.join([sys.executable, "-c", "print('changed lint')"])
        location.write_text(json.dumps(config))
        self.assertEqual(self.cli("check").returncode, 1)
        result = self.cli("contract", "task", "--kind", "code", "--basis", "Approved new lint scope", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.record()["status"], "PARTIAL")
        self.assertEqual(self.record()["review"]["status"], "UNKNOWN")

    def test_code_completion_cannot_drop_configured_lint(self):
        self.code_project()
        checks = [c for c in self.record()["contract"]["checks"] if c["id"] == "test"]
        self.assertEqual(self.configure(checks, kind="code").returncode, 0)
        self.assertEqual(self.run_check("print('test')", "unit", check_id="test", count=1).returncode, 0)
        self.mark_complete()
        result = self.cli("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("configured lint/test", result.stderr)

    def test_old_success_cannot_certify_after_a_failed_rerun(self):
        script = "from pathlib import Path; raise SystemExit(1 if Path('broken').exists() else 0)"
        self.assertEqual(self.configure([self.check_spec(script)]).returncode, 0)
        self.assertEqual(self.run_check(script, "unit", check_id="suite", count=1).returncode, 0)
        self.mark_complete()
        (self.root / "broken").touch()
        self.assertEqual(self.run_check(script, "unit", check_id="suite", count=1).returncode, 1)
        record = self.record()
        self.assertEqual(record["review"]["status"], "UNKNOWN")
        record["acceptance"][0].update(status="VERIFIED", evidence=[record["evidence"][0]["id"]])
        self.save(record)
        result = self.cli("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("latest current", result.stderr)

    def test_missing_count_is_unknown_and_raw_outcome_cannot_be_relabelled(self):
        self.assertEqual(self.run_check("print('count unknown')", "unit").returncode, 0)
        record = self.record()
        self.assertEqual(record["test_status"], "UNKNOWN")
        self.assertEqual(record["evidence"][0]["status"], "UNKNOWN")
        record["evidence"][0]["outcome"] = "unavailable"
        self.save(record)
        result = self.cli("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Non-execution", result.stderr)

    def test_unavailable_command_has_no_fabricated_exit_or_count(self):
        result = self.cli("run", "task", "--candidate", "A", "--layer", "unit", "--count", "3",
                          "--apply", "--", "nonexistent-synthetic-command-for-test")
        self.assertEqual(result.returncode, 1)
        item = self.record()["evidence"][0]
        self.assertEqual(item["outcome"], "unavailable")
        self.assertIsNone(item["exit_code"])
        self.assertIsNone(item["count"])
        self.assertEqual(self.cli("check").returncode, 0)

    def test_invalid_contract_does_not_write_or_traceback(self):
        before = self.path.read_bytes()
        bad = self.check_spec()
        bad["min_count"] = True
        for checks in ([bad], [self.check_spec(), self.check_spec()], {"not": "an array"}):
            result = self.configure(checks)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(self.path.read_bytes(), before)

    def test_repeat_migration_still_rejects_task_identity_mismatch(self):
        record = self.record()
        record["id"] = "another-task"
        self.save(record)
        result = self.cli("migrate", "task", "--kind", "maintenance", "--basis", "Repeat migration")
        self.assertEqual(result.returncode, 1)

    def test_v1_migration_previews_then_backs_up_and_invalidates_old_claims(self):
        self.assertEqual(self.run_check("print('legacy test')", "unit", count=1).returncode, 0)
        record = self.record()
        record["schema_version"] = 1
        record.pop("contract")
        record.pop("releases")
        record["release"] = {"status": "RELEASED", "reference": "old-release-with-no-candidate"}
        record["review"].pop("contract")
        for item in record["evidence"]:
            for key in ("contract", "check_id", "outcome"):
                item.pop(key)
        self.save(record)
        before = self.path.read_bytes()
        self.assertEqual(self.cli("check").returncode, 0)
        self.assertIn("legacy v1", self.cli("check").stdout)
        self.assertEqual(self.run_check("print('must not run')").returncode, 1)
        args = ("task", "--kind", "maintenance", "--basis", "Approve explicit legacy migration")
        result = self.cli("migrate", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.root / ".agent/workflow-backups").exists())
        result = self.cli("migrate", *args, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        migrated = self.record()
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["test_status"], "UNKNOWN")
        self.assertEqual(migrated["releases"], [{"candidate": "", "reference": "old-release-with-no-candidate"}])
        self.assertEqual(migrated["evidence"][0]["outcome"], "legacy")
        self.assertEqual(migrated["review"]["status"], "UNKNOWN")
        self.assertEqual(self.cli("check").returncode, 0)
        self.assertIn("| UNRELEASED |", self.cli("todo").stdout)
        identifier = result.stdout.split("TRANSACTION: ")[1].strip()
        self.assertEqual((self.root / f".agent/workflow-backups/{identifier}/0").read_bytes(), before)
        second = self.cli("migrate", *args, "--apply")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.record(), migrated)
        rollback = subprocess.run([sys.executable, "-B", str(ROOT / "validation/manage.py"), str(self.root),
                                   "--rollback", identifier, "--apply"], capture_output=True, text=True)
        self.assertEqual(rollback.returncode, 0, rollback.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_timeout_survives_unrelated_success_and_summary_tampering(self):
        self.assertEqual(self.run_check("import time; time.sleep(30)", "unit", timeout=1).returncode, 1)
        self.assertEqual(self.run_check("print('static success')").returncode, 0)
        record = self.record()
        self.assertEqual(record["test_status"], "TIMEOUT")
        self.assertEqual(record["evidence"][0]["outcome"], "timeout")
        for incorrect in ("RED", "GREEN", "UNKNOWN", "UNTESTED"):
            record["test_status"] = incorrect
            self.save(record)
            self.assertEqual(self.cli("check").returncode, 1, incorrect)

    def test_release_stays_with_its_candidate_and_history_is_preserved(self):
        self.assertEqual(self.run_check("print('A')").returncode, 0)
        record = self.record()
        record.pop("release", None)
        record["releases"] = [{"candidate": "A", "reference": "synthetic-release-A"}]
        self.save(record)
        result = self.run_check("print('B')", candidate="B")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.record()["releases"], [{"candidate": "A", "reference": "synthetic-release-A"}])
        self.assertIn("| UNRELEASED |", self.cli("todo").stdout)
        self.assertEqual(self.run_check("print('A again')", candidate="A").returncode, 0)
        self.assertIn("| RELEASED |", self.cli("todo").stdout)

    def test_declared_lint_failure_cannot_be_completed_using_another_pass(self):
        checks = [{"id": "lint", "description": "Full lint", "required": True, "layer": "static",
                   "command": [sys.executable, "-c", "raise SystemExit(1)"], "cwd": ".", "min_count": None}]
        (self.root / "checks.json").write_text(json.dumps(checks))
        result = self.cli("contract", "task", "--kind", "maintenance", "--basis", "Declared checks",
                          "--checks", "checks.json", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli("run", "task", "--candidate", "A", "--layer", "static", "--check-id", "lint",
                          "--apply", "--", *checks[0]["command"])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.cli("run", "task", "--candidate", "A", "--layer", "static", "--apply",
                                  "--", sys.executable, "-c", "print('observation')").returncode, 0)
        record = self.record()
        passed = record["evidence"][-1]
        record.update(status="COMPLETE", next="")
        record["acceptance"][0].update(status="VERIFIED", evidence=[passed["id"]])
        record["review"].update(status="VERIFIED", reviewer="other", reference="Synthetic review",
                               candidate="A", contract=passed["contract"])
        self.save(record)
        result = self.cli("check")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("required check", result.stderr)


if __name__ == "__main__":
    unittest.main()
