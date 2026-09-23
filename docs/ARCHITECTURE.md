# 架构与数据组织

Python 3.10+ 标准库。分发仓库拥有版本，目标项目拥有本地事实。

| 模块 | 职责 |
|---|---|
| check_bundle.py / install_bundle.py | v2.2 配置校验与兼容的仅创建安装 |
| profiles.py | 文档组合与 local / managed 归属 |
| manage.py | 安装、升级、漂移检查、回退 |
| storage.py | 路径、指纹、文件替换、备份与恢复 |
| tasks.py | task v1/v2、命令留档、显式迁移、证据检查、TODO |
| task_contract.py | v2 检查声明、契约指纹、原始执行结果与完成校验 |
| adapters.py | 七客户端诊断、全局薄入口 |

依赖单向：命令模块 → profiles/task_contract/storage → check_bundle；task_contract 也复用 storage。无第三方依赖、模型调用或网络调用。

项目锁 .agent/workflow-lock.json 与全局锁 .agent/workflow-global-lock.json 分开。配置/产品文档 local，共享规则 managed；有本地编辑的规则不能自动覆盖。
任务源在 docs/changes/<id>/task.json；外部任务保留并通过 source 引用。TODO 只生成概览。
任务 v2 将候选、检查契约、执行事实、验收/审查和发布历史分开。检查集合与完整 argv/cwd 参与契约指纹，变更后必须重新验收。
项目配置、事实文档与 .agent/project-rules.md 为 local；共享入口和工具为 managed。扩展文件不改变平台指令优先级。
v1 不自动迁移；显式 migrate 用已有事务机制备份原文，将无法证明的执行/发布归属保留为未知。project.json 与安装锁仍为 v1。
日志 hash 证明字节一致；候选、批准、独立审查身份需要真实证据，JSON 不认证身份。

事务先保存旧字节与前后 hash；失败按事务 ID 恢复，回退拒绝后续编辑。批次不保证整体原子性，要求可信且无并发修改的目录。
