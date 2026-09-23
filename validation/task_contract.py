"""Check contract v2: declarations and derived results, never executes commands."""
from __future__ import annotations

import re
import shlex

from check_bundle import CONFIG_PATH, safe_relative, strict_json, validate_config
from storage import digest, encoded, read_file

STATES = ("VERIFIED", "PARTIAL", "FAILED", "UNKNOWN")
LAYERS = ("static", "unit", "integration", "runtime", "visual", "native", "external", "ci", "release")


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value) is not None


def words(value):
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def exact(value, fields, context):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(f"Invalid {context} fields")


def fingerprint(contract):
    return digest(encoded(contract))


def sha256(value, empty=False):
    return isinstance(value, str) and ((empty and value == "") or re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def project_checks(root):
    data = read_file(root, CONFIG_PATH)
    if data is None:
        return "", []
    config = strict_json(data.decode())
    errors = validate_config(config, root)
    if errors:
        raise ValueError("Invalid project configuration: " + "; ".join(errors))
    if config["status"] != "configured":
        return "", []
    checks = []
    for name, layer, count in (("lint", "static", None), ("test", "unit", 1)):
        command = shlex.split(config[name + "_command"])
        if any(arg in ("&&", "||", ";", "|", ">", ">>", "<", "&") for arg in command):
            raise ValueError("Configured commands need explicit argv; declare sh -c explicitly for shell syntax")
        checks.append({"id": name, "description": f"Configured {name} command", "required": True,
                       "layer": layer, "command": command, "cwd": config["working_directory"], "min_count": count})
    return digest(data), checks


def new_contract(root, kind, basis, checks_path=None):
    project, checks = project_checks(root) if kind == "code" else ("", [])
    if checks_path is not None:
        data = read_file(root, checks_path)
        if data is None:
            raise ValueError("Checks file does not exist")
        checks = strict_json(data.decode())
    contract = {"kind": kind, "basis": basis, "project_sha256": project, "checks": checks}
    validate_contract(contract)
    return contract


def validate_contract(contract):
    exact(contract, "kind basis project_sha256 checks", "contract")
    if contract["kind"] not in ("code", "maintenance") or not words(contract["basis"]):
        raise ValueError("Contract requires task kind and change basis")
    if not sha256(contract["project_sha256"], empty=True):
        raise ValueError("Invalid project fingerprint")
    if not isinstance(contract["checks"], list):
        raise ValueError("Checks must be an array")
    seen = set()
    for check in contract["checks"]:
        exact(check, "id description required layer command cwd min_count", "check")
        if not identifier(check["id"]) or check["id"] in seen or not words(check["description"]):
            raise ValueError("Invalid or duplicate check id/description")
        seen.add(check["id"])
        if type(check["required"]) is not bool or check["layer"] not in LAYERS:
            raise ValueError("Invalid check requirement/layer")
        if (not isinstance(check["command"], list) or not check["command"]
                or not all(isinstance(arg, str) and "\x00" not in arg for arg in check["command"])
                or not check["command"][0] or not safe_relative(check["cwd"], directory=True)):
            raise ValueError("Invalid check command/cwd")
        count = check["min_count"]
        if check["layer"] in ("unit", "integration"):
            if type(count) is not int or count < 1:
                raise ValueError("Test check needs a positive minimum observed count")
        elif count is not None:
            raise ValueError("Only test checks declare min_count")


def matching_check(record, check_id, layer, command, cwd):
    check = next((c for c in record["contract"]["checks"] if c["id"] == check_id), None)
    if check is None or (check["layer"], check["command"], check["cwd"]) != (layer, command, cwd):
        raise ValueError("Check command/layer/cwd differs from the declared contract")
    return check


def current_runs(record):
    latest = {}
    stamp = fingerprint(record["contract"])
    for item in record["evidence"]:
        if item["candidate"] != record["candidate"] or item["contract"] != stamp or item["outcome"] == "legacy":
            continue
        key = ("check", item["check_id"]) if item["check_id"] else (item["layer"], tuple(item["command"]), item["cwd"])
        latest[key] = item
    return latest


def execution_status(outcome, code, layer, count):
    if outcome in ("unavailable", "legacy"):
        return "UNKNOWN"
    if outcome == "timeout" or code != 0:
        return "FAILED"
    if layer in ("unit", "integration"):
        return "UNKNOWN" if count is None else "PARTIAL" if count == 0 else "VERIFIED"
    return "VERIFIED"


def validate_execution(item, record):
    outcome = item["outcome"]
    if (outcome not in ("exited", "timeout", "unavailable", "observed", "legacy")
            or not sha256(item["contract"], empty=True) or not isinstance(item["check_id"], str)
            or (item["check_id"] and not identifier(item["check_id"]))):
        raise ValueError("Invalid execution outcome/check contract")
    if outcome == "legacy":
        if item["contract"] or item["check_id"]:
            raise ValueError("Legacy evidence cannot certify a v2 contract")
        return
    if not item["contract"]:
        raise ValueError("New evidence needs a contract fingerprint")
    code = item["exit_code"]
    if outcome in ("observed", "unavailable"):
        if code is not None or item["count"] is not None:
            raise ValueError("Non-execution cannot declare an exit code or test count")
        if outcome == "observed" and item["layer"] in ("unit", "integration"):
            raise ValueError("Test execution cannot be replaced by an observation")
    elif type(code) is not int or (outcome == "timeout" and code == 0):
        raise ValueError("Execution outcome conflicts with exit code")
    if outcome != "observed" and item["status"] != execution_status(outcome, code, item["layer"], item["count"]):
        raise ValueError("Evidence status conflicts with raw execution outcome")
    if item["contract"] == fingerprint(record["contract"]) and item["check_id"]:
        matching_check(record, item["check_id"], item["layer"], item["command"], item["cwd"])


def test_summary(record):
    current = current_runs(record)
    tests = [e for e in current.values() if e["layer"] in ("unit", "integration")]
    required = [c for c in record["contract"]["checks"] if c["required"] and c["layer"] in ("unit", "integration")]
    if any(("check", c["id"]) not in current for c in required) or any(e["status"] == "UNKNOWN" for e in tests):
        return "UNKNOWN"
    if any(e["outcome"] == "timeout" for e in tests):
        return "TIMEOUT"
    if any(e["status"] == "FAILED" for e in tests):
        return "RED"
    if any((current[("check", c["id"])]["count"] or 0) < c["min_count"] for c in required):
        return "UNTESTED"
    if tests and all(e["status"] == "VERIFIED" for e in tests):
        return "GREEN"
    if not tests and any(e["outcome"] == "legacy" and e["candidate"] == record["candidate"]
                         and e["layer"] in ("unit", "integration") for e in record["evidence"]):
        return "UNKNOWN"
    return "UNTESTED"


def check_completion(record, root, *, current_project=True):
    contract = record["contract"]
    checks = {c["id"]: c for c in contract["checks"]}
    if contract["kind"] == "code" and current_project:
        project, defaults = project_checks(root)
        if not project or project != contract["project_sha256"]:
            raise ValueError("COMPLETE needs current configured project checks; refresh the contract")
        for default in defaults:
            check = checks.get(default["id"])
            if (not check or not check["required"] or any(check[k] != default[k] for k in ("layer", "command", "cwd"))):
                raise ValueError("COMPLETE needs required configured lint/test checks")
    current = current_runs(record)
    for check in checks.values():
        if not check["required"]:
            continue
        run = current.get(("check", check["id"]))
        if (run is None or run["status"] != "VERIFIED"
                or (check["min_count"] is not None and (run["count"] or 0) < check["min_count"])
                or (contract["kind"] == "code" and check["id"] in ("lint", "test") and run["outcome"] != "exited")):
            raise ValueError("COMPLETE requires a successful current required check: " + check["id"])


def reset_acceptance(record):
    for criterion in record["acceptance"]:
        criterion.update(status="UNKNOWN", evidence=[])
    record["review"].update(status="UNKNOWN", reviewer="", reference="", candidate="", contract="")
    record["status"] = "PARTIAL"
    record["next"] = "核对当前契约，重新运行必需检查并完成验收与独立审查"
