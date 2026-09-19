# tooling.md — 工具使用约束

## 允许
- 读取仓库内任意文件
- 运行 `test_command`、`lint_command`
- 运行只读 git 命令：`status`、`diff`、`log`、`show`

## 需确认
- 安装新依赖
- 运行修改数据库的脚本
- 网络请求（除包管理器）

## 禁止
- `git push --force`、`git reset --hard` 到已推送提交
- 删除 `.git/`
- 修改 CI 配置（除人工确认）
- 执行 `rm -rf` 于仓库根目录之外

## 命令超时
统一使用 `project.md` 的 `timeout_seconds`。
