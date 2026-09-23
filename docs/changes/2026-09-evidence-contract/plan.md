# 完成判定与升级修复

- 状态：EVIDENCE_READY / PARTIAL（独立审查与原生试点待执行）；基线 main 538d7242b982b0249385882599eb1d567f8c6f49。
- 授权：最初“好”被自动审批认定不覆盖具体架构，补丁未落地；随后向用户提交 contract-proposal.md，用户明确回复“批准”，现按该具体方案实施。沿用本任务已有的验证后提交、分支推送授权，不把旧分支的合并授权扩展到本次 PR。
- 目标：必需检查失败、缺失、范围缩减、状态改成 UNKNOWN 均不能误完成；超时语义持久保存；发布绑定候选；项目定制后能继续升级。
- 范围：validation/tasks.py、任务契约模块、profiles.py、相关 CLI 回归测试、根入口和相关维护文档、项目扩展规则模板、本记录与 TODO。
- 非目标：全局安装、修改 sumulige-claude、模型调用、子 Agent、冷启动状态机、归档系统、全量七客户端评测、合并或发布。
- 兼容：task v2 为显式新契约；v1 保留历史只读校验，迁移先预览、备份原文并清空无法证明的验收。project.json 与安装锁仍为 v1。Python CLI/JSON 消费者与安装后的 CLI 均需回归。
- 模型细节：契约声明 kind、依据、项目配置指纹和固定检查集合；执行绑定候选、契约指纹、check_id、完整 argv/cwd、原始 outcome。契约改变使旧验收失效。哈希不能认证授权或测试语义。
- 必需验收：已复现五条反例；命令参数缩减不能替代完整检查；失败后同一契约成功重跑可恢复；文档观察可完成；配置检查不得被删；v1 迁移预览无副作用、备份可恢复；扩展规则跨升级/回退保留；安装后工具完整可运行。
- 方法：CLI 公共边界的临时项目回归；bundle、全部 unittest、tasks check、TODO --check、diff --check；再核实分支 HEAD 的实际 CI。
- 风险与回滚：严格 v2 字段改变消费者行为，保留 v1 读取及原文备份；共享规则仍拒绝就地定制，人工将自定义规则移至项目自有扩展文件后升级，无 force/adopt。
- 范围复核：预计超过 300 行。契约、迁移、安装分发和反例测试需要同一候选验证；不为行数拆散兼容性变更，无外部依赖。
- 独立审查 UNKNOWN：主会话自检不代替另一审查者；无子 Agent 授权。完成实现和本地验证后再交付具体审查对象。
- 接力试点：先完成修复，再确认第二个客户端与独立执行授权；仅查看本机安装状态不等于启动原生客户端验收。

## 实现与证据索引

1. UNKNOWN 掩盖失败的 v1 反例先失败，增加基于实际测试证据的 COMPLETE 校验后通过；原 v1 字段未改变。
2. 具体 v2 方案获批后，原草稿测试移回 validation/tests/test_contract.py。必需 lint、持久超时、发布候选、备份迁移、配置刷新、安装模块与扩展规则均执行了先失败后通过的回归。
3. 范围缩减、旧成功被后续失败替代、最低数量、无退出码的启动失败、异常输入及任务 ID 不符另有 CLI 反例。
4. 当前候选见 inputs.json：Git 基线加明确文件清单的 SHA-256；排除 docs/changes/ 的回执及生成 TODO，避免自引用。它是本次交付快照，不冒充通用 snapshot/handoff 工具。
5. task.json 使用新契约记录本地检查；checks.log 与 bundle.json 是实际命令输出。旧 docs/changes/2026-09-coding-workflow/task.json 保持 v1 历史，不自动迁移。
6. 主会话执行与自检，未调用子 Agent 或其他模型。独立审查仍为 UNKNOWN；后续需针对确切候选由另一执行者留下记录。

## 验收映射

| 验收 | 方法与证据 | 层级 |
|---|---|---|
| 完成约定与原始结果一致 | test_tasks/test_contract；checks.log | 本地 CLI 集成 |
| v1 预览、备份、恢复 | test_v1_migration_previews_then_backs_up_and_invalidates_old_claims | 临时项目，不是生产迁移 |
| 项目定制可持续升级 | test_extract_custom_rules_then_upgrade_twice_and_rollback_preserves_extension | 临时项目，两次升级加回退 |
| 安装包可以独立运行 | test_installed_task_cli_can_create_and_check_v2_without_source_imports | 安装后 CLI，无源仓库导入 |
| 规则与配置结构 | bundle.json；tasks check、TODO --check、diff --check | 静态与记录一致性 |
| GitHub CI | 按最终分支 SHA 查 Actions 实际 job/step；PR 中报告 | 与本地证据分开 |
| 独立审查 / 原生接力 | UNKNOWN；未以自身审查或临时项目替代 | 下一阶段 |

运行数量、候选和日志哈希以 task.json 与输出文件为准。即使本地检查通过，任务仍 PARTIAL，review.required=true 保留。未安装全局规则、未修改 sumulige-claude、未合并或发布。
