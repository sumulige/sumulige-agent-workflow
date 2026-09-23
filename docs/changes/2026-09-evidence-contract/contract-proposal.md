# 已批准：任务契约 v2 与本地规则扩展

状态：APPROVED。用户在阅读本具体方案及自动审批拒绝说明后，明确回复“批准”。批准覆盖下列数据模型、CLI、迁移和扩展层；独立审查、原生试点与合并发布仍分别记录。

## 1. 批准对象

在 sumulige-coding-agent-workflow 的 codex/task-evidence-contract 分支实施下列数据模型、CLI 及扩展文件变化。保持 Python 标准库、project.json v1、安装锁 v1 和现有事务回退。不会改全局配置、sumulige-claude、依赖、仓库权限或发布状态。

## 2. 数据模型

新建任务使用 schema_version=2。保留目标、范围、授权、候选、验收等原有字段，改变如下：

| 对象 | 新约定 |
|---|---|
| contract | kind=code/maintenance、basis（建立/修改依据）、project_sha256、checks 数组 |
| 单个 check | id、description（检查范围）、required、layer、完整 command argv、cwd、min_count（测试为正整数，其余 null） |
| evidence | 增加 contract 指纹、check_id（未声明的探索执行为空）、outcome |
| outcome | exited、timeout、unavailable、observed、legacy；无法启动/观察不伪造子进程退出码 |
| review | 增加 contract 指纹；审查须同时对应候选与当前检查约定 |
| releases | 替代旧单个 release 汇总；数组记录 candidate 与 reference，当前发布状态按候选匹配推导，历史不删除 |

code 默认带项目配置中的 lint/test，完成时两者必须为必需项、匹配当前配置且有成功执行。维护/观察任务可用适用的结构检查或人工证据，必须填写依据，不强制伪造测试 GREEN。

契约变更后清空旧验收、审查并保留历史证据。相同 check_id 只有在候选、契约、完整 argv/cwd 都匹配时才能产生替代结果。缩小命令范围、降低数量要求或删除检查不能沿用旧契约的验收。

测试概览从原始执行事实生成并交叉校验；TIMEOUT 不受后续无关 static 运行影响，手填 UNKNOWN 不能掩盖确定的失败。测试数量仍由操作者按日志确认，工具不证明测试语义、需求完整性或授权真实性。

## 3. CLI 与兼容

1. create 增加 --kind、--basis、--checks；--checks 指向项目内 JSON 检查数组。配置命令按 argv 明确解析，不隐式调用 shell；需要 shell 的项目应显式声明 shell 命令。
2. 新增 contract ID：先输出预览；--apply 更新契约并使旧验收失效。basis 必填。无隐式执行。
3. run 增加 --check-id；声明检查必须与固定命令、目录、层级匹配。未绑定执行可留档，但不能满足必需检查。
4. 新增 migrate ID：v1 → v2 默认预览，--apply 保存原文备份再更新。旧 evidence 标 legacy，不猜测旧超时或发布属于哪个候选；未能证明的验收清空。回退可恢复备份字节。
5. check / todo 继续读取 v1，并明确其为旧结构校验。v1 新命令执行需先显式迁移。这是行为兼容变化，需要本方案的明确批准；不自动迁移已有项目。
6. 退出码仍为 0 成功/预览、1 校验或执行失败、2 参数错误。仅 --apply 写入，运行不自动重试，文件写入保留比较并替换保护。

## 4. 本地规则与升级

新增项目自有的 .agent/project-rules.md；共享入口说明读取该文件。首次安装只创建缺失文件，后续升级和回退保留用户编辑。它是项目规则扩展，不更改平台指令优先级。

已有 managed 文件中的定制需人工审阅并搬到此扩展，随后恢复核实过的共享版本，再升级。工具继续报告冲突，不提供强制覆盖或任意认领。需验证迁移操作后后续第二次升级与回退仍保留扩展内容。

## 5. 必需验证与边界

CLI 临时项目反例覆盖 lint 失败、UNKNOWN 掩盖失败、缺少必需检查、缩小测试范围、同契约成功重跑、超时保留、发布 A/B 区分、维护任务观察验收、迁移预览/备份、扩展规则跨升级/回退、安装后的 CLI 可运行。

完整回归与 CI 对应确切候选。独立审查、真实客户端接力、全局安装、合并及正式发布分别记录；本方案不将这些视为自动完成或自动授权。
