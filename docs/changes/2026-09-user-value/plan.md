# 用户价值优先的需求梳理

1. 目标：将已确认的用户结果与价值原则落到核心入口、需求流程和模板，使重要需求先说明用户场景、目标结果、依据与成本，再进入实施方案。
2. 授权：上轮提出核心原则正文及七项用户价值说明，用户回复“可以”。本轮仅落实这些文档要求，不把故事中的人物经历、收益或待验证痛点写成项目事实。
3. 基线：main 的 HEAD 为 f11e39a0d2b0539cc64a3d2004784d739ffab543；已有 AGENTS.md、README.md、CHANGELOG.md 和 docs/changes/2026-09-core-engineering/ 的未提交成果，继续保留。
4. 范围：AGENTS.md、README.md、CHANGELOG.md、docs/PROJECT-SPEC.md、docs/agent/workflow.md、docs/specs/_TEMPLATE/requirements.md、templates/core/docs/PROJECT-SPEC.md 和本目录。
5. 非目标：不修改 Python 工具、机器配置、依赖或产品实现，不新增采集、收费或指标系统，不操作全局配置、Coach OS、Git 提交、远端或分支。

## 实施与验收

1. 在原有十条原则之前加入已确认的用户价值总原则；十条正文和上轮证据保持原样。
2. 工作流程说明重要需求进入方案前应梳理用户价值；小改动可简写或引用现有记录，只读任务仍在会话中说明。
3. 需求模板增加用户与场景、当前做法、目标结果、证据与假设、最小解决方式、成本与取舍、验证与退出七项；项目初始化模板引用同一说明，不维护重复表格。
4. 项目范围、README 和变更记录同步说明该要求；模板保持 DRAFT，未验证信息和指标不得自动变为事实或批准。
5. 编辑完成后运行结构检查、现有 87 项回归、任务/TODO、差异检查；核对原十条与上轮证据指纹未变，保存命令、工作目录、退出码和输出。
6. 本次验收针对文档及分发工具回归，不声称用户收益、真实 Agent 遵循或原生客户端行为已验证。
7. 若涉及需求实质变更、权限扩大或同一区域外部编辑，先核实再处理。恢复只撤回本轮差异，不覆盖既有工作区成果。

## 进展

1. 已核实当前事实来源、现有模板及未提交成果，并保存前置指纹。
2. 已写入用户价值总原则和七项模板内容，流程与项目初始化模板引用同一需求说明；README、产品范围和 CHANGELOG 已同步。
3. 原十条原则及上轮证据的 SHA-256 比较一致；五项本地命令均退出 0，87 项既有回归通过。完整命令、输出、工作目录和差异指纹见 [checks.json](checks.json)。

## 本地交付（七项初版）

```text
TASK_STATUS: COMPLETE
CHANGED: 范围内 7 份规则与模板文档；本目录方案与验证记录
CHECKS: checks.json 中 5 项命令全部退出 0；现有回归执行并通过 87 项
TEST_STATUS: GREEN
EVIDENCE: checks.json 记录基线、既有改动指纹与当前正文差异指纹；用户收益与真实 Agent 行为未验证
AUTHORIZATION: 用户确认总原则及七项需求说明；仅本地文档维护
ACTORS: 实现与自检为当前 Codex 主会话；具体模型版本 unknown；无独立审查者
GIT: main，基线 f11e39a0d2b0539cc64a3d2004784d739ffab543；本轮及上轮核心原则改动均未提交
NEXT: none（本地文档维护范围）
```

## 情境与负担细化

1. 授权：用户确认四项补充——触发时刻、希望摆脱的负担、必须保留的控制，以及用真实使用行为验证负担是否减少。
2. 范围：仅细化需求模板的四个既有条目，在 workflow.md 补充假设核实与必要控制的边界，同步 CHANGELOG 和本记录；保留七项结构、原十条原则及既有证据。
3. 验证：本轮是低风险文案维护，以来源核对、七项结构、局部内容与链接检查、任务/TODO 和 git diff --check 验收；不新增单元测试，不把初版的 87 项回归结果当成本轮重新执行结果。
4. 当前进展：四个条目及流程边界已更新；七项结构与原十条原则编号保持。结构、任务/TODO 和差异四项检查均退出 0，证据见 [refinement-checks.json](refinement-checks.json)。

```text
TASK_STATUS: COMPLETE
CHANGED: 需求模板四个既有条目、workflow.md 一条边界、CHANGELOG 及本记录
CHECKS: refinement-checks.json 中 4 项命令全部退出 0；七项结构核对通过
TEST_STATUS: 不适用（纯文案细化，未改代码或测试；未重跑程序测试）
EVIDENCE: refinement-checks.json 的候选差异指纹、命令与输出；实际用户收益未验证
AUTHORIZATION: 用户确认四项情境与负担补充；仅本地文档维护
ACTORS: 当前 Codex 主会话实现与自检；具体模型版本 unknown；无独立审查者
GIT: main；当前及前两轮文档改动保持未提交
NEXT: none（本地文档细化范围）
```
