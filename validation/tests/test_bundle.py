"""Regression tests use synthetic temporary repositories, never real secrets."""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import check_bundle as checker
import install_bundle as installer

SOURCE = ROOT.parent


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


class BundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        shutil.copytree(SOURCE, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.config = json.loads((self.root / checker.CONFIG_PATH).read_text(encoding="utf-8"))
        self.target = Path(self.temp.name) / "target"
        self.target.mkdir()

    def save_config(self) -> None:
        (self.root / checker.CONFIG_PATH).write_text(json.dumps(self.config) + "\n", encoding="utf-8")

    def configured(self) -> None:
        self.config.update(status="configured", test_command="python3 -m unittest", lint_command="python3 -m compileall -q validation")
        self.save_config()

    def install(self, apply: bool = False) -> tuple[int, str]:
        arguments = [str(self.target), "--source", str(self.root)]
        if apply:
            arguments.append("--apply")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = installer.main(arguments)
        return result, output.getvalue()

    def test_valid_template_is_not_ready(self) -> None:
        self.assertEqual(checker.validate_bundle(self.root)["fail"], 0)
        self.assertGreater(checker.validate_bundle(self.root, "ready")["fail"], 0)

    def test_configured_valid(self) -> None:
        self.configured()
        self.assertEqual(checker.validate_bundle(self.root, "ready")["fail"], 0)

    def test_configured_empty_commands_fail_in_both_modes(self) -> None:
        self.config["status"] = "configured"
        self.save_config()
        for mode in ("bundle", "ready"):
            with self.subTest(mode=mode):
                self.assertGreater(checker.validate_bundle(self.root, mode)["fail"], 0)

    def test_invalid_configuration_values(self) -> None:
        cases = {
            "status": ["configured-invalid", "configured ", "", None, False, []],
            "timeout_seconds": [-1, 0, 3601, True, 1.5, "600", None],
            "protected_paths": [False, "AGENTS.md", [], ["../secret"], ["/tmp"], ["docs//agent/"], ["C:\\tmp"]],
            "schema_version": [True, 2, "1"],
            "working_directory": ["../", "/tmp", "x/../y", "x//y", "x\\y", "C:/tmp", "", False],
            "test_command": [None, [], "a\nb", "a\x00b"],
            "lint_command": [False, "a\rb"],
            "commit_policy": ["always", None],
            "memory_policy": ["always", None],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    config = dict(self.config, **{field: value})
                    self.assertTrue(checker.validate_config(config, self.root))

    def test_missing_and_unknown_fields_fail(self) -> None:
        for key in self.config:
            with self.subTest(key=key):
                config = dict(self.config)
                del config[key]
                self.assertTrue(checker.validate_config(config, self.root))
        self.assertTrue(checker.validate_config(dict(self.config, status_typo="configured"), self.root))
        self.assertTrue(checker.validate_config([], self.root))

    def test_duplicate_and_nonstandard_json_rejected(self) -> None:
        for text in ('{"status":1,"status":2}', '{"outer":{"x":1,"x":2}}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{bad'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                checker.strict_json(text)

    def test_malformed_config_fails_without_crash(self) -> None:
        for text in ('{"status":1,"status":2}', '[]', '{bad', '\ufeff{}'):
            with self.subTest(text=text):
                (self.root / checker.CONFIG_PATH).write_text(text, encoding="utf-8")
                self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)

    def test_protected_paths_duplicate_or_weakened(self) -> None:
        for paths in (["AGENTS.md"], self.config["protected_paths"] * 2):
            with self.subTest(paths=paths):
                self.assertTrue(checker.validate_config(dict(self.config, protected_paths=paths), self.root))

    def test_working_directory_must_exist_when_ready(self) -> None:
        self.configured()
        self.config["working_directory"] = "absent"
        self.save_config()
        self.assertGreater(checker.validate_bundle(self.root, "ready")["fail"], 0)
        (self.root / "absent").mkdir()
        self.assertEqual(checker.validate_bundle(self.root, "ready")["fail"], 0)

    def test_commands_are_never_executed(self) -> None:
        sentinel = Path(self.temp.name) / "must-not-exist"
        self.configured()
        self.config["test_command"] = f'touch "{sentinel}"'
        self.save_config()
        self.assertEqual(checker.validate_bundle(self.root, "ready")["fail"], 0)
        self.assertFalse(sentinel.exists())

    def test_no_side_effects_and_hashes_match(self) -> None:
        before = snapshot(self.root)
        report = checker.validate_bundle(self.root)
        self.assertEqual(before, snapshot(self.root))
        for relative, digest in report["input_sha256"].items():
            self.assertEqual(digest, hashlib.sha256(before[relative]).hexdigest())
        self.assertFalse((self.root / "validation/results.json").exists())

    def test_empty_and_missing_core_files(self) -> None:
        for relative in checker.CORE_FILES:
            path = self.root / relative
            original = path.read_bytes()
            with self.subTest(path=relative):
                path.write_bytes(b"")
                self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)
                path.unlink()
                self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)
                path.write_bytes(original)

    def test_markers_without_rule_body_fail(self) -> None:
        path = self.root / "AGENTS.md"
        text = path.read_text(encoding="utf-8")
        for number in range(1, 10):
            with self.subTest(number=number):
                modified = "\n".join(f"<!-- HR-{number} --> **HR-{number}** " if line.startswith(f"<!-- HR-{number} -->") else line for line in text.splitlines())
                path.write_text(modified, encoding="utf-8")
                self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)
        path.write_text(text + "\n<!-- HR-7 -->\n", encoding="utf-8")
        self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)

    def test_comment_only_body_fails(self) -> None:
        path = self.root / "AGENTS.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join("<!-- HR-7 --> **HR-7** <!-- no body -->" if line.startswith("<!-- HR-7 -->") else line for line in lines), encoding="utf-8")
        self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)

    def test_broken_or_escaping_local_link_fails(self) -> None:
        path = self.root / "AGENTS.md"
        text = path.read_text(encoding="utf-8")
        for link in ("missing.md", "../outside.md", "/outside.md"):
            with self.subTest(link=link):
                path.write_text(text + f"\n[broken]({link})\n", encoding="utf-8")
                self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)

    def test_symlink_core_file_is_not_read(self) -> None:
        path = self.root / "AGENTS.md"
        outside = Path(self.temp.name) / "synthetic"
        outside.write_text("synthetic inaccessible test value", encoding="utf-8")
        path.unlink()
        path.symlink_to(outside)
        report = checker.validate_bundle(self.root)
        self.assertGreater(report["fail"], 0)
        self.assertNotIn("AGENTS.md", report["input_sha256"])

    def test_symlink_working_directory_rejected(self) -> None:
        self.configured()
        (self.root / "linked").symlink_to(self.target, target_is_directory=True)
        self.config["working_directory"] = "linked"
        self.save_config()
        self.assertGreater(checker.validate_bundle(self.root, "ready")["fail"], 0)

    def test_invalid_utf8_reports_failure(self) -> None:
        (self.root / "AGENTS.md").write_bytes(b"\xff")
        self.assertGreater(checker.validate_bundle(self.root)["fail"], 0)

    def test_cli_json_and_exit_codes(self) -> None:
        for mode, expected in (("bundle", 0), ("ready", 1)):
            with self.subTest(mode=mode):
                before = snapshot(self.root)
                proc = subprocess.run([sys.executable, "-B", str(self.root / "validation/check_bundle.py"), "--root", str(self.root), "--mode", mode, "--json"], capture_output=True, text=True, timeout=20)
                self.assertEqual(proc.returncode, expected, proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["mode"], mode)
                self.assertEqual(before, snapshot(self.root))

    def test_missing_root_and_invalid_mode(self) -> None:
        self.assertGreater(checker.validate_bundle(self.root / "absent")["fail"], 0)
        with self.assertRaises(ValueError):
            checker.validate_bundle(self.root, "invalid")

    def test_installer_cli_without_bytecode_flag_is_read_only(self) -> None:
        before = snapshot(self.root)
        proc = subprocess.run([sys.executable, str(self.root / "validation/install_bundle.py"), str(self.target)], capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual(snapshot(self.target), {})

    def test_install_preview_does_not_write(self) -> None:
        before = snapshot(self.target)
        code, output = self.install()
        self.assertEqual(code, 0, output)
        self.assertIn("PREVIEW ONLY", output)
        self.assertEqual(before, snapshot(self.target))

    def test_install_apply_repeat_and_exclusions(self) -> None:
        (self.target / "README.md").write_text("keep user's readme", encoding="utf-8")
        code, output = self.install(True)
        self.assertEqual(code, 0, output)
        self.assertEqual(checker.validate_bundle(self.target)["fail"], 0)
        before = snapshot(self.target)
        self.assertEqual(self.install(True)[0], 0)
        self.assertEqual(before, snapshot(self.target))
        self.assertEqual((self.target / "README.md").read_text(), "keep user's readme")
        for excluded in (".github", "validation/tests", "validation/results.json", ".gitignore"):
            self.assertFalse((self.target / excluded).exists())

    def test_conflict_is_all_or_nothing(self) -> None:
        (self.target / "AGENTS.md").write_text("keep existing rules", encoding="utf-8")
        before = snapshot(self.target)
        for apply in (False, True):
            with self.subTest(apply=apply):
                code, output = self.install(apply)
                self.assertEqual(code, 1)
                self.assertIn("CONFLICT", output)
                self.assertEqual(before, snapshot(self.target))

    def test_installer_does_not_transfer_configuration(self) -> None:
        self.configured()
        self.config["commit_policy"] = "after-validation"
        self.config["memory_policy"] = "append-authorized"
        self.save_config()
        self.assertEqual(self.install(True)[0], 0)
        copied = json.loads((self.target / checker.CONFIG_PATH).read_text())
        self.assertEqual(copied, checker.DEFAULT_CONFIG)

    def test_configured_target_is_preserved_on_upgrade(self) -> None:
        self.assertEqual(self.install(True)[0], 0)
        path = self.target / checker.CONFIG_PATH
        config = json.loads(path.read_text())
        config.update(status="configured", test_command="real test", lint_command="real lint")
        path.write_text(json.dumps(config))
        before = snapshot(self.target)
        self.assertEqual(self.install(True)[0], 1)
        self.assertEqual(before, snapshot(self.target))

    def test_install_symlink_parent_and_file_refused(self) -> None:
        for relative, is_directory in (("docs", True), ("AGENTS.md", False)):
            with self.subTest(relative=relative):
                outside = Path(self.temp.name) / ("outside-dir" if is_directory else "outside-file")
                if is_directory:
                    outside.mkdir()
                else:
                    outside.write_text("preserve", encoding="utf-8")
                link = self.target / relative
                link.symlink_to(outside, target_is_directory=is_directory)
                self.assertEqual(self.install(True)[0], 1)
                self.assertFalse((self.target / "CLAUDE.md").exists())
                link.unlink()

    def test_install_parent_file_conflict(self) -> None:
        (self.target / "docs").write_text("not a directory", encoding="utf-8")
        before = snapshot(self.target)
        self.assertEqual(self.install(True)[0], 1)
        self.assertEqual(before, snapshot(self.target))

    def test_bad_source_or_target_refused(self) -> None:
        (self.root / "docs/agent/workflow.md").write_text("", encoding="utf-8")
        self.assertEqual(self.install(True)[0], 1)
        self.assertEqual(snapshot(self.target), {})
        with self.assertRaises(ValueError):
            installer.plan_install(SOURCE, SOURCE)
        with self.assertRaises(ValueError):
            installer.plan_install(SOURCE, self.target / "absent")

    def test_io_failure_reports_partial_without_deleting_files(self) -> None:
        original_open = Path.open
        counter = [0]
        def failing_open(path: Path, mode: str = "r", *args, **kwargs):
            if mode == "xb":
                counter[0] += 1
                if counter[0] == 2:
                    raise OSError("synthetic write failure")
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, "open", failing_open):
            code, output = self.install(True)
        self.assertEqual(code, 1)
        self.assertIn("PARTIAL", output)
        self.assertTrue((self.target / "AGENTS.md").exists())

    def test_python_sources_parse_without_bytecode(self) -> None:
        for path in (SOURCE / "validation").rglob("*.py"):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
