# 项目入口重构的提交与同步

1. 授权：沿用本任务“提交主main 推送 同步到coachos”的要求；用户已批准本次入口拆分方案，并选择“1. 允许一名只读子代理审查”。仅授权当前确定范围的一名审查者，无嵌套委派、分支删除、强推、部署或 release。
2. 源基线：sumulige/sumulige-coding-agent-workflow 的 main 717ff71cb1d806b2a960623f02e8d8e9002b10ca；最新 fetch 后与 origin/main 一致，暂存区为空。11 份实现文件按 checks.json 固定候选，其他文件仅为本目录方案和证据。
3. 源提交范围：AGENTS.md、README.md、CHANGELOG.md、docs/agent/workflow.md、tooling.md、maintenance.md、reference/engineering.md、reference/resources.md、templates/core/.agent/project-rules.md、validation/check_bundle.py、validation/tests/test_managed.py，以及本目录八份记录和可重现脚本。正文与证据保持同一候选，超过 300 行的范围理由见 plan.md。
4. 目标基线：sumulige/coachOS 的 main ac0cd64ecf7d9ec50e6448cda4151371284ffead；既有产品资料持续由其他工作编辑。只按声明的治理路径做事务更新和提交；不要求整个产品工作区静止或干净。
5. 目标范围：预览确认的 AGENTS.md、docs/agent/workflow.md、tooling.md、maintenance.md、reference/engineering.md、reference/resources.md、validation/check_bundle.py、.agent/workflow-lock.json；另更新 .agent/project-rules.md、docs/DEVELOPMENT.md 的固定来源与资源入口引用，以及 docs/changes/2026-09-entry-routing-sync/ 的同步证据。
6. 路径：独立审查确定候选 → 必要修订及受影响检查 → 精确提交并推送源 main → 导出并核对固定提交 → 目标安装与元数据备份事务 → 安装、ready、任务/TODO、重复安装、回滚预览与配置 lint/test → 精确提交并推送目标 main → 两端远端 SHA 与 CI 核对。
7. 回退：目标先预览元数据、再预览 managed 事务；文件已被后续编辑则保留冲突，不自动覆盖。远端历史通过另行授权的 revert 恢复，不改写已推送历史。
8. 验收边界：独立规范与需求审查单列，原生客户端行为仍 UNKNOWN；本次无产品实现，配置 lint/test 是既有回归，不是产品需求完成证明。CI 按实际候选与步骤核对，目标无 CI 时如实记录。

发布后精确提交与远端事实由本次会话最终交付记录保存；提交生成前不填写推测 SHA。
