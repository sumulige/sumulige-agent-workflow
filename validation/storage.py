"""Small, recoverable file transactions in a trusted, quiescent directory.

No OS sandbox, hostile-process protection, or automatic overwrite resolution.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from check_bundle import local_path, strict_json

BACKUPS = ".agent/workflow-backups"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def read_file(root: Path, relative: str) -> bytes | None:
    path = local_path(root, relative)
    for parent in path.parents:
        if parent == root:
            break
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"Parent is not a directory: {relative}")
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"Not a regular file: {relative}")
    return path.read_bytes()


def replace_file(root: Path, relative: str, before: bytes | None, after: bytes | None):
    if read_file(root, relative) != before:
        raise ValueError(f"File changed since preview: {relative}")
    path = local_path(root, relative)
    if after is None:
        if before is not None:
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if before is None:
        with path.open("xb") as output:
            output.write(after)
        return
    temporary = path.with_name(path.name + ".workflow-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as output:
            output.write(after)
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(path.stat().st_mode & 0o777)
        if read_file(root, relative) != before:
            raise ValueError(f"File changed during write: {relative}")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def transaction(root: Path, changes: dict[str, tuple[bytes | None, bytes | None]]) -> str | None:
    changes = {p: pair for p, pair in changes.items() if pair[0] != pair[1]}
    if not changes:
        return None
    for path, (before, _) in changes.items():
        if read_file(root, path) != before:
            raise ValueError(f"File changed since preview: {path}")
    identifier = uuid.uuid4().hex
    relative = f"{BACKUPS}/{identifier}"
    # Backups can contain target-owned content. Keep them out of Git without
    # editing the project's existing .gitignore or copying source authority.
    backup_root = local_path(root, BACKUPS)
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    ignore = read_file(root, BACKUPS + "/.gitignore")
    if ignore is None:
        replace_file(root, BACKUPS + "/.gitignore", None, b"*\n")
    elif ignore != b"*\n":
        raise ValueError("Backup ignore file differs; review before writing backups")
    journal = local_path(root, relative)
    journal.mkdir(parents=True, exist_ok=False, mode=0o700)
    entries = {}
    for index, (path, (before, after)) in enumerate(changes.items()):
        backup = str(index)
        if before is not None:
            (journal / backup).write_bytes(before)
        entries[path] = {"before": digest(before) if before is not None else None,
                         "after": digest(after) if after is not None else None,
                         "backup": backup}
    receipt = {"schema_version": 1, "state": "prepared", "files": entries}
    (journal / "receipt.json").write_bytes(encoded(receipt))
    try:
        for path, (before, after) in changes.items():
            replace_file(root, path, before, after)
        receipt["state"] = "applied"
        (journal / "receipt.json").write_bytes(encoded(receipt))
    except (OSError, ValueError) as error:
        raise ValueError(f"PARTIAL transaction {identifier}; inspect receipt and use --rollback: {error}") from error
    return identifier


def rollback_plan(root: Path, identifier: str):
    if len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
        raise ValueError("Invalid transaction ID")
    directory = f"{BACKUPS}/{identifier}"
    receipt = strict_json(local_path(root, directory + "/receipt.json").read_text())
    if (not isinstance(receipt, dict) or set(receipt) != {"schema_version", "state", "files"}
            or type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1
            or receipt["state"] not in ("prepared", "applied") or not isinstance(receipt["files"], dict)):
        raise ValueError("Invalid transaction receipt")
    changes = {}
    for path, entry in receipt["files"].items():
        if (not isinstance(entry, dict) or set(entry) != {"before", "after", "backup"}
                or not isinstance(entry["backup"], str) or not entry["backup"].isdigit()
                or path.startswith(BACKUPS + "/")):
            raise ValueError("Invalid transaction entry")
        current = read_file(root, path)
        current_hash = digest(current) if current is not None else None
        if current_hash not in (entry["before"], entry["after"]):
            raise ValueError(f"Rollback conflict: {path}")
        previous = None
        if entry["before"] is not None:
            previous = local_path(root, directory + "/" + entry["backup"]).read_bytes()
            if digest(previous) != entry["before"]:
                raise ValueError(f"Corrupt backup: {path}")
        changes[path] = (current, previous)
    return changes
