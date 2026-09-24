#!/usr/bin/env python3
"""Read-only structural/configuration checks; never execute project commands.

Python 3.10+, standard library only. This is not a sandbox or a semantic proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIG_PATH = "docs/agent/project.json"
CORE_FILES = (
    "AGENTS.md", "CLAUDE.md", CONFIG_PATH,
    "docs/agent/project.md", "docs/agent/workflow.md",
    "docs/agent/testing.md", "docs/agent/tooling.md",
    "docs/agent/scenarios.md", "docs/agent/clients.md",
    "docs/agent/maintenance.md",
    "docs/agent/reference/engineering.md", "docs/agent/reference/resources.md",
    "docs/specs/_TEMPLATE/requirements.md",
    "docs/specs/_TEMPLATE/design.md", "docs/specs/_TEMPLATE/tasks.md",
    "docs/adr/0000-template.md", ".agent/memory.example.md",
    "validation/check_bundle.py",
)
DEFAULT_CONFIG = {
    "schema_version": 1,
    "status": "unconfigured",
    "test_command": "",
    "lint_command": "",
    "working_directory": ".",
    "protected_paths": ["AGENTS.md", "CLAUDE.md", "docs/agent/", "validation/", ".github/"],
    "timeout_seconds": 600,
    "commit_policy": "explicit-request",
    "memory_policy": "suggest-only",
}
TEST_STATES = ("GREEN", "RED", "UNTESTED", "TIMEOUT", "UNKNOWN")
TASK_STATES = ("COMPLETE", "PARTIAL", "BLOCKED")


def strict_json(text: str) -> Any:
    """Reject duplicate keys and non-JSON numeric constants, including nested ones."""
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError("Non-JSON numeric constant")

    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)


def safe_relative(value: Any, *, directory: bool = False) -> bool:
    """Only literal repository-relative POSIX paths; no globs or traversal."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if directory and value == ".":
        return True
    if any(c in value for c in "\\:*?[]\x00\r\n") or value.startswith("/"):
        return False
    parts = value.removesuffix("/").split("/")
    return all(part not in ("", ".", "..") for part in parts)


def local_path(root: Path, relative: str) -> Path:
    """Reject every symlink component rather than following it while checking."""
    if not safe_relative(relative, directory=True):
        raise ValueError("Invalid relative path")
    path = root
    if relative != ".":
        for part in relative.removesuffix("/").split("/"):
            path = path / part
            if path.is_symlink():
                raise ValueError("Symlink path is not accepted")
    return path


def validate_config(config: Any, root: Path, *, ready: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(config, dict):
        return ["project must be a JSON object"]
    if set(config) != set(DEFAULT_CONFIG):
        errors.append("project keys must match schema_version 1 exactly")
    if type(config.get("schema_version")) is not int or config.get("schema_version") != 1:
        errors.append("schema_version must be integer 1")
    if config.get("status") not in ("unconfigured", "configured"):
        errors.append("status must be exactly unconfigured or configured")
    if ready and config.get("status") != "configured":
        errors.append("project is not configured")
    for field in ("test_command", "lint_command"):
        command = config.get(field)
        if not isinstance(command, str) or any(c in command for c in "\x00\r\n"):
            errors.append(f"{field} must be a single-line string")
        elif config.get("status") == "configured" and not command.strip():
            errors.append(f"{field} must be nonempty when configured")
    timeout = config.get("timeout_seconds")
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        errors.append("timeout_seconds must be an integer in 1..3600")
    paths = config.get("protected_paths")
    if not isinstance(paths, list) or not paths or not all(safe_relative(p) for p in paths):
        errors.append("protected_paths must be a nonempty list of literal relative paths")
    elif len(set(paths)) != len(paths):
        errors.append("protected_paths must not contain duplicates")
    else:
        for required in ("AGENTS.md", "CLAUDE.md", "docs/agent/", "validation/", ".github/"):
            if required not in paths:
                errors.append(f"protected_paths must include {required}")
    cwd = config.get("working_directory")
    if not safe_relative(cwd, directory=True):
        errors.append("working_directory must be a literal relative directory")
    else:
        try:
            path = local_path(root, cwd)
            if ready and not path.is_dir():
                errors.append("working_directory does not exist as a directory")
        except (OSError, ValueError):
            errors.append("working_directory must not traverse symlinks")
    if config.get("commit_policy") not in ("explicit-request", "after-validation"):
        errors.append("invalid commit_policy")
    if config.get("memory_policy") not in ("suggest-only", "append-authorized"):
        errors.append("invalid memory_policy")
    return errors


def validate_bundle(root: Path, mode: str = "bundle") -> dict[str, Any]:
    """Check declared files only. Never crawl secrets or run configured commands."""
    if mode not in ("bundle", "ready"):
        raise ValueError("Unknown validation mode")
    root = root.resolve()
    checks: list[dict[str, Any]] = []
    texts: dict[str, str] = {}
    fingerprints: dict[str, str] = {}

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "result": "pass" if ok else "fail", "detail": detail})

    check("root.directory", root.is_dir())
    for relative in CORE_FILES:
        try:
            path = local_path(root, relative)
            if not path.is_file():
                raise ValueError("Missing regular file")
            data = path.read_bytes()
            text = data.decode("utf-8")
            if not re.sub(r"<!--.*?-->", "", text, flags=re.S).strip():
                raise ValueError("Empty document")
            texts[relative] = text
            fingerprints[relative] = hashlib.sha256(data).hexdigest()
            check(f"file:{relative}", True)
        except (OSError, UnicodeError, ValueError) as error:
            check(f"file:{relative}", False, type(error).__name__)

    if CONFIG_PATH in texts:
        try:
            config = strict_json(texts[CONFIG_PATH])
            errors = validate_config(config, root, ready=mode == "ready")
            check("project.schema", not errors, "; ".join(errors))
        except ValueError:
            check("project.schema", False, "Invalid JSON or duplicate keys")

    agents = texts.get("AGENTS.md", "")
    for number in range(1, 10):
        marker = f"<!-- HR-{number} -->"
        pattern = rf"^<!-- HR-{number} --> \*\*HR-{number}\*\* (.+)$"
        matches = re.findall(pattern, agents, flags=re.M)
        body = re.sub(r"<!--.*?-->", "", matches[0]).strip() if len(matches) == 1 else ""
        check(f"agents.HR-{number}.body", agents.count(marker) == 1 and bool(body))
    for relative, text in texts.items():
        if not relative.endswith(".md"):
            continue
        # A limited inline-link check, not a full Markdown parser or URL checker.
        without_code = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", without_code):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            try:
                parent = Path(relative).parent
                destination = (root / parent / target).resolve()
                rel = destination.relative_to(root).as_posix()
                check(f"link:{relative}:{target}", local_path(root, rel).exists())
            except (OSError, ValueError):
                check(f"link:{relative}:{target}", False, "Outside root or invalid path")
    testing = texts.get("docs/agent/testing.md", "")
    for state in TEST_STATES + TASK_STATES:
        check(f"testing.state:{state}", f"`{state}`" in testing)
    check("claude.import", "@AGENTS.md" in texts.get("CLAUDE.md", "").splitlines())
    failed = sum(item["result"] == "fail" for item in checks)
    return {
        "mode": mode, "total": len(checks), "fail": failed,
        "scope": "static structure/configuration only; no command or agent execution",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "input_sha256": fingerprints, "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--mode", choices=("bundle", "ready"), default="bundle")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout, never write a file")
    args = parser.parse_args(argv)
    report = validate_bundle(args.root, args.mode)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            print(f"[{item['result'].upper()}] {item['check']} {item['detail']}")
        print(f"{report['total']} checks; {report['fail']} fail; mode={args.mode}")
        print(report["scope"])
    return 1 if report["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
