# 七客户端接入

共用项目 AGENTS.md 与 docs/agent/，只适配加载入口。官方资料核对：2026-09-23；资料支持不等于本机原生验收通过。

| 客户端 | 项目入口 | 标准全局入口 | 本包适配 |
|---|---|---|---|
| Codex | AGENTS.md | ~/.codex/AGENTS.md | 指示读取共享入口 |
| Claude Code | CLAUDE.md 导入 AGENTS.md | ~/.claude/CLAUDE.md | @ 相对导入 |
| Cursor | AGENTS.md | User Rules | 手动审阅片段 |
| Hermes | AGENTS.md，注意专用上下文 | 无统一全局 AGENTS 保证 | 项目入口与手动片段 |
| Pi | AGENTS.md | ~/.pi/agent/AGENTS.md | 指示读取共享入口 |
| Gemini CLI | GEMINI.md 导入 AGENTS.md | ~/.gemini/GEMINI.md | @ 相对导入 |
| OpenCode | AGENTS.md | ~/.config/opencode/AGENTS.md | 指示读取，不假定 @ 自动展开 |

## Codex

[官方说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 描述全局与项目目录链、AGENTS.override.md 优先级。
核实 CODEX_HOME、启动目录和长度限制。本包不改 config.toml、模型或权限；全局指针依赖 Agent 实际读取，不是原生 import。

## Claude Code

[官方说明](https://code.claude.com/docs/en/memory) 支持 AGENTS.md（v2.1.277+），但 CLAUDE.md/CLAUDE.local.md、会话能力和配置会影响选择。
保留 CLAUDE.md 的 @AGENTS.md 作为兼容入口，不复制正文。核实 /memory 与实际读取；外部导入需要的原生批准不得绕过。

## Cursor

[官方规则](https://cursor.com/docs/rules) 支持 AGENTS.md 与 User Rules。
不写内部设置存储、不生成重复 .cursor/rules。全局命令生成 manual/cursor.md，人工审阅后加入 User Rules。IDE、CLI、云端分别验收。

## Hermes Agent

[官方上下文](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files) 列出 .hermes.md / HERMES.md、AGENTS.override.md、AGENTS.md 等入口及优先级。
专用文件可能遮蔽 AGENTS，安全扫描和截断可能阻止加载。观察 /context 和实际调用，不关闭扫描。
Git 仓库内有目录链；仓库外不读取任意父目录。SOUL 在 HERMES_HOME 处理身份语气。
全局命令仅生成 manual/hermes.md，默认以项目 AGENTS 接入；不改 SOUL、USER、MEMORY 或网关后端。

## Pi Coding Agent

[官方配置](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/configuration.md) 说明全局/父目录上下文和 AGENTS.override.md 等优先级。
不替换 SYSTEM.md、不安装扩展、不改工具列表。上下文读取与命令隔离分别验证，不把项目信任视为逐命令审批。

## Gemini CLI

[官方说明](https://geminicli.com/docs/cli/gemini-md/) 支持全局、工作区、按需上下文及 @ 相对导入。
项目 GEMINI.md 只导入 AGENTS.md，不改 settings.json。用 /memory show、/memory reload 核实；信任目录和自定义文件名需原生验证。

## OpenCode

[官方规则](https://opencode.ai/docs/rules/) 支持项目/全局 AGENTS.md，复用文档也可配置 instructions。
本包不覆盖 opencode.json；Markdown 文件指针不会自动展开，所以明确指示按需读取并核实实际工具调用。

## 接入与接力

1. adapters.py check PROJECT 只检查根目录入口与部分遮蔽文件，不检查全部祖先、全局设置或原生会话。
2. 全局安装显式 --home 预览；标准目录以外需单独整合；已有不同规则冲突停止，不强制覆盖。共享入口按版本保存。
3. 新会话用合成项目只读验证，保存版本、模式、目录、原生诊断和前后差异。模型自称“已加载”不充分。
4. 接力保留 task_id、候选、批准来源、范围、证据、归属和 next；未知 model/provider/session 写 unknown。
5. 按 scenarios.md 分客户端验收，未执行记 UNKNOWN。合成文件测试不能冒充原生通过。
6. 独立审查由未参与实现的执行者进行；切换角色或模型名不能自动产生独立性。

本包不启动客户端、不调度 Agent、不进行付费模型调用；不宣称成本收益已测量。
