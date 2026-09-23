#!/usr/bin/env python3
"""Seven-client bootstrap preview and project loading diagnostics.

Native loading must be verified in each real client; this tool does not invoke AI.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from check_bundle import local_path, safe_relative, strict_json, validate_bundle
from profiles import VERSION
from storage import digest, encoded, read_file, rollback_plan, transaction

CLIENTS = ("codex", "claude-code", "cursor", "hermes", "pi", "gemini", "opencode")
NATIVE = {"codex": ".codex/AGENTS.md", "claude-code": ".claude/CLAUDE.md",
          "pi": ".pi/agent/AGENTS.md", "gemini": ".gemini/GEMINI.md",
          "opencode": ".config/opencode/AGENTS.md"}
PREFIX = ".config/sumulige-coding-agent-workflow"
LOCK = ".agent/workflow-global-lock.json"


def global_plan(source: Path, home: Path, clients):
    if not home.is_dir() or validate_bundle(source)["fail"]:
        raise ValueError("Home must exist and source bundle must validate")
    policy = local_path(source, "templates/global/AGENTS.md").read_bytes()
    central = f"{PREFIX}/versions/{VERSION}-{digest(policy)[:12]}/AGENTS.md"
    location = str(home / central)
    if any(c in location for c in "\n\r\x00"):
        raise ValueError("Home path must not contain control characters")
    files = {central: policy}
    for client in clients:
        if client in ("claude-code", "gemini"):
            # Native @ imports are interpreted by these two clients, not by all clients.
            text = f"# Shared coding workflow\n\n@../{central}\n"
        else:
            text = ("# Shared coding workflow\n\nFor coding tasks, read the shared entry at:\n"
                    f"{location}\n\nThen follow the actual project's AGENTS.md. "
                    "This is an instruction to read a file, not a native import directive.\n")
        path = NATIVE.get(client, f"{PREFIX}/manual/{client}.md")
        if client == "cursor":
            text += "\nManual setup: review this text in Cursor User Rules; IDE and CLI require separate checks.\n"
        if client == "hermes":
            text += "\nManual setup: use project AGENTS.md; verify .hermes.md / AGENTS.override.md precedence. Do not replace SOUL.md.\n"
        files[path] = text.encode()
    previous = read_file(home, LOCK)
    lock = strict_json(previous.decode()) if previous is not None else {"schema_version": 1, "files": {}}
    if (not isinstance(lock, dict) or set(lock) != {"schema_version", "files"}
            or type(lock["schema_version"]) is not int or lock["schema_version"] != 1
            or not isinstance(lock["files"], dict)):
        raise ValueError("Invalid global lock")
    for path, sha in lock["files"].items():
        if (not safe_relative(path) or not isinstance(sha, str) or len(sha) != 64
                or any(c not in "0123456789abcdef" for c in sha)):
            raise ValueError("Invalid global lock entry")
    entries, plan = dict(lock["files"]), []
    for path, data in files.items():
        current = read_file(home, path)
        if current == data:
            state = "SAME"
        elif current is None:
            state = "CONFLICT" if path in entries else "CREATE"
        elif digest(current) == entries.get(path):
            state = "UPDATE"
        else:
            state = "CONFLICT"
        plan.append((path, state, current, data))
        entries[path] = digest(data)
    desired_lock = encoded({"schema_version": 1, "files": entries})
    plan.append((LOCK, "SAME" if previous == desired_lock else "UPDATE" if previous else "CREATE",
                 previous, desired_lock))
    return plan


def diagnose(root: Path, clients):
    failed = False
    core = read_file(root, "AGENTS.md")
    if not core:
        print("MISSING: project AGENTS.md")
        failed = True
    for client in clients:
        warnings = []
        overrides = {"codex": ("AGENTS.override.md",),
                     "pi": ("AGENTS.override.md",),
                     "hermes": (".hermes.md", "HERMES.md", "AGENTS.override.md")}.get(client, ())
        for name in overrides:
            if read_file(root, name) is not None:
                warnings.append(f"{name} may shadow AGENTS.md")
        if client in ("claude-code", "gemini"):
            entry = "CLAUDE.md" if client == "claude-code" else "GEMINI.md"
            content = read_file(root, entry)
            if content is None or "@AGENTS.md" not in content.decode().splitlines():
                warnings.append(f"{entry} shared import missing; inspect native configuration")
        if client == "opencode" and read_file(root, "opencode.json") is not None:
            print("NOTE: inspect opencode.json instructions and permissions without overwriting them")
        print(f"{client}: " + ("; ".join(warnings) if warnings else "project entry present"))
        failed = failed or bool(warnings)
    print("SCOPE: static entry diagnostics only; native loading, ancestor/global precedence and execution permissions UNKNOWN")
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    check = subs.add_parser("check")
    check.add_argument("root", type=Path)
    install = subs.add_parser("global")
    install.add_argument("--home", type=Path, required=True, help="Explicit target home using standard client directories")
    install.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    install.add_argument("--apply", action="store_true")
    install.add_argument("--rollback", metavar="TRANSACTION_ID")
    for command in (check, install):
        command.add_argument("--clients", nargs="+", choices=CLIENTS, default=list(CLIENTS))
    args = parser.parse_args(argv)
    try:
        if args.action == "check":
            root = args.root.resolve()
            if not root.is_dir():
                raise ValueError("Project root must exist")
            return diagnose(root, args.clients)
        home = args.home.resolve()
        if not home.is_dir():
            raise ValueError("Home must exist")
        if args.rollback:
            changes = rollback_plan(home, args.rollback)
            for path, (before, after) in changes.items():
                if before != after:
                    print(f"RESTORE: {path}")
        else:
            plan = global_plan(args.source.resolve(), home, args.clients)
            for path, state, _, _ in plan:
                print(f"{state}: {path}")
            for client in args.clients:
                if client not in NATIVE:
                    print(f"MANUAL: {client} — review central manual snippet; no native global configuration is changed")
            if any(state == "CONFLICT" for _, state, _, _ in plan):
                raise ValueError("No writes: existing rules require reviewed manual integration")
            changes = {p: (before, after) for p, state, before, after in plan if state in ("CREATE", "UPDATE")}
        if args.apply:
            receipt = transaction(home, changes)
            print(f"TRANSACTION: {receipt}" if receipt else "UNCHANGED")
        else:
            print("PREVIEW ONLY: no writes; custom client home locations require manual integration")
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
