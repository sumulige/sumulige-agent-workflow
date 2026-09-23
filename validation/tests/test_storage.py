"""Filesystem failure injection at the OS boundary, using synthetic bytes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import rollback_plan, transaction


class RecoveryTests(unittest.TestCase):
    def test_partial_os_failure_can_be_rolled_back_without_touching_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "second.txt").write_bytes(b"old second")
            (root / "unrelated.txt").write_bytes(b"user content")
            with patch("os.replace", side_effect=OSError("synthetic disk failure")):
                with self.assertRaisesRegex(ValueError, "PARTIAL transaction") as failure:
                    transaction(root, {"first.txt": (None, b"new first"),
                                       "second.txt": (b"old second", b"new second")})
            identifier = str(failure.exception).split("transaction ")[1].split(";")[0]
            self.assertEqual((root / "first.txt").read_bytes(), b"new first")
            self.assertEqual((root / "second.txt").read_bytes(), b"old second")
            transaction(root, rollback_plan(root, identifier))
            self.assertFalse((root / "first.txt").exists())
            self.assertEqual((root / "second.txt").read_bytes(), b"old second")
            self.assertEqual((root / "unrelated.txt").read_bytes(), b"user content")

    def test_modified_backup_is_not_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "file.txt").write_bytes(b"old")
            identifier = transaction(root, {"file.txt": (b"old", b"new")})
            (root / f".agent/workflow-backups/{identifier}/0").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "Corrupt backup"):
                rollback_plan(root, identifier)
            self.assertEqual((root / "file.txt").read_bytes(), b"new")

    def test_changed_precondition_prevents_any_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "file.txt").write_bytes(b"user edit")
            with self.assertRaisesRegex(ValueError, "changed since preview"):
                transaction(root, {"file.txt": (b"old", b"new")})
            self.assertFalse((root / ".agent").exists())
            self.assertEqual((root / "file.txt").read_bytes(), b"user edit")


if __name__ == "__main__":
    unittest.main()
