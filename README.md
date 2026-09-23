# sumulige-coding-agent-workflow

统一 AI 编码项目的文档、任务、交接与验收证据。Python 3.10+ 标准库；没有模型调用或第三方运行依赖。

当前为 **2.3.0-dev 候选**，已合入 main，尚未发布 release。源码：[sumulige-coding-agent-workflow](https://github.com/sumulige/sumulige-coding-agent-workflow)。[交付记录](docs/changes/2026-09-coding-workflow/plan.md) 分别记录本地、原生客户端、独立审查与发布状态；[合并与更名记录](docs/changes/2026-09-coding-workflow/publication.md) 保留远端操作依据。

## 1. 项目安装

在分发仓库运行，目标目录须已存在：

```bash
python3 -B validation/manage.py /path/to/project --profile core
# 审查 CREATE / LOCAL / SAME / UPDATE / CONFLICT 后才写入
python3 -B validation/manage.py /path/to/project --profile core --apply
python3 -B validation/manage.py /path/to/project --check
python3 -B validation/adapters.py check /path/to/project
```

1. core：AGENTS、README、CHANGELOG、TODO、产品范围、架构、开发、验收。
2. web：core 加 DESIGN、PAGE-STRUCTURE、DEPLOYMENT。
3. registry：web 加 COMPONENT-GUIDELINES、REGISTRY。

项目文档与配置保留原样，共享规则冲突会阻止整个更新；先审阅合并，无强制覆盖。新文档以 DRAFT 初始化，不编造产品事实。初始化后补充真实命令与范围，由人确认 [项目状态](docs/agent/project.md)。

## 2. 日常使用

AI 按 [维护映射](docs/agent/maintenance.md) 随代码更新受影响文档。只读不写文件，小改动可继续用现有 Issue，复杂任务用 docs/changes/。

```bash
python3 -B validation/tasks.py create cart-fix --root /path/to/project \
  --title "修复购物车校验" --objective "空购物车不能结算" \
  --scope src/cart --authorization "用户明确要求修复" \
  --acceptance "空购物车被拒绝且有效购物车不受影响"
# 上述只预览；审查后追加 --apply
python3 -B validation/tasks.py check --root /path/to/project
python3 -B validation/tasks.py todo --root /path/to/project
# 审查后追加 --apply；CI 使用 --check
```

任务工具随新版安装到目标项目，也可从分发仓库调用。命令留档与 JSON 契约见维护说明。任务、测试、独立审查和发布分别记录。

## 3. 升级与回退

用经核实的来源版本升级，锁记录版本与文件指纹，不自动追随 main。

```bash
python3 -B validation/manage.py /path/to/project
python3 -B validation/manage.py /path/to/project --apply
# 用上次输出的事务 ID；先预览再追加 --apply
python3 -B validation/manage.py /path/to/project --rollback TRANSACTION_ID
```

备份保存旧字节，回退拒绝覆盖后续编辑。I/O 中断按事务记录恢复。备份可能含原有项目内容，应仅本地保存。工具适用于可信且无并发修改的目录，不提供操作系统隔离。
旧 install_bundle.py 保持 v2.2 仅创建行为；无锁旧项目不自动接管不同的规则。

## 4. 七客户端与全局入口

Codex、Claude Code、Cursor、Hermes、Pi、Gemini CLI、OpenCode 共用项目 AGENTS.md；Claude/Gemini 使用薄导入入口。[客户端差异](docs/agent/clients.md)。

```bash
# 显式目标 home；默认仅预览
python3 -B validation/adapters.py global --home /path/to/home
python3 -B validation/adapters.py global --home /path/to/home --clients codex claude-code
```

全局工具支持标准目录布局，已有规则不同则拒绝。Codex、Claude、Pi、Gemini、OpenCode 有文件入口；Cursor/Hermes 输出 MANUAL 片段，保留原设置与 SOUL。自定义客户端目录需单独核实。项目初始化不会隐式安装全局入口或启动模型。

## 5. 维护与验收

```bash
python3 -B validation/check_bundle.py --mode bundle
python3 -B -m unittest discover -s validation/tests -v
python3 -B validation/tasks.py check --root .
python3 -B validation/tasks.py todo --root . --check
git diff --check
```

测试使用临时项目，不操作真实 home。软件测试不能证明七客户端原生加载、权限隔离或模型遵守规则，真实验收按 [场景](docs/agent/scenarios.md) 分别留档。

1. [产品范围](docs/PROJECT-SPEC.md)
2. [架构](docs/ARCHITECTURE.md)
3. [开发](docs/DEVELOPMENT.md)
4. [验收](docs/TESTING.md)
5. [任务](TODO.md)
