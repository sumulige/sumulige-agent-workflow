# 复杂任务先写方案：实施与同步记录

1. 目标：将用户确认的建立共识、同步背景、约束执行、持续留痕四项目标落到共享规则，提交推送 main，并同步到 Coach OS。
2. 授权：本会话先给出四项目标的优化表述，用户随后要求“提交推送就一个main 然后同步到coachos”。本轮直接使用 main，核实旧分支已合入后移除其本地与远端引用；不改写提交历史。
3. 基线：工作流 main 为 95669d7b47a905429383f3aaf3ca7840a65941c0；Coach OS main 为 88ca7547a8d3d6ce4e458265ff2efb5c2d8ef4bc。fetch 后均与 origin/main 一致。
4. 范围：工作流 AGENTS.md、README.md、CHANGELOG.md、docs/PROJECT-SPEC.md、docs/agent/workflow.md、docs/agent/maintenance.md 及本记录目录；Coach OS 仅相应 managed 文件、安装锁、当前来源说明与同步证据。
5. 非目标：不改产品、架构、数据模型、依赖、机器配置、测试实现、全局规则或发布 release。Coach OS 既有产品文档改动保留，不纳入本次提交。
6. 任务类型：已批准表述的文档与治理维护；不新增执行器或机器契约。主会话执行，自检不称独立审查；本次文档维护未要求独立审查验收。

## 执行顺序

1. 在根入口声明复杂任务先写方案，在 workflow.md 解释四项目标、方案内容与持续维护方式；同步项目说明和变更记录。
2. 完成全部文档修改后运行规则包结构、现有回归、任务/TODO 和差异检查，保存命令与结果；审核精确路径后提交推送工作流 main。
3. 用已提交的固定来源预览 Coach OS 升级；只接受预期 managed 文件及锁的变化。安装器备份后应用，更新本地来源说明。
4. 检查 Coach OS ready、安装归属、任务/TODO、重复安装、回退预览及现有 lint/test；确认产品文件字节未被本任务改动后按明确路径提交推送 main。
5. 核对两个仓库本地 HEAD 与远端 main、CI 和分支列表；删除旧分支前再次确认其提交为 main 的祖先。

## 验收与恢复

1. 四项目标与既有只读/授权边界一致：通过最终文档差异人工核对。只读复杂任务可在会话写方案，写入工作文件仍需授权。
2. 分发有效：规则包结构、87 项既有回归、任务/TODO、git diff --check；真实 Agent 行为和原生客户端遵循情况仍为 UNKNOWN。
3. 同步有效：Coach OS managed 文件与固定来源字节一致，安装锁检查通过，重复安装 UNCHANGED，回退预览可用；记录事务 ID。
4. 远端有效：两个 main 与相应本地 HEAD 一致；只剩 main 分支。工作流 CI 按提交核对，Coach OS CI 如不存在则如实记录。
5. 产品保护：同步前保存现有改动文件和保留产品/应用/复用目录的文件指纹，提交只包含工作流路径。浏览器 E2E 不适用于这次文档改动，不以单元回归代替其证据。
6. 停止条件：managed 漂移、同一文件并发编辑、未合入分支或远端前进时先保留现场并核实。恢复使用安装器事务预览；已推送内容如需撤回使用后续 revert，不强推。

## 已合入旧分支的恢复点

| 仓库 | 分支 | 原提交 |
|---|---|---|
| workflow | codex/coding-agent-workflow | 21d019da90fc6e9eaf3563fea6c1e4bdbf8f69e8 |
| workflow | codex/e2e-final-validation | 0c9bf4786d5bc46423f44130d7a6d6e1a082ff80 |
| workflow | codex/rename-workflow-docs | 1af70024e7ec7dfbf0230926a19b092cacf67f2c |
| workflow | codex/task-evidence-contract | f4ac31bbd946682229a7cf91e56321e9c1c7c2a0 |
| workflow | feat/workflow-v2.2-hardening | 44e7a80f65aa30f2a237c5b740bc5e69e090dc3b |
| coachOS | codex/coding-workflow-migration-20260923 | fdeff226c1e77ec1cf929520233662a4d0b390cb |

## 当前进展

1. 已核实两个仓库、远端、主分支及旧分支祖先关系；工作流干净，Coach OS 产品文档有既有改动。
2. 四项目标及维护要求已写入 6 份说明；结构检查、87 项回归、任务/TODO 和差异检查均退出 0，完整输出见 [checks.json](checks.json)。此为本地证据，不表示 CI 或原生行为通过。
3. Coach OS 升级预览仅更新 AGENTS.md、docs/agent/workflow.md、docs/agent/maintenance.md 和 .agent/workflow-lock.json；297 个产品/应用/复用文件已在本地保存前置指纹，另有 33 条既有工作区改动记录。
4. 下一步：提交推送工作流 main，再以该提交同步 Coach OS；后续同步与远端结果记录在 Coach OS 的 docs/changes/2026-09-plan-first-sync/。
