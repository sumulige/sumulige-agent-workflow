"""Installation/upgrade/recovery contracts exercised through the public CLIs."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and not p.is_symlink()}


class ManagedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source, self.target = self.base / "source", self.base / "target"
        shutil.copytree(ROOT, self.source, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.target.mkdir()

    def cli(self, *args, script="manage.py"):
        return subprocess.run([sys.executable, "-B", str(self.source / "validation" / script),
                               *map(str, args)], capture_output=True, text=True)

    def install(self, *args):
        result = self.cli(self.target, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_repeated_install_is_idempotent_including_backups(self):
        self.install("--apply")
        before = snapshot(self.target)
        result = self.install("--apply")
        self.assertIn("UNCHANGED", result.stdout)
        self.assertEqual(snapshot(self.target), before)

    def test_upgrade_and_rollback_preserve_project_config_and_documents(self):
        self.install("--apply")
        spec = self.target / "docs/PROJECT-SPEC.md"
        spec.write_text("# Approved custom scope\n")
        config_path = self.target / "docs/agent/project.json"
        config = json.loads(config_path.read_text())
        config.update(status="configured", lint_command="python -m lint", test_command="python -m unittest")
        config_path.write_text(json.dumps(config))
        old = (self.target / "AGENTS.md").read_bytes()
        source_rules = self.source / "AGENTS.md"
        source_rules.write_bytes(old + b"\nAdditional upstream rule.\n")
        result = self.install("--apply")
        self.assertNotEqual((self.target / "AGENTS.md").read_bytes(), old)
        identifier = result.stdout.split("TRANSACTION: ")[1].strip()
        preview = snapshot(self.target)
        self.install("--rollback", identifier)
        self.assertEqual(snapshot(self.target), preview)
        self.install("--rollback", identifier, "--apply")
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), old)
        self.assertEqual(spec.read_text(), "# Approved custom scope\n")
        self.assertEqual(json.loads(config_path.read_text()), config)

    def test_custom_rule_conflict_is_all_or_nothing(self):
        self.install("--apply")
        (self.target / "AGENTS.md").write_text("Keep local agreement\n")
        before = snapshot(self.target)
        result = self.cli(self.target, "--profile", "registry", "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(snapshot(self.target), before)

    def test_first_install_conflict_does_not_create_other_files(self):
        (self.target / "AGENTS.md").write_text("Existing agreement\n")
        before = snapshot(self.target)
        self.assertEqual(self.cli(self.target, "--apply").returncode, 1)
        self.assertEqual(snapshot(self.target), before)

    def test_rollback_refuses_post_install_edits(self):
        result = self.install("--apply")
        identifier = result.stdout.split("TRANSACTION: ")[1].strip()
        (self.target / "docs/PROJECT-SPEC.md").write_text("New user scope\n")
        before = snapshot(self.target)
        self.assertEqual(self.cli(self.target, "--rollback", identifier, "--apply").returncode, 1)
        self.assertEqual(snapshot(self.target), before)

    def test_rollback_initial_install_removes_only_owned_files(self):
        (self.target / "README.md").write_text("Original readme\n")
        result = self.install("--apply")
        identifier = result.stdout.split("TRANSACTION: ")[1].strip()
        self.install("--rollback", identifier, "--apply")
        self.assertEqual((self.target / "README.md").read_text(), "Original readme\n")
        self.assertFalse((self.target / "AGENTS.md").exists())
        self.assertFalse((self.target / ".agent/workflow-lock.json").exists())

    def test_symlink_parent_is_rejected_without_following_it(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.target / ".agent").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.cli(self.target, "--apply").returncode, 1)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_invalid_lock_duplicate_keys_and_deleted_owned_file_are_rejected(self):
        self.install("--apply")
        lock = self.target / ".agent/workflow-lock.json"
        before = lock.read_bytes()
        lock.write_text('{"schema_version":1,"schema_version":1}')
        self.assertEqual(self.cli(self.target, "--apply").returncode, 1)
        lock.write_bytes(before)
        (self.target / "AGENTS.md").unlink()
        self.assertEqual(self.cli(self.target, "--apply").returncode, 1)
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_profiles_add_documents_without_downgrade_deletion(self):
        self.install("--profile", "core", "--apply")
        self.assertFalse((self.target / "DESIGN.md").exists())
        self.install("--profile", "web", "--apply")
        self.assertTrue((self.target / "DESIGN.md").exists())
        self.assertFalse((self.target / "docs/REGISTRY.md").exists())
        self.install("--profile", "registry", "--apply")
        before = snapshot(self.target)
        self.assertEqual(self.cli(self.target, "--profile", "core", "--apply").returncode, 1)
        self.assertEqual(snapshot(self.target), before)

    def test_broken_document_links_are_reported(self):
        self.install("--apply")
        (self.target / "README.md").write_text("[Missing](docs/NO-SUCH-DOC.md)\n")
        result = self.cli(self.target, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Broken local", result.stderr)

    def test_all_seven_entries_and_override_diagnostics(self):
        self.install("--apply")
        result = self.cli("check", self.target, script="adapters.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for client in ("codex", "claude-code", "cursor", "hermes", "pi", "gemini", "opencode"):
            self.assertIn(client + ":", result.stdout)
        (self.target / ".hermes.md").write_text("Existing Hermes context\n")
        before = snapshot(self.target)
        result = self.cli("check", self.target, "--clients", "hermes", script="adapters.py")
        self.assertEqual(result.returncode, 1)
        self.assertIn("shadow", result.stdout)
        self.assertEqual(snapshot(self.target), before)

    def test_empty_source_template_cannot_be_installed(self):
        (self.source / "templates/core/docs/PROJECT-SPEC.md").write_text("\n")
        self.assertEqual(self.cli(self.target, "--apply").returncode, 1)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_backups_are_git_ignored_even_in_an_existing_project(self):
        subprocess.run(["git", "init", "-q", str(self.target)], check=True, capture_output=True)
        result = self.install("--apply")
        identifier = result.stdout.split("TRANSACTION: ")[1].strip()
        receipt = f".agent/workflow-backups/{identifier}/receipt.json"
        result = subprocess.run(["git", "check-ignore", receipt], cwd=self.target, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
