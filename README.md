# agent-workflow-bundle v2.2

面向 AI 编码代理的轻量仓库规则包：任务分级、授权边界、可核实交付，以及零第三方依赖的配置检查。
**不是 Agent 调度平台，也不是沙箱。静态检查通过不代表项目就绪、模型行为可靠或权限隔离生效。**

## 先看变化

[v2.2 变更说明](CHANGELOG.md) · [核心规则](AGENTS.md) · [项目配置](docs/agent/project.md)

## 安全安装到已有项目

在本规则包目录运行，Python 3.10+；目标目录须已存在。默认只预览：

```bash
python3 -B validation/check_bundle.py --mode bundle
python3 -B validation/install_bundle.py /path/to/target-repository
# 审查 CREATE / SAME / CONFLICT 后再显式写入
python3 -B validation/install_bundle.py /path/to/target-repository --apply
```

安装器只复制声明的核心规则、配置模板、规格模板和检查器，不复制本 README、CI、测试结果或 .gitignore。
任何内容冲突都会在写入前停止；相同文件跳过；已有文件绝不覆盖，没有 --force 选项。
拒绝路径中的符号链接，写入使用排他创建。请在可信且没有并发修改的目录执行；这不是防竞态沙箱。
I/O 故障中途失败会列出本次已创建文件，不删除其他成果；检查这些文件后再重试。
新版配置始终以 unconfigured、空命令和保守提交/记忆策略安装，不继承来源项目的授权。

已有 v2.1 或个性化规则时，先预览冲突，再在独立分支手动合并；不要把整个包覆盖到项目根目录。
升级前记录 Git 差异并备份；仅回滚本次变更，不使用 reset --hard 清理已有成果。
项目配置不会被安装器自动迁移或重置，发生冲突时原样保留。详细步骤见 [迁移说明](docs/agent/project.md)。

## 初始化目标项目

在 docs/agent/project.json 中填写实际命令、工作目录和保护路径，保留 schema_version 与字段类型。
由人授权试运行实际 lint/test 并记录结果，确认适用验证后再批准 configured：

```bash
python3 -B validation/check_bundle.py --mode ready
```

ready 只做静态就绪检查，不执行命令、不证明测试通过。缺少运行证据不得声称项目可用。
普通产品写入受状态门约束；只读任务与用户明确授权的规则/配置维护有独立路径。

## 日常使用

“只读点评”不生成规格或记忆；“修复这个 Bug”先确认复现和验收；明确批准的范围内继续工作。
[工作流程](docs/agent/workflow.md) 说明任务分级，[验证规则](docs/agent/testing.md) 区分任务完成与测试五态。
默认不自动提交；明确要求提交 GitHub 时使用任务分支与 PR，不自动合并、部署或修改仓库保护。
Claude Code 已通过 CLAUDE.md 导入 AGENTS.md；其他工具和执行隔离见 [工具接入](docs/agent/tooling.md)。

## 维护本规则包

```bash
python3 -B validation/check_bundle.py --mode bundle
python3 -B -m unittest discover -s validation/tests -v
python3 -B validation/check_bundle.py --json
```

默认只向标准输出报告，不写 validation/results.json。JSON 附已检查输入文件的 SHA-256；保留证据需显式重定向。
配置严格拒绝非法状态、重复键、错误类型、空的 configured 命令、非法超时和不安全路径。
结构检查可发现空文件、缺失规则正文和部分断链，但不证明自然语言语义完整，不检查外链和 Markdown 锚点。

CI 对 Python 3.10/3.13 运行结构与回归测试，使用只读权限和固定 SHA，不注入秘密、不设置仓库保护。
管理员应在看到真实检查运行后配置必需检查和独立评审；不能把“已添加工作流”说成“保护已开启”。
[20 条真实 Agent 场景](docs/agent/scenarios.md) 是待执行清单，不是已经通过的行为测试。

## 目录

| 路径 | 职责 |
|---|---|
| AGENTS.md / CLAUDE.md | 共享核心规则 / Claude 导入 |
| docs/agent/ | 唯一 JSON 配置、流程、验证、工具来源与行为场景 |
| docs/specs/_TEMPLATE/ / docs/adr/ | 需求、设计、任务与 ADR 模板 |
| .agent/memory.example.md | 经验证经验与交接格式，不自动写共享记忆 |
| validation/check_bundle.py | 只读静态检查器，不执行项目命令 |
| validation/install_bundle.py | 默认预览、冲突拒绝、仅创建的安装器 |
| validation/tests/ | 使用临时仓库的反例与回归测试 |
| .github/workflows/bundle-check.yml | 本规则包 CI，不自动部署到目标项目 |
