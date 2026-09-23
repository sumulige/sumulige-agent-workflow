#!/usr/bin/env python3
"""Create/check task receipts, capture explicit commands, and derive TODO.

Check and TODO preview never write or execute project commands. Python 3.10+.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path

sys.dont_write_bytecode = True

from check_bundle import local_path, safe_relative, strict_json
from storage import digest, encoded, read_file, replace_file, transaction
from task_contract import (LAYERS, STATES, check_completion, current_runs, exact, execution_status,
                           fingerprint, identifier, matching_check, new_contract, reset_acceptance,
                           test_summary, validate_contract, validate_execution, words)
FIELDS = {"schema_version", "id", "title", "objective", "source", "scope", "authorization",
          "candidate", "implementer", "status", "test_status", "release", "review",
          "acceptance", "evidence", "next"}
START, END = "<!-- workflow:tasks:start -->", "<!-- workflow:tasks:end -->"


def validate(record, root: Path, *, refreshing_contract=False):
    version = record.get("schema_version") if isinstance(record, dict) else None
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Task schema_version must be 1 or 2")
    if set(record) != ((FIELDS - {"release"}) | {"contract", "releases"} if version == 2 else FIELDS):
        raise ValueError("Task keys must match schema_version")
    if not identifier(record["id"]):
        raise ValueError("Invalid task schema/id")
    if version == 2:
        validate_contract(record["contract"])
    for key in ("title", "objective", "authorization", "implementer"):
        if not words(record[key]):
            raise ValueError(f"Task {key} is required")
    for key in ("source", "candidate", "next"):
        if not isinstance(record[key], str):
            raise ValueError(f"Task {key} must be text")
    if (not isinstance(record["scope"], list) or not record["scope"]
            or not all(safe_relative(path, directory=True) for path in record["scope"])):
        raise ValueError("Task scope must contain literal project-relative paths")
    if record["status"] not in ("COMPLETE", "PARTIAL", "BLOCKED"):
        raise ValueError("Invalid task status")
    if record["test_status"] not in ("GREEN", "RED", "UNTESTED", "TIMEOUT", "UNKNOWN"):
        raise ValueError("Invalid test status")
    if version == 1:
        exact(record["release"], "status reference", "release")
        release = record["release"]
        if release["status"] not in ("UNRELEASED", "RELEASED") or not isinstance(release["reference"], str):
            raise ValueError("Invalid release status")
        if release["status"] == "RELEASED" and not words(release["reference"]):
            raise ValueError("RELEASED requires a separate release reference")
    else:
        if not isinstance(record["releases"], list):
            raise ValueError("Releases must be an array")
        for release in record["releases"]:
            exact(release, "candidate reference", "release")
            if not isinstance(release["candidate"], str) or not words(release["reference"]):
                raise ValueError("Invalid release candidate/reference")
    exact(record["review"], "required status reviewer reference candidate" + (" contract" if version == 2 else ""), "review")
    review = record["review"]
    if type(review["required"]) is not bool or review["status"] not in STATES:
        raise ValueError("Invalid review status")
    if not all(isinstance(review[key], str) for key in ("reviewer", "reference", "candidate")):
        raise ValueError("Invalid review identity/reference")
    if review["status"] == "VERIFIED":
        if (not words(review["reviewer"]) or review["reviewer"] == record["implementer"]
                or not words(review["reference"]) or not record["candidate"]
                or review["candidate"] != record["candidate"]):
            raise ValueError("Independent review needs another reviewer, reference and matching candidate")
        if version == 2 and review["contract"] != fingerprint(record["contract"]):
            raise ValueError("Independent review must match the current check contract")
    if version == 2 and not isinstance(review["contract"], str):
        raise ValueError("Invalid review contract")
    if not isinstance(record["evidence"], list):
        raise ValueError("Evidence must be an array")
    evidence = {}
    for item in record["evidence"]:
        exact(item, "id layer status candidate command cwd exit_code count artifact sha256"
              + (" contract check_id outcome" if version == 2 else ""), "evidence")
        if not identifier(item["id"]) or item["id"] in evidence:
            raise ValueError("Invalid or duplicate evidence id")
        if item["layer"] not in LAYERS or item["status"] not in STATES or not words(item["candidate"]):
            raise ValueError("Invalid evidence layer/status/candidate")
        if (not isinstance(item["command"], list) or not item["command"]
                or not all(isinstance(arg, str) and "\x00" not in arg for arg in item["command"])
                or not item["command"][0]):
            raise ValueError("Evidence command must be an argv array (or explicit observation description)")
        if not safe_relative(item["cwd"], directory=True) or not safe_relative(item["artifact"]):
            raise ValueError("Invalid evidence path")
        if item["exit_code"] is not None and type(item["exit_code"]) is not int:
            raise ValueError("Invalid evidence exit code")
        if item["count"] is not None and (type(item["count"]) is not int or item["count"] < 0):
            raise ValueError("Invalid test count")
        artifact = read_file(root, item["artifact"])
        if artifact is None or not isinstance(item["sha256"], str) or digest(artifact) != item["sha256"]:
            raise ValueError("Evidence artifact is missing or changed")
        if item["status"] == "VERIFIED":
            if item["exit_code"] not in (0, None):
                raise ValueError("Failed command cannot be VERIFIED")
            if item["layer"] in ("unit", "integration") and (
                    item["exit_code"] != 0 or item["count"] is None or item["count"] < 1):
                raise ValueError("Verified tests need exit 0 and a positive observed test count")
        evidence[item["id"]] = item
        if version == 2:
            validate_execution(item, record)
    tests = current_tests(record)
    if version == 2 and record["test_status"] != test_summary(record):
        raise ValueError("Test summary differs from current execution evidence")
    if record["test_status"] == "GREEN" and (not tests or any(e["status"] != "VERIFIED" for e in tests)):
        raise ValueError("GREEN requires current, successful, nonzero test evidence")
    if version == 1 and record["test_status"] == "UNTESTED" and any(e["count"] != 0 or e["exit_code"] != 0 for e in tests):
        raise ValueError("UNTESTED conflicts with current test evidence")
    if record["test_status"] == "RED" and not any(e["status"] == "FAILED" for e in tests):
        raise ValueError("RED needs current failing test evidence")
    if not isinstance(record["acceptance"], list) or not record["acceptance"]:
        raise ValueError("Task requires acceptance criteria")
    seen = set()
    for criterion in record["acceptance"]:
        exact(criterion, "id description required status evidence", "acceptance")
        if (not identifier(criterion["id"]) or criterion["id"] in seen
                or not words(criterion["description"]) or type(criterion["required"]) is not bool
                or criterion["status"] not in STATES or not isinstance(criterion["evidence"], list)
                or not all(isinstance(ref, str) and ref in evidence for ref in criterion["evidence"])):
            raise ValueError("Invalid acceptance criterion or evidence reference")
        seen.add(criterion["id"])
        if criterion["status"] == "VERIFIED" and (not criterion["evidence"] or any(
                evidence[ref]["status"] != "VERIFIED" or evidence[ref]["candidate"] != record["candidate"]
                for ref in criterion["evidence"])):
            raise ValueError("Verified acceptance needs current VERIFIED evidence")
        if version == 2 and criterion["status"] == "VERIFIED" and any(
                evidence[ref] not in current_runs(record).values() for ref in criterion["evidence"]):
            raise ValueError("Verified acceptance needs the latest current contract evidence")
    if record["status"] == "COMPLETE":
        if version == 2:
            check_completion(record, root, current_project=not refreshing_contract)
        if (not words(record["candidate"]) or not any(c["required"] for c in record["acceptance"])
                or any(c["required"] and c["status"] != "VERIFIED" for c in record["acceptance"])
                or record["test_status"] in ("RED", "TIMEOUT")
                or any(item["status"] != "VERIFIED" for item in tests)
                or (review["required"] and review["status"] != "VERIFIED")):
            raise ValueError("COMPLETE requires all required acceptance and independent review evidence")
    elif not words(record["next"]):
        raise ValueError("Unfinished task requires a next action")


def current_tests(record):
    if record["schema_version"] == 2:
        return [e for e in current_runs(record).values() if e["layer"] in ("unit", "integration")]
    latest = {}
    for item in record["evidence"]:
        if item["candidate"] == record["candidate"] and item["layer"] in ("unit", "integration"):
            latest[(item["layer"], tuple(item["command"]), item["cwd"])] = item
    return list(latest.values())


def records(root: Path):
    folder = local_path(root, "docs/changes")
    if not folder.exists():
        return []
    results = []
    for directory in sorted(folder.iterdir()):
        if directory.is_symlink():
            raise ValueError("Task directory must not be a symlink")
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        relative = f"docs/changes/{directory.name}/task.json"
        data = read_file(root, relative)
        if data is None:
            continue  # Human-only / external-task records need no synthetic JSON mirror.
        record = strict_json(data.decode())
        validate(record, root)
        if record["id"] != directory.name:
            raise ValueError("Task id must match its directory")
        results.append(record)
    return results


def render_todo(items):
    def escape(text):
        return str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")
    if not items:
        return "暂无任务记录。\n"
    lines = ["| 任务 | 状态 | 测试 | 发布 | 下一步 |", "|---|---|---|---|---|"]
    for record in items:
        link = f"[{record['id']}](docs/changes/{record['id']}/task.json)"
        if record["schema_version"] == 1:
            release_status = "LEGACY RELEASED (candidate UNKNOWN)" if record["release"]["status"] == "RELEASED" else "UNRELEASED"
        else:
            release_status = "RELEASED" if record["candidate"] and any(
                release["candidate"] == record["candidate"] for release in record["releases"]) else "UNRELEASED"
        lines.append("| " + " | ".join([link + " " + escape(record["title"]), record["status"],
                     record["test_status"], release_status, escape(record["next"])]) + " |")
    return "\n".join(lines) + "\n"


def todo(root: Path, apply=False, check=False):
    body = render_todo(records(root))
    original = read_file(root, "TODO.md")
    text = original.decode() if original is not None else f"# 当前任务\n\n{START}\n{END}\n"
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) >= text.index(END):
        raise ValueError("TODO ownership markers missing/ambiguous; review and add markers before generation")
    begin, rest = text.split(START)
    _, end = rest.split(END)
    desired = (begin + START + "\n" + body + END + end).encode()
    if check and desired != original:
        raise ValueError("TODO is stale; preview then regenerate it")
    if apply:
        replace_file(root, "TODO.md", original, desired)
    else:
        print(desired.decode(), end="")


def create(args):
    if not identifier(args.id):
        raise ValueError("Use a lowercase task id with digits/hyphens, at most 64 characters")
    record = {"schema_version": 2, "id": args.id, "title": args.title,
              "objective": args.objective, "source": args.source, "scope": args.scope,
              "authorization": args.authorization, "candidate": "", "implementer": args.implementer,
              "status": "PARTIAL", "test_status": "UNTESTED",
              "releases": [],
              "review": {"required": True, "status": "UNKNOWN", "reviewer": "", "reference": "", "candidate": "", "contract": ""},
              "acceptance": [{"id": f"ac-{index}", "description": item, "required": True,
                              "status": "UNKNOWN", "evidence": []} for index, item in enumerate(args.acceptance, 1)],
              "evidence": [], "next": "确认验收并在已授权范围内实施"}
    record["contract"] = new_contract(args.root, args.kind, args.basis or args.authorization, args.checks)
    record["test_status"] = test_summary(record)
    validate(record, args.root)
    if args.apply:
        replace_file(args.root, f"docs/changes/{args.id}/task.json", None, encoded(record))
    else:
        print(encoded(record).decode(), end="")


def update_contract(args):
    if not identifier(args.id):
        raise ValueError("Invalid task id")
    relative = f"docs/changes/{args.id}/task.json"
    before = read_file(args.root, relative)
    if before is None:
        raise ValueError("Create a task first")
    record = strict_json(before.decode())
    # A formerly complete task must remain refreshable after its project config
    # changes. All record/evidence checks still run; the new contract resets claims.
    validate(record, args.root, refreshing_contract=args.action == "contract")
    if record["id"] != args.id:
        raise ValueError("Task id mismatch")
    if args.action == "migrate" and record["schema_version"] == 2:
        print("UNCHANGED: already schema_version 2")
        return
    if args.action == "contract" and record["schema_version"] != 2:
        raise ValueError("Migrate the v1 task before updating its contract")
    if args.action == "migrate":
        record["schema_version"] = 2
        release = record.pop("release")
        record["releases"] = ([{"candidate": "", "reference": release["reference"]}]
                              if release["status"] == "RELEASED" else [])
        for item in record["evidence"]:
            item.update(contract="", check_id="", outcome="legacy")
    record["contract"] = new_contract(args.root, args.kind, args.basis, args.checks)
    reset_acceptance(record)
    record["test_status"] = test_summary(record)
    validate(record, args.root)
    if args.apply:
        if args.action == "migrate":
            transaction_id = transaction(args.root, {relative: (before, encoded(record))})
            print(f"TRANSACTION: {transaction_id}")
        else:
            replace_file(args.root, relative, before, encoded(record))
    else:
        print(encoded(record).decode(), end="")


def run_command(args, command):
    if not identifier(args.id) or not words(args.candidate) or not command or not command[0]:
        raise ValueError("run requires a task id, candidate and command after --")
    if not 1 <= args.timeout <= 3600 or (args.count is not None and args.count < 0):
        raise ValueError("Timeout must be 1..3600 seconds and count nonnegative")
    relative = f"docs/changes/{args.id}/task.json"
    before = read_file(args.root, relative)
    if before is None:
        raise ValueError("Create a task record first")
    record = strict_json(before.decode())
    validate(record, args.root)
    if record["schema_version"] != 2:
        raise ValueError("Migrate the v1 task before running new commands")
    if record["id"] != args.id:
        raise ValueError("Task id mismatch")
    if args.check_id:
        matching_check(record, args.check_id, args.layer, command, args.cwd)
    cwd = local_path(args.root, args.cwd)
    if not cwd.is_dir():
        raise ValueError("Command working directory must exist")
    print(encoded({"cwd": str(cwd), "command": command, "candidate": args.candidate}).decode(), end="")
    if not args.apply:
        print("PREVIEW ONLY: command not executed; no files written")
        return 0
    evidence_id = "run-" + uuid.uuid4().hex
    log = f"docs/changes/{args.id}/{evidence_id}.log"
    destination = local_path(args.root, log)
    timed_out = False
    unavailable = False
    with destination.open("xb") as output:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=(os.name == "posix"))
            try:
                code = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                code = process.wait()
                output.write(b"\nWorkflow timeout reached; process terminated.\n")
        except OSError as error:
            unavailable = True
            output.write(f"Execution unavailable: {type(error).__name__}\n".encode())
            code = None
    reset_acceptance(record)
    record["candidate"] = args.candidate
    outcome = "unavailable" if unavailable else "timeout" if timed_out else "exited"
    count = None if unavailable else args.count
    status = execution_status(outcome, code, args.layer, count)
    record["evidence"].append({"id": evidence_id, "layer": args.layer, "status": status,
                              "candidate": args.candidate, "command": command, "cwd": args.cwd,
                              "exit_code": code, "count": count, "artifact": log,
                              "contract": fingerprint(record["contract"]), "check_id": args.check_id,
                              "outcome": outcome,
                              "sha256": digest(destination.read_bytes())})
    record["test_status"] = test_summary(record)
    record["status"] = "PARTIAL"
    record["next"] = "检查实际日志、核对验收并更新任务记录；不根据退出码自动宣告完成"
    validate(record, args.root)
    try:
        replace_file(args.root, relative, before, encoded(record))
    except (OSError, ValueError) as error:
        raise ValueError(f"Task update failed; captured log retained at {log}: {error}") from error
    print(f"CAPTURED: {log}; exit={code}; evidence={status}")
    return 0 if code == 0 else 1


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in arguments:
        separator = arguments.index("--")
        arguments, command = arguments[:separator], arguments[separator + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("create", "check", "todo", "run", "contract", "migrate"):
        sub = commands.add_parser(name)
        sub.add_argument("--root", type=Path, default=Path.cwd())
        if name in ("create", "todo", "run", "contract", "migrate"):
            sub.add_argument("--apply", action="store_true")
        if name in ("create", "contract", "migrate"):
            sub.add_argument("--kind", choices=("code", "maintenance"), default="code")
            sub.add_argument("--basis", required=name != "create")
            sub.add_argument("--checks", help="Project-relative JSON array of declared checks")
        if name in ("contract", "migrate"):
            sub.add_argument("id")
        if name == "todo":
            sub.add_argument("--check", action="store_true")
        if name == "create":
            sub.add_argument("id")
            for key in ("title", "objective", "authorization"):
                sub.add_argument("--" + key, required=True)
            sub.add_argument("--scope", action="append", required=True)
            sub.add_argument("--acceptance", action="append", required=True)
            sub.add_argument("--source", default="")
            sub.add_argument("--implementer", default="primary-agent")
        if name == "run":
            sub.add_argument("id")
            sub.add_argument("--candidate", required=True)
            sub.add_argument("--layer", choices=LAYERS, required=True)
            sub.add_argument("--cwd", default=".")
            sub.add_argument("--timeout", type=int, default=600)
            sub.add_argument("--count", type=int, help="Test count observed by operator; never inferred from exit 0")
            sub.add_argument("--check-id", default="", help="Exact declared check; omission is exploratory")
    args = parser.parse_args(arguments)
    try:
        args.root = args.root.resolve()
        if not args.root.is_dir():
            raise ValueError("Project root must exist")
        if command and args.action != "run":
            raise ValueError("Only run accepts a command after --")
        if args.action == "create":
            create(args)
        elif args.action in ("contract", "migrate"):
            update_contract(args)
        elif args.action == "check":
            items = records(args.root)
            legacy = sum(item["schema_version"] == 1 for item in items)
            print(f"VALID: {len(items)} task records; {legacy} legacy v1 (structural checks only); no identity/semantic certification")
        elif args.action == "run":
            return run_command(args, command)
        else:
            if args.check and args.apply:
                raise ValueError("--check and --apply cannot be combined")
            todo(args.root, args.apply, args.check)
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
