# Change Record — coding workflow implementation

1. State：EVIDENCE_READY。Objective：把 v2.2 候选实现为跨客户端编码工作流分发包。
2. Scope：本仓库规则、文档、模板、Python 工具与测试；sumulige-claude 不动。
3. Baseline：feat/workflow-v2.2-hardening / 44e7a80f65aa30f2a237c5b740bc5e69e090dc3b。分支 codex/coding-agent-workflow。
4. Authorization：用户确认定位、文档组合、统一来源、保守升级与证据边界后要求“帮我实施”，随后明确要求“完成了验证了就提交推送”。本地实现、验证、提交及本任务分支推送获授权；真实全局配置、远端改名、合并及发布仍分别过门。
5. Contract：新增公共 CLI、task/lock schema v1；消费者为维护者与 AI。新增合约，不改变 v2.2 project.json 和旧安装器语义。0 成功、1 校验/冲突/执行失败、2 参数错误；默认预览，--apply 写入。
6. Acceptance：模板可安装；已有事实保留；规则升级冲突保护且可回退；错误/未知/零测试不冒充通过；TODO 可派生；七客户端差异明确；原仓库无改动。
7. Recovery：先备份，记录预期前后字节；回退拒绝后续编辑。无 force、无自动删除旧版本。
8. Assumptions：Python 3.10+、可信且无并发修改目录、标准 home 布局；自定义客户端目录人工整合。DRAFT 模板不是项目事实。
9. UNKNOWN：真实客户端加载与行为、中断跨客户端接力、成本收益、独立审查、新候选 CI/发布。
10. Review：主会话自检，未启动子 Agent；独立审查待执行。
11. Plan：模板/安装 → 任务证据 → 七客户端 → 回归/故障检查 → 交付记录 → 独立审查与远端确认。
12. Owner：primary-agent。Last verified：2026-09-23。

本地结果与证据在同目录 task.json、checks.log、bundle.json、inputs.json、review.md。
新候选的远端 CI/发布不能沿用 v2.2 的结果；未独立审查与未跑原生客户端的状态继续保留。
