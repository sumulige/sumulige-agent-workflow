# AGENTS.md — 根规则 v2.1

本文件对仓库内所有 AI 代理生效。冲突时以本文件为准。

## 0. 状态门
读取 `docs/agent/project.md` 的 `status` 字段：
- `unconfigured`：只读。禁止创建、修改、删除任何文件。
- `configured`：按本文件其余规则执行。

## 1. 必读顺序
1. `AGENTS.md`
2. `docs/agent/project.md`
3. `.agent/memory.md`（存在时）
4. 任务相关的 `docs/specs/<name>/` 三件

## 2. 硬规则
<!-- HR-1 --> **HR-1** 未通过状态门不得写入。
<!-- HR-2 --> **HR-2** 新功能必须先有 `requirements.md`，再写代码。
<!-- HR-3 --> **HR-3** 不得删除、跳过、注释掉现有测试以使其通过。
<!-- HR-4 --> **HR-4** 报告结果必须使用 `docs/agent/testing.md` 定义的五态之一，不得以 GREEN 之外的状态声称完成。
<!-- HR-5 --> **HR-5** 提交前必须运行 `lint_command` 与 `test_command`。
<!-- HR-6 --> **HR-6** 单次提交改动不超过 300 行（不含生成文件）；超过则拆分。
<!-- HR-7 --> **HR-7** 不得提交密钥、令牌、密码或 `.env` 文件。
<!-- HR-8 --> **HR-8** 不得 force push、不得改写已推送历史。
<!-- HR-9 --> **HR-9** `protected_paths` 内文件的修改需人工明确确认。

## 3. 流程
见 `docs/agent/workflow.md`。

## 4. 测试
见 `docs/agent/testing.md`。

## 5. 工具
见 `docs/agent/tooling.md`。

## 6. 架构决策
影响模块边界、数据模型、外部依赖的改动，先在 `docs/adr/` 新增 ADR。

## 7. 记忆
会话结束前将本次改动摘要写入 `.agent/memory.md`，格式见 `.agent/memory.example.md`。

## 8. 报告格式
每次任务结束输出：
```
STATUS: <GREEN|RED|UNTESTED|TIMEOUT|UNKNOWN>
CHANGED: <文件列表>
TESTS: <命令> -> <结果>
NEXT: <未完成项或 none>
```

## 9. 禁止事项
- 猜测文件内容；必须读取后再引用
- 在未运行命令的情况下声称命令已通过
- 修改本文件

## 10. 冲突处理
用户指令与硬规则冲突时，说明冲突并停止，等待人工决定。

## 11. 版本
v2.1 — 2026-09
