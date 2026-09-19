# project.md — 项目配置

```yaml
status: unconfigured        # unconfigured | configured
test_command: ""            # 例: pytest -q
lint_command: ""            # 例: ruff check .
protected_paths:            # 修改需人工确认
  - AGENTS.md
  - docs/agent/
  - .github/workflows/
timeout_seconds: 600
```

## 说明
- `status` 为 `unconfigured` 时代理只读。
- `test_command` 为空时，所有任务的测试状态记为 `UNKNOWN`。
