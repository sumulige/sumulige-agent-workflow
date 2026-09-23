# 开发流程

1. 环境与安装：依据 lockfile 和实际运行记录填写。
2. 启动、构建、lint、test：写明工作目录、前置条件和预期结果。
3. 任务：只读不落盘；小改动使用简短任务或现有 Issue；复杂变更使用 docs/changes/。
4. 文档维护：按 docs/agent/maintenance.md 随代码变更同步。
5. 交付：任务、测试、独立审查、CI 与发布分别报告。

机器命令唯一配置是 docs/agent/project.json，不另设配置状态。
