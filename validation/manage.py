#!/usr/bin/env python3
"""Preview/apply a pinned project distribution or safely roll back a transaction."""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from check_bundle import local_path, safe_relative, strict_json, validate_bundle
from profiles import PROFILES, VERSION, distribution
from storage import digest, encoded, read_file, rollback_plan, transaction

LOCK = ".agent/workflow-lock.json"


def load_lock(data: bytes | None):
    if data is None:
        return None
    lock = strict_json(data.decode())
    if (not isinstance(lock, dict) or set(lock) != {"schema_version", "version", "profile", "files"}
            or type(lock["schema_version"]) is not int or lock["schema_version"] != 1
            or not isinstance(lock["version"], str) or lock["profile"] not in PROFILES
            or not isinstance(lock["files"], dict)):
        raise ValueError("Invalid workflow lock")
    for path, entry in lock["files"].items():
        if (not safe_relative(path) or path == LOCK or path.startswith(".agent/workflow-backups/")
                or not isinstance(entry, dict) or set(entry) != {"sha256", "ownership"}
                or entry["ownership"] not in ("local", "managed")
                or not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in entry["sha256"])):
            raise ValueError("Invalid workflow lock entry")
    return lock


def project_plan(source: Path, target: Path, profile: str | None = None):
    if source == target or not target.is_dir():
        raise ValueError("Target must exist and differ from source")
    old_data = read_file(target, LOCK)
    old = load_lock(old_data)
    profile = profile or (old["profile"] if old else "core")
    if old and PROFILES.index(profile) < PROFILES.index(old["profile"]):
        raise ValueError("Profile removal requires a reviewed manual migration")
    files = distribution(source, profile)
    old_files = old["files"] if old else {}
    entries = dict(old_files)
    plan = []
    for path, (desired, ownership) in files.items():
        current = read_file(target, path)
        previous = old_files.get(path)
        if previous and previous["ownership"] != ownership:
            raise ValueError(f"Ownership migration requires manual review: {path}")
        if ownership == "local" and current is not None:
            state, desired = "LOCAL", current
        elif current is None:
            state = "CONFLICT" if previous else "CREATE"
        elif current == desired:
            state = "SAME"
        elif previous and digest(current) == previous["sha256"]:
            state = "UPDATE"
        else:
            state = "CONFLICT"
        plan.append((path, state, current, desired))
        entries[path] = {"sha256": digest(desired), "ownership": ownership}
    lock = encoded({"schema_version": 1, "version": VERSION, "profile": profile, "files": entries})
    plan.append((LOCK, "SAME" if lock == old_data else "UPDATE" if old else "CREATE", old_data, lock))
    return plan


def check_project(root: Path):
    lock = load_lock(read_file(root, LOCK))
    if lock is None:
        raise ValueError("No managed lock; use the legacy bundle checker or preview initialization")
    if validate_bundle(root)["fail"]:
        raise ValueError("Project core bundle failed structural checks")
    for relative, entry in lock["files"].items():
        content = read_file(root, relative)
        if content is None or not content.strip():
            raise ValueError(f"Missing or empty installed file: {relative}")
        if entry["ownership"] == "managed" and digest(content) != entry["sha256"]:
            raise ValueError(f"Managed rule drift (preserved, never auto-overwritten): {relative}")
        if not relative.endswith(".md"):
            continue
        text = re.sub(r"```.*?```", "", content.decode(), flags=re.S)
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", text):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            normalized = posixpath.normpath(posixpath.join(posixpath.dirname(relative), target))
            if not local_path(root, normalized).exists():
                raise ValueError(f"Broken local document link: {relative} -> {target}")
    print(f"VALID: {lock['profile']} profile, {lock['version']}; structural checks only")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true", help="Read-only installed-file, drift and local-link check")
    parser.add_argument("--rollback", metavar="TRANSACTION_ID")
    args = parser.parse_args(argv)
    try:
        target, source = args.target.resolve(), args.source.resolve()
        if not target.is_dir():
            raise ValueError("Target must be an existing directory")
        if args.check:
            if args.apply or args.rollback or args.profile:
                raise ValueError("--check cannot be combined with mutation options")
            check_project(target)
            return 0
        if args.rollback:
            if args.profile:
                raise ValueError("--profile does not apply to rollback")
            changes = rollback_plan(target, args.rollback)
            for path, (before, after) in changes.items():
                if before != after:
                    print(f"RESTORE: {path}")
        else:
            plan = project_plan(source, target, args.profile)
            for path, state, _, _ in plan:
                print(f"{state}: {path}")
            if any(state == "CONFLICT" for _, state, _, _ in plan):
                raise ValueError("No writes: resolve conflicts with a reviewed manual merge")
            changes = {path: (before, after) for path, state, before, after in plan if state in ("CREATE", "UPDATE")}
        if args.apply:
            identifier = transaction(target, changes)
            print(f"TRANSACTION: {identifier}" if identifier else "UNCHANGED")
        else:
            print("PREVIEW ONLY: no writes; review before --apply")
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
