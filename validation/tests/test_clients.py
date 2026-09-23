"""Four-client documentation/install regression tests, not native client tests."""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import check_bundle as checker
import install_bundle as installer


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and not p.is_symlink()}


class ClientInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        shutil.copytree(ROOT.parent, self.root,
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.target = Path(self.temp.name) / "target"
        self.target.mkdir()

    def install(self, apply: bool = False) -> tuple[int, str]:
        arguments = [str(self.target), "--source", str(self.root)]
        if apply:
            arguments.append("--apply")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = installer.main(arguments)
        return result, output.getvalue()

    def test_four_client_guide_is_validated_and_installed(self) -> None:
        relative = "docs/agent/clients.md"
        self.assertIn(relative, checker.CORE_FILES)
        guide = self.root / relative
        self.assertTrue(guide.is_file())
        for heading in ("## Cursor", "## Pi Coding Agent", "## Hermes Agent", "## Codex"):
            self.assertIn(heading, guide.read_text(encoding="utf-8"))
        code, output = self.install(True)
        self.assertEqual(code, 0, output)
        self.assertEqual((self.target / relative).read_bytes(), guide.read_bytes())
        report = checker.validate_bundle(self.target)
        self.assertEqual(report["fail"], 0)
        self.assertIn(relative, report["input_sha256"])

    def test_install_preserves_client_local_context_and_settings(self) -> None:
        # Synthetic files only. Their presence does not prove native rule loading.
        relatives = (".hermes.md", "HERMES.md", "AGENTS.override.md",
                     ".pi/SYSTEM.md", ".pi/settings.json", ".pi/extensions/local.ts",
                     ".cursor/rules/local.mdc", ".codex/config.toml", "SOUL.md")
        for relative in relatives:
            for root, content in ((self.root, b"source-local synthetic content"),
                                  (self.target, b"keep target-local synthetic content")):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        before = snapshot(self.target)
        code, output = self.install(True)
        self.assertEqual(code, 0, output)
        after = snapshot(self.target)
        for relative, content in before.items():
            self.assertEqual(after[relative], content)

    def test_install_does_not_generate_client_overrides_or_runtime_settings(self) -> None:
        code, output = self.install(True)
        self.assertEqual(code, 0, output)
        for relative in (".hermes.md", "HERMES.md", "AGENTS.override.md", ".pi",
                         ".cursor", ".codex", "SOUL.md"):
            self.assertFalse((self.target / relative).exists(), relative)
