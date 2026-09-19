# 四客户端接入：Cursor、Pi Coding Agent、Hermes Agent、Codex

本项目优先面向这四种客户端，共用根目录 AGENTS.md 与 docs/agent/，不维护四份规则正文。
这里的 Pi 指 Pi Coding Agent（原 badlogic/pi-mono，官方仓库现重定向到 earendil-works/pi）；
Hermes 指 NousResearch Hermes Agent，不指同名模型。用户安装版本、扩展、全局规则和后端均尚未核实。
官方资料核对：2026-09-19；资料支持不等于当前安装版本已验收，不自动安装、升级或改全局设置。

## 共同入口与安装边界

从目标仓库根目录打开或启动客户端，先使用[安全安装和配置说明](project.md)。
原生自动发现的是 AGENTS.md；其中指向的普通 Markdown 分册仍需 Agent 按需读取，
不能把 Markdown 链接或其他客户端的 @导入语法当作四种工具都支持的自动展开机制。
保留现有 CLAUDE.md 兼容入口，但这四种工具不依赖 Claude Code 才能工作。
本包不创建 .hermes.md、HERMES.md、AGENTS.override.md、.pi/SYSTEM.md 或任何客户端全局配置。
安装器只保证声明文件的创建/冲突检查，不检测宿主的覆盖规则、扩展、设置或真正生效的权限。
发现已有适配文件时先核实作用，不自动删除；必要合并须获得该文件的修改授权。

## Cursor

[官方规则说明](https://cursor.com/docs/rules) 支持根目录和子目录的 AGENTS.md；
本包不额外生成重复的 .cursor/rules/*.mdc。需要路径匹配等功能时再维护最小的局部规则。
检查项目/用户/团队规则和现有 .cursorrules 是否冲突；IDE Agent、CLI、云端分别记录运行模式。
不要把 Agent 规则的适用性扩大到 Tab 等所有功能，也不要把 IDE 权限配置直接视作 CLI 的配置。
[CLI 权限](https://cursor.com/docs/cli/reference/permissions) 与
[忽略文件](https://cursor.com/docs/reference/ignore-file) 各有边界；文件工具、终端、MCP 必须分别验收。

## Pi Coding Agent

[官方 README](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md) 说明：
启动时读取全局 ~/.pi/agent/ 和父目录至当前目录的上下文；不能假定只扫描 Git 根目录以内。
[上下文加载源码](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/core/resource-loader.ts)
在同目录优先选择 AGENTS.override.md，再选 AGENTS.md，之后才是 CLAUDE.md 等兼容名称。
本机旧版或分支版可能不同，记录实际版本；不用 --no-context-files，否则会关闭本包入口的发现。

项目信任控制的是项目设置/资源/扩展，不是对每条 bash 命令弹出审批。
Pi 核心不提供默认逐命令权限弹窗；扩展可执行代码，不能靠一句“只读”或计划文件形成隔离。
推荐在无生产秘密的独立工作区或容器中运行。只读复核可在确认本机参数支持后使用：

```bash
pi --tools read,grep,find,ls --no-extensions --no-skills --no-prompt-templates
```

这是缩减模型可用工具的例子，不是操作系统沙箱；仍须核实启动配置、显式扩展参数、网络和自动保存。
在原生启动信息中核对上下文文件；切换仓库或更新规则后重新核对，不凭旧会话记忆判断加载成功。

## Hermes Agent

[官方上下文说明](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)
把 .hermes.md / HERMES.md 作为高优先级专用入口；它们可能使 AGENTS.md 不再是选中的入口。
现行文档还列出 AGENTS.override.md。启动前核实当前目录、仓库目录链和实际选中的文件，
不要为了“适配 Hermes”新增一份只写 @AGENTS.md 的 .hermes.md 并假定它会自动导入。

上下文文件可能因注入扫描、长度限制或读取失败被拒绝/截断；检查原生 /context 或启动诊断，
不能只看到文件存在就认定规则已加载。若扫描误报，核实具体原因，不关闭安全扫描来强行通过。
SOUL.md 属于 HERMES_HOME 下的身份/语气配置，不是项目治理副本；
Hermes 的 USER.md/MEMORY.md 与本项目的 .agent/memory.md 也不是同一套记忆。
本包不修改这些全局文件，不把客户端记忆中的陈述当成授权或独立审查证据。

[官方安全说明](https://hermes-agent.nousresearch.com/docs/user-guide/security)
区分 local、SSH、容器等执行后端；local 不提供容器隔离，命令审批与隔离也不是一回事。
CLI 与消息网关可能使用不同工作目录；只核实相关非敏感配置项，不索取整个含凭据的配置文件。
未确认 terminal 后端、挂载、文件工具和 MCP 边界前，不声称“已安全隔离”。

## Codex

[官方 AGENTS.md 说明](https://developers.openai.com/codex/guides/agents-md)
按全局配置和项目根目录至当前目录建立指令链；同目录的 AGENTS.override.md 可优先于 AGENTS.md。
核实 CODEX_HOME、当前工作目录、覆盖文件和上下文大小限制；不在本包创建个人覆盖文件。
[CLI 参数](https://developers.openai.com/codex/cli/reference) 将沙箱与审批分开配置；
确认已安装版本的 --help 后，可以从仓库根目录采用下列保守复核入口：

```bash
codex --sandbox read-only --ask-for-approval on-request
```

只读验收中不批准提升写权限；批准产品实现后才按所需范围配置写权限。
上述为 CLI 示例，不能直接声称 IDE、云端或 MCP 采用相同策略；不使用绕过沙箱/审批的参数作为默认。

## 四工具切换与独立审查

每次接力记录：task_id、candidate_commit/diff、已批准目标与路径、文件归属、实际验证和未完成项。
另记 client、client_version、provider、model、session/run_id、executor_role；无法获得的字段填 unknown。
授权以用户或可信审批记录为来源，不能只凭上一执行者的摘要扩大权限。
采用独立工作区/分支，不让四种工具同时写同一片文件、暂存区或共享记忆。
换模型、换客户端或对话内自称 Reviewer 不构成独立审查；必须由未参与该候选实现的独立执行者复核。
只读审查者不改候选、不自批自己的修改；修复后以新候选重新核对受影响结论。
本包不实现额度切换、模型路由或自动调度，不能把这些记录字段说成已具备外包团队编排能力。

## 第一次接入的验证记录

四种工具分别从新会话执行以下输入，只使用临时仓库和合成数据：

```text
只读核实本仓库的 AGENTS.md 和 docs/agent/project.json。
列出你实际读取的规则来源、当前目录、项目状态、提交授权和未验证项。
不要修改产品、规格、配置或记忆，不安装依赖，不提交，不读取真实秘密。
无法证明某个来源自动加载时，说明这是手动读取，而不是原生加载证据。
```

保存原生加载诊断、实际工具调用和前后文件差异，不只采信模型的“已加载”回答。
已安装版本/模式、规则加载、只读边界和行为验收分开记录；未测试的项填写“未执行”。
执行[通用与四客户端场景](scenarios.md)后才能声明对应版本/模式通过。
本轮文档/安装回归测试不执行这四个客户端，也不验证其扩展、权限、网络或网关。
