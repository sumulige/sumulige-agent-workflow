#!/usr/bin/env python3
"""agent-workflow-bundle 一致性自检。用法: python3 validation/check_bundle.py"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = [
    "README.md", "AGENTS.md",
    "docs/agent/project.md", "docs/agent/workflow.md",
    "docs/agent/testing.md", "docs/agent/tooling.md",
    "docs/specs/_TEMPLATE/requirements.md", "docs/specs/_TEMPLATE/design.md",
    "docs/specs/_TEMPLATE/tasks.md", "docs/adr/0000-template.md",
    ".agent/memory.example.md", "validation/check_bundle.py",
]
VAGUE = ["尽量", "可能", "大概", "适当", "尽快", "一般", "通常", "酌情"]
RULE_FILES = ["AGENTS.md", "docs/agent/workflow.md", "docs/agent/testing.md", "docs/agent/tooling.md"]
STATES = ["GREEN", "RED", "UNTESTED", "TIMEOUT", "UNKNOWN"]

results = []
def check(name, ok, level="fail", detail=""):
    results.append({"check": name, "result": "pass" if ok else level, "detail": detail})

def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()

for p in REQUIRED:
    check(f"exists:{p}", os.path.exists(os.path.join(ROOT, p)))

if os.path.exists(os.path.join(ROOT, "docs/agent/project.md")):
    pm = read("docs/agent/project.md")
    m = re.search(r"^status:\s*(\w+)", pm, re.M)
    check("project.status_present", bool(m))
    check("project.status_valid", bool(m) and m.group(1) in ("unconfigured", "configured"),
          detail=m.group(1) if m else "")
    for k in ("test_command", "lint_command", "protected_paths", "timeout_seconds"):
        check(f"project.field:{k}", re.search(rf"^{k}:", pm, re.M) is not None)

if os.path.exists(os.path.join(ROOT, "AGENTS.md")):
    ag = read("AGENTS.md")
    for i in range(1, 10):
        check(f"agents.HR-{i}", f"<!-- HR-{i} -->" in ag)
    check("agents.state_gate", "状态门" in ag)
    for s in STATES:
        check(f"agents.state:{s}", s in ag)

if os.path.exists(os.path.join(ROOT, "docs/agent/testing.md")):
    tm = read("docs/agent/testing.md")
    for s in STATES:
        check(f"testing.state:{s}", f"`{s}`" in tm)

for p in RULE_FILES:
    if os.path.exists(os.path.join(ROOT, p)):
        txt = read(p)
        n = sum(txt.count(w) for w in VAGUE)
        check(f"vague_words:{p}", n <= 5, level="warning", detail=f"count={n}")

fails = [r for r in results if r["result"] == "fail"]
warns = [r for r in results if r["result"] == "warning"]
for r in results:
    mark = {"pass": "OK  ", "fail": "FAIL", "warning": "WARN"}[r["result"]]
    print(f"[{mark}] {r['check']} {r['detail']}")
print(f"\n{len(results)} checks: {len(results)-len(fails)-len(warns)} pass, {len(fails)} fail, {len(warns)} warning")

os.makedirs(os.path.join(ROOT, "validation"), exist_ok=True)
with open(os.path.join(ROOT, "validation/results.json"), "w", encoding="utf-8") as f:
    json.dump({"total": len(results), "fail": len(fails), "warning": len(warns), "checks": results},
              f, ensure_ascii=False, indent=2)
sys.exit(1 if fails else 0)
