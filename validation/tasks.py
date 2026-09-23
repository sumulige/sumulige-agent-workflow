#!/usr/bin/env python3
"""Create/check task receipts, capture explicit commands, and derive TODO.

Check and TODO preview never write or execute project commands. Python 3.10+.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import uuid
from pathlib import Path

sys.dont_write_bytecode = True

from check_bundle import local_path, safe_relative, strict_json
from storage import digest, encoded, read_file, replace_file

STATES = ("VERIFIED", "PARTIAL", "FAILED", "UNKNOWN")
LAYERS = ("static", "unit", "integration", "runtime", "visual", "native", "external", "ci", "release")
FIELDS = {"schema_version", "id", "title", "objective", "source", "scope", "authorization",
          "candidate", "implementer", "status", "test_status", "release", "review",
          "acceptance", "evidence", "next"}
START, END = "<!-- workflow:tasks:start -->", "<!-- workflow:tasks:end -->"


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value) is not None


def words(value):
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def exact(value, fields, context):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(f"Invalid {context} fields")


def validate(record, root: Path):
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("Task keys must match schema_version 1")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1 or not identifier(record["id"]):
        raise ValueError("Invalid task schema/id")
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
    exact(record["release"], "status reference", "release")
    release = record["release"]
    if release["status"] not in ("UNRELEASED", "RELEASED") or not isinstance(release["reference"], str):
        raise ValueError("Invalid release status")
    if release["status"] == "RELEASED" and not words(release["reference"]):
        raise ValueError("RELEASED requires a separate release reference")
    exact(record["review"], "required status reviewer reference candidate", "review")
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
    if not isinstance(record["evidence"], list):
        raise ValueError("Evidence must be an array")
    evidence = {}
    for item in record["evidence"]:
        exact(item, "id layer status candidate command cwd exit_code count artifact sha256", "evidence")
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
    tests = current_tests(record)
    if record["test_status"] == "GREEN" and (not tests or any(e["status"] != "VERIFIED" for e in tests)):
        raise ValueError("GREEN requires current, successful, nonzero test evidence")
    if record["test_status"] == "UNTESTED" and any(e["count"] != 0 or e["exit_code"] != 0 for e in tests):
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
    if record["status"] == "COMPLETE":
        if (not words(record["candidate"]) or not any(c["required"] for c in record["acceptance"])
                or any(c["required"] and c["status"] != "VERIFIED" for c in record["acceptance"])
                or record["test_status"] in ("RED", "TIMEOUT")
                or (review["required"] and review["status"] != "VERIFIED")):
            raise ValueError("COMPLETE requires all required acceptance and independent review evidence")
    elif not words(record["next"]):
        raise ValueError("Unfinished task requires a next action")


def current_tests(record):
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
        lines.append("| " + " | ".join([link + " " + escape(record["title"]), record["status"],
                     record["test_status"], record["release"]["status"], escape(record["next"])]) + " |")
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
    record = {"schema_version": 1, "id": args.id, "title": args.title,
              "objective": args.objective, "source": args.source, "scope": args.scope,
              "authorization": args.authorization, "candidate": "", "implementer": args.implementer,
              "status": "PARTIAL", "test_status": "UNTESTED",
              "release": {"status": "UNRELEASED", "reference": ""},
              "review": {"required": True, "status": "UNKNOWN", "reviewer": "", "reference": "", "candidate": ""},
              "acceptance": [{"id": f"ac-{index}", "description": item, "required": True,
                              "status": "UNKNOWN", "evidence": []} for index, item in enumerate(args.acceptance, 1)],
              "evidence": [], "next": "确认验收并在已授权范围内实施"}
    validate(record, args.root)
    if args.apply:
        replace_file(args.root, f"docs/changes/{args.id}/task.json", None, encoded(record))
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
    if record["id"] != args.id:
        raise ValueError("Task id mismatch")
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
            code = 127
    if record["candidate"] != args.candidate:
        for criterion in record["acceptance"]:
            criterion.update(status="UNKNOWN", evidence=[])
        record["review"].update(status="UNKNOWN", reviewer="", reference="", candidate="")
    record["candidate"] = args.candidate
    verified = code == 0 and (args.layer not in ("unit", "integration") or (args.count or 0) > 0)
    status = "UNKNOWN" if unavailable else "VERIFIED" if verified else "FAILED" if code != 0 else "PARTIAL"
    record["evidence"].append({"id": evidence_id, "layer": args.layer, "status": status,
                              "candidate": args.candidate, "command": command, "cwd": args.cwd,
                              "exit_code": code, "count": args.count, "artifact": log,
                              "sha256": digest(destination.read_bytes())})
    tests = current_tests(record)
    record["test_status"] = ("TIMEOUT" if timed_out and args.layer in ("unit", "integration") else
                             "RED" if any(e["status"] == "FAILED" for e in tests) else
                             "GREEN" if tests and all(e["status"] == "VERIFIED" for e in tests) else
                             "UNTESTED" if tests and all(e["count"] == 0 and e["exit_code"] == 0 for e in tests) else
                             "UNKNOWN" if tests else "UNTESTED")
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
    for name in ("create", "check", "todo", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("--root", type=Path, default=Path.cwd())
        if name in ("create", "todo", "run"):
            sub.add_argument("--apply", action="store_true")
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
    args = parser.parse_args(arguments)
    try:
        args.root = args.root.resolve()
        if not args.root.is_dir():
            raise ValueError("Project root must exist")
        if command and args.action != "run":
            raise ValueError("Only run accepts a command after --")
        if args.action == "create":
            create(args)
        elif args.action == "check":
            print(f"VALID: {len(records(args.root))} task records; structural evidence checks only")
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
