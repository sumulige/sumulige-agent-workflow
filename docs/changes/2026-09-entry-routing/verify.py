"""Reproduce the split-entry upgrade and rollback with synthetic projects only."""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "717ff71cb1d806b2a960623f02e8d8e9002b10ca"
REFERENCES = ("docs/agent/reference/engineering.md", "docs/agent/reference/resources.md")


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()
            and ".agent/workflow-backups/" not in str(p.relative_to(root))}


def main():
    records = []

    def run(args, cwd):
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=600)
        records.append({"command": list(map(str, args)), "cwd": str(cwd),
                        "exit_code": result.returncode,
                        "output": result.stdout + result.stderr})
        if result.returncode:
            raise RuntimeError(records[-1])
        return result.stdout

    original = subprocess.check_output(["git", "show", BASE + ":AGENTS.md"], cwd=ROOT).decode()
    current = (ROOT / "AGENTS.md").read_text()
    old_engineering = original.split("**用户结果与价值优先：**", 1)[1].split("\n## 4. 测试", 1)[0].strip()
    new_engineering = (ROOT / REFERENCES[0]).read_text().split("**用户结果与价值优先：**", 1)[1].strip()
    assert old_engineering == new_engineering
    assert original.splitlines()[2:6] == current.splitlines()[2:6]
    assert [s for s in original.splitlines() if s.startswith("<!-- HR-")] == [
        s for s in current.splitlines() if s.startswith("<!-- HR-")]
    assert current.count("\n## ") == 2
    workflow = (ROOT / "docs/agent/workflow.md").read_text()
    for start, end in (("## 6. 架构决策", "## 7. 记忆"),
                       ("## 7. 记忆", "## 8. 报告格式"),
                       ("## 8. 报告格式", "## 9. 提交与独立审查"),
                       ("## 9. 提交与独立审查", "## 10. 冲突与暂停"),
                       ("## 10. 冲突与暂停", "## 11. 版本")):
        body = original.split(start + "\n\n", 1)[1].split("\n" + end, 1)[0].strip()
        body = body.replace("(docs/adr/", "(../adr/").replace("(.agent/", "(../../.agent/")
        assert body in workflow, start

    with tempfile.TemporaryDirectory(prefix="entry-routing-") as temp:
        base = Path(temp)
        legacy = base / "legacy"
        legacy.mkdir()
        archive = subprocess.check_output(["git", "archive", BASE], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            # The pinned repository archive is trusted; extraction stays in a new temp directory.
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in Path(member.name).parts or member.issym() or member.islnk():
                    raise ValueError("Unsafe archive member")
            tar.extractall(legacy)
        target = base / "project"
        target.mkdir()
        old_cli = [sys.executable, "-B", str(legacy / "validation/manage.py"), str(target)]
        new_cli = [sys.executable, "-B", str(ROOT / "validation/manage.py"), str(target)]
        run(old_cli + ["--apply"], ROOT)
        local = target / ".agent/project-rules.md"
        local.write_text("# Synthetic project facts\nKeep the project-owned resource index.\n")
        before = snapshot(target)
        preview = run(new_cli, ROOT)
        assert all("CREATE: " + name in preview for name in REFERENCES)
        assert snapshot(target) == before
        applied = run(new_cli + ["--apply"], ROOT)
        identifier = applied.split("TRANSACTION: ", 1)[1].strip()
        run(new_cli + ["--check"], ROOT)
        installed = run([sys.executable, "-B", str(target / "validation/check_bundle.py"), "--json"], target)
        assert all(name in json.loads(installed)["input_sha256"] for name in REFERENCES)
        assert all((target / name).read_bytes() == (ROOT / name).read_bytes() for name in REFERENCES)
        assert snapshot(target)[".agent/project-rules.md"] == before[".agent/project-rules.md"]
        backups = set((target / ".agent/workflow-backups").iterdir())
        assert "UNCHANGED" in run(new_cli + ["--apply"], ROOT)
        assert set((target / ".agent/workflow-backups").iterdir()) == backups
        upgraded = snapshot(target)
        run(new_cli + ["--rollback", identifier], ROOT)
        assert snapshot(target) == upgraded
        run(new_cli + ["--rollback", identifier, "--apply"], ROOT)
        assert snapshot(target) == before
        assert all(not (target / name).exists() for name in REFERENCES)
        run(old_cli + ["--check"], ROOT)
        receipt = json.loads((target / ".agent/workflow-backups" / identifier / "receipt.json").read_text())
    print(json.dumps({"base": BASE, "result": "VERIFIED", "records": records,
                      "preserved": ["top_test_principles", "HR-1..9", "user_value_and_ten_principles",
                                    "moved_workflow_clauses", "local_project_rules", "rollback_snapshot"],
                      "root_chars": {"before": len(original), "after": len(current)},
                      "transaction": receipt,
                      "boundary": "Synthetic CLI lifecycle and text preservation; native agent behavior UNKNOWN."},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
