# 文档维护与版本管理

## 文档职责

| 变更触发 | AI 更新的事实来源 |
|---|---|
| 已批准目标与范围变化 | docs/PROJECT-SPEC.md；保留批准依据 |
| 模块、数据或重要设计变化 | docs/ARCHITECTURE.md；重大取舍链接 docs/adr/ |
| 视觉、页面、组件变化 | DESIGN.md、PAGE-STRUCTURE.md、COMPONENT-GUIDELINES.md（适用时） |
| 开发与验收命令变化 | README.md、DEVELOPMENT.md、TESTING.md；机器配置在 project.json |
| 构建、分发、部署变化 | REGISTRY.md、DEPLOYMENT.md（适用时） |
| 任务状态与证据变化 | docs/changes/；TODO.md 仅生成概览 |
| 用户可见变化 | CHANGELOG.md 的 Unreleased；不虚构发布 |

只加载和维护任务相关文件。只读请求不创建任务、规格或记忆。
小改动可引用已有 Issue；复杂任务保留范围、验收、批准、证据和下一步。
项目拥有事实文档；模板只初始化缺失文件。AI 不为通过检查自批需求。

## 三种组合

1. core：规则、README、CHANGELOG、TODO、产品范围、架构、开发与验收。
2. web：core 加 DESIGN、PAGE-STRUCTURE、DEPLOYMENT。
3. registry：web 加 COMPONENT-GUIDELINES、REGISTRY。

## 安装升级

在分发仓库运行 validation/manage.py，默认预览，--apply 才写入。
`.agent/workflow-lock.json` 记录版本、文件 SHA-256 与归属；规则 managed，项目事实 local。
更新仅覆盖与上次安装 hash 一致的规则；自定义规则冲突阻止整个更新。local 文件保留。
v2.2 安装器保持仅创建语义；无锁旧项目先审阅冲突，不自动认领不同内容。
不随 main 自动升级；管理员选择已核实来源。hash 是内容指纹，不是作者签名。

写入前在 `.agent/workflow-backups/<id>/` 保存旧文件与 receipt。
I/O 中断报告事务 ID；检查后用 `--rollback <id>` 预览，再 --apply 恢复。
回退拒绝安装后的编辑；只删除本事务创建且未变化的文件，保留空目录与备份。
在可信且无并发修改的目录运行；逐文件原子替换不是跨文件事务或竞态攻击防护。

## 任务与命令留档

1. `tasks.py create ID` 接收 title、objective、scope（可重复）、authorization、acceptance（可重复），可加 source 与 implementer。默认输出 JSON；--apply 排他创建，已有任务不覆盖。
2. AI 在批准范围内编辑 docs/changes/ID/task.json，把当前事实、验收证据和 next 交给下一客户端。普通小任务可保留现有 Issue，无需复制一个 JSON。
3. `tasks.py check --root PROJECT` 只读检查所有任务；`todo` 预览概览，--apply 更新 TODO 的两个 workflow:tasks 标记之间，标记外原样保留。无标记的旧 TODO 拒绝覆盖。
4. `todo --check` 用于 CI 检查漂移；只读任务不得调用 --apply 或 run --apply。

实际命令必须显式放在双横线后，默认仍只预览：

```bash
python3 -B validation/tasks.py run cart-fix --root /path/to/project \
  --candidate COMMIT_OR_DIFF_FINGERPRINT --layer unit --count 12 \
  --timeout 600 --apply -- python3 -B -m unittest discover -s tests -v
```

使用真实候选提交，或 base commit 加工作区指纹；新候选会清空旧验收引用与审查状态。
--count 由操作者按实际日志核对后填写，工具不会从退出码猜测测试数量。未知数量记 UNKNOWN，零测试记 UNTESTED。
每次执行产生新的日志，不自动重试、不自动标记验收或任务完成。命令重跑可能有副作用，应先核实范围；日志不得包含秘密。
同一候选、层级、argv 和 cwd 的最近一次结果用于测试概览，旧日志仍保留。
超时为 1–3600 秒；POSIX 超时终止该命令进程组，其他系统只保证直接子进程结束。工具不能清理由命令自行脱离进程组的服务，操作者仍须确认归属并清理。
命令失败/不可用/超时返回 1；日志已经保存但 task 更新失败时，保留日志供人工接回记录，不自动重复执行。

## JSON 与 CLI 契约 v1

新增工具面向公开维护者和 AI 消费者；旧 check_bundle.py JSON、project.json schema 和 install_bundle.py 参数保持兼容。
所有 JSON 拒绝重复键及 NaN/Infinity。工具输出为人类可读 stdout/stderr，不承诺逐行格式是稳定 API；机器以 JSON 文件为准。
退出码：0 为操作成功或预览通过，1 为校验/冲突/I/O/命令失败，2 为参数错误。--apply 以外的检查和预览不写文件。

| task.json 字段 | 类型与语义 |
|---|---|
| schema_version / id | 整数 1；1–64 位小写字母、数字、连字符，与目录名一致 |
| title / objective / authorization / implementer | 必填非空文本；授权陈述须能回溯真实来源，不是自动授权 |
| source / candidate / next | 文本；source 可链接既有任务，未完成需 next；有证据和完成时需候选标识 |
| scope | 非空仓库相对字面路径数组，无 glob、绝对路径或越界 |
| status / test_status | COMPLETE/PARTIAL/BLOCKED；GREEN/RED/UNTESTED/TIMEOUT/UNKNOWN |
| release | status=UNRELEASED/RELEASED 与 reference 文本；RELEASED 必须有独立发布引用 |
| review | required 布尔、status、reviewer、reference、candidate；VERIFIED 要求不同实现者、引用及相同候选 |
| acceptance | id、description、required 布尔、status、evidence ID 数组；完成前所有必需项 VERIFIED |
| evidence | id、layer、status、candidate、command argv 数组、cwd、exit_code、count、artifact、sha256 |

验收、审查与证据 status 为 VERIFIED/PARTIAL/FAILED/UNKNOWN。
layer 为 static/unit/integration/runtime/visual/native/external/ci/release。
exit_code 为整数或 null（人工观察）；count 为非负整数或 null。VERIFIED 的测试须 exit 0 且 count > 0。
artifact 为仓库内实际文件路径，sha256 必须匹配；人工观察的 command 写明观察方法，不伪造程序执行。
上述对象字段严格匹配，无隐式默认字段。示例可由 create 命令生成；普通文本不得冒充机器状态。
校验器只验证记录的一致性和文件字节，不验证身份、批准真实性、候选归属或测试语义，不能防止恶意伪造最初记录。

项目 lock：schema_version=1、version 文本、profile=core/web/registry、files（路径映射到 sha256/ownership）。
ownership=local 的项目事实保留；managed 必须与上次 hash 一致才可更新。只允许 profile 增加，删除需人工迁移。
全局 lock：schema_version=1、files（路径到 SHA-256），与项目 lock 独立。升级不删除旧版本或未选择客户端。
事务 receipt：schema_version=1、state=prepared/applied、files（路径映射到 before/after hash 或 null、数字 backup 文件名）。
锁和 receipt 是本地审计记录，不是签名或权限系统；备份不得上传到公共仓库。
