# 项目配置与迁移

## 唯一配置来源

[project.json](project.json) 是机器配置；本说明不再维护另一份 YAML 状态。
使用 Python 3.10+ 标准库检查，不增加 YAML 或其他运行依赖。
本仓库发布的是可移植模板，默认 `unconfigured`；模板检查通过不表示目标项目就绪。
用户明确委托维护本规则包时，适用根规则的治理维护例外，不必伪装已配置产品。

## 字段约定

| 字段 | 约定 |
|---|---|
| schema_version | 整数 1；未知字段、缺失字段、重复 JSON 键均拒绝 |
| status | 精确值 unconfigured 或 configured，不接受前缀或拼写变体 |
| test_command / lint_command | 单行字符串；configured 时必须非空；不能用空操作冒充验证 |
| working_directory | 仓库相对目录；`.` 表示根目录；ready 模式要求实际存在 |
| protected_paths | 非空、无重复的字面路径列表；尾斜杠表示整个子树，不支持 glob |
| timeout_seconds | 1–3600 的整数秒；这是本工具的边界，不是通用性能指标 |
| commit_policy | explicit-request 或 after-validation；不授权合并、部署 |
| memory_policy | suggest-only 或 append-authorized；不授权只读任务写入 |

保护列表必须保留 AGENTS.md、CLAUDE.md、docs/agent/、validation/ 和 .github/。
路径禁止绝对路径、`..`、反斜杠和通配符；检查器拒绝沿符号链接读取声明文件。
路径保护的执行由 Agent 权限、沙箱与仓库审查实现，本 JSON 不是强制隔离配置。

## 两层检查

```bash
python3 validation/check_bundle.py --mode bundle
python3 validation/check_bundle.py --mode ready
python3 validation/check_bundle.py --mode bundle --json
```

bundle 检查核心文件、规则正文存在性、受支持的本地行内链接和 JSON 结构。
ready 额外要求 configured、完整命令声明与实际工作目录；它只是静态配置就绪检查。
两种模式均不执行配置命令、不请求网络、不写结果文件，不证明命令存在、测试发现数量或行为正确。
保留报告时由操作者显式重定向到已授权路径，不覆盖旧证据；报告带输入 SHA-256。

## 初始化与 v2.1 迁移

先记录现有 Git 差异，在独立分支处理冲突，不覆盖已有 README、AGENTS 或项目配置。
把旧 project.md YAML 的实际命令、超时、保护路径逐项迁入 JSON；保留或补充必要保护路径。
确认工作目录和项目运行时；由人授权命令试运行，记录 lint/test 的真实结果后再批准 configured。
缺少可用验证工具时保持 unconfigured，仍能进行只读和明确授权的治理维护。
不要为了通过检查填 `true`、`echo OK` 或本规则包的结构检查来冒充目标产品测试。

## 当前规则包维护命令

从本规则包根目录执行：

```bash
python3 validation/check_bundle.py --mode bundle
python3 -B -m unittest discover -s validation/tests -v
```

这些是规则包自身的检查，不自动成为目标项目的 test/lint。
目标项目的类型检查、构建、集成测试、界面与手动验收，按 [验证规则](testing.md) 写入任务计划。
不根据文件数量假定技术栈，不擅自升级运行时或依赖；用 lockfile 与现有项目配置核实。
