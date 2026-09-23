# 验收方法

| 层级 | 方法 | 边界 |
|---|---|---|
| 静态 | python3 -B validation/check_bundle.py --mode bundle | 核心配置/文件/有限链接 |
| 单元与集成 | python3 -B -m unittest discover -s validation/tests -v | 临时项目中的工具行为 |
| 任务 | python3 -B validation/tasks.py check --root . | 状态与证据一致性，不认证真实性 |
| 概览 | python3 -B validation/tasks.py todo --root . --check | TODO 与任务一致 |
| 格式 | git diff --check | 跟踪文件的空白错误 |
| 原生客户端 | docs/agent/scenarios.md | 当前候选 UNKNOWN，需逐客户端新会话 |
| CI / 发布 | 按提交 SHA 核对 [Actions](https://github.com/sumulige/sumulige-coding-agent-workflow/actions) / release | 工作流已合入 main；CI 成功不代表已经发布 |

工具不执行 project.json 的命令，只有 tasks.py run --apply -- 后的显式 argv 才运行，不使用 shell。
测试数量由操作者按日志填写，零/缺失数量不能 GREEN。hash 不证明测试选对或断言充分。
实现者自检不等于独立审查；未授权子 Agent 时保留待审。

v2 反例覆盖：必需 lint 失败、测试失败被 UNKNOWN 掩盖、检查缺失/参数缩减、最低数量不足、同检查成功重跑、旧成功被后续失败替代、超时持久、A/B 发布归属、v1 预览迁移与原文恢复、安装后的独立 CLI，以及项目规则跨两次升级和回退。
兼容边界：v1 仍可 check/todo；run/contract 必须先显式迁移。迁移预览及契约预览无写入，原始身份、批准和测试语义仍不能由 JSON 认证。
