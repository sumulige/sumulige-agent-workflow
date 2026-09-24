# 核心工程原则与用户价值规则：main 提交和 Coach OS 同步

1. 目标与授权：用户于 2026-09-24 明确要求“提交主main 推送 同步到coachos”；将此前确认的核心工程原则、用户价值说明及情境与负担细化提交到工作流 main，再同步并提交推送 Coach OS main。此前各文档阶段的“不提交、不同步”是历史范围，本次授权增加上述交付动作。
2. 基线：工作流 main 为 f11e39a0d2b0539cc64a3d2004784d739ffab543；Coach OS main 为 fb930a42d3bde966a09686f58099aa3270f05d0c。两者 fetch 后均与 origin/main 无差异，暂存区均为空。Coach OS 产品文档有既有未提交成果。
3. 源码范围：AGENTS.md、CHANGELOG.md、README.md、docs/PROJECT-SPEC.md、docs/agent/workflow.md、docs/specs/_TEMPLATE/requirements.md、templates/core/docs/PROJECT-SPEC.md，以及核心工程和用户价值两个变更记录目录。正文目前新增 47 行、删除 2 行；含历史命令输出的证据可能超过 300 行，作为同一已确认规则变更保持内聚，不修改既有证据。
4. 路径：最终本地检查 → 精确暂存与提交 → 推送并核对远端 SHA → 从固定提交预览 Coach OS 分发 → 事务同步 managed 文件 → 更新本地来源说明 → 检查、精确提交和推送 → 核对两端引用与 CI。
5. Coach OS 范围：预览确定的 managed 规则与锁文件、.agent/project-rules.md 和 docs/DEVELOPMENT.md 的来源说明，以及 docs/changes/2026-09-user-value-sync/ 中的同步证据。现有 local 项目范围文件保留，不把初始化模板覆盖到产品规格。
6. 必需验收：源包结构、既有回归、任务/TODO、差异检查通过；目标安装检查、ready、任务/TODO、重复安装 UNCHANGED、回滚预览及配置的 lint/test 通过；提交路径符合范围；两仓库 local HEAD 与远端 main 相等。源 CI 核对实际候选与 job/step；目标若未配置 CI 如实记录。
7. 边界：不删除分支、不改写历史、不部署或发布 release，不修改产品实现、产品文档、依赖、全局配置或秘密。真实 Agent 遵循、原生客户端和独立审查未验证；当前仅验收文档治理与分发同步。
8. 风险与恢复：分发冲突或治理区域出现外部变更时停止该项并核实；保留既有产品工作。同步使用带备份的事务，先预览回滚，再按元数据、managed 安装的顺序恢复。远端已提交内容通过后续授权的 revert 恢复，不强推。

## 进展与证据

1. 已核对本地与远端基线、完整正文差异和两端暂存区；57 项结构检查、87 项既有回归、2 条任务记录校验、TODO 与差异检查全部通过，命令与输出见 publication-checks.json。
2. 后续同步及最终远端证据记录在 Coach OS 的 docs/changes/2026-09-user-value-sync/ 中；源提交自身不能包含其尚未生成的 SHA。
