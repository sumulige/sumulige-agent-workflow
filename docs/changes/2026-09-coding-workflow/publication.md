# 合并与仓库更名记录

1. 授权：用户明确要求“合并这个分支 项目更名为 sumulige-coding-agent-workflow”。范围为本仓库分支合并、更名及必要的文档/远端地址同步；不包含发布 release、全局安装或改动 sumulige-claude。
2. 合并：[PR #2](https://github.com/sumulige/sumulige-coding-agent-workflow/pull/2)，head 为 21d019da90fc6e9eaf3563fea6c1e4bdbf8f69e8，base 为 main，合并提交为 867d85ff57d16d02e54a5ee1caf8d94f09fcedd5。采用普通 merge，保留四个候选提交及 v2.2 基础历史。
3. 合并前验证：[候选 CI](https://github.com/sumulige/sumulige-coding-agent-workflow/actions/runs/35828419276) 与 [PR CI](https://github.com/sumulige/sumulige-coding-agent-workflow/actions/runs/35828694520) 的 Python 3.10 / 3.13 检查均通过。未使用 admin 绕过或修改分支保护。
4. 更名：sumulige/sumulige-agent-workflow → sumulige/sumulige-coding-agent-workflow。API 回读新名称、默认分支 main，稳定仓库 ID 仍为 1376744339。原有提交、PR 与仓库身份保留。
5. 本地：此项目 origin 同步为 https://github.com/sumulige/sumulige-coding-agent-workflow.git；本地目录已经使用新名称。sumulige-claude 的文件和远端未修改。
6. 认证复核：允许联网后 gh auth status 成功，使用 keyring 中的现有认证。前次沙箱内“令牌失效”输出不足以判断真实令牌状态，不需要重新登录。
7. 验收边界：用户批准合并不等于独立审查或原生客户端验收已经执行。原任务的 PARTIAL 和未验证项保留；没有发布 tag/release，没有全局安装。
8. 日期：2026-09-23。这份记录补充先前候选快照，不改写其日志或源码指纹；后续文档提交以 Git 历史和对应 CI 为准。
