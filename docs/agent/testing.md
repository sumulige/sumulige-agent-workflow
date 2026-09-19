# testing.md — 测试五态与红绿规则

## 五态定义
| 状态 | 条件 |
|---|---|
| `GREEN` | test_command 退出码 0，且改动文件有对应测试 |
| `RED` | test_command 退出码非 0 |
| `UNTESTED` | test_command 通过，但改动文件无对应测试 |
| `TIMEOUT` | test_command 超过 `timeout_seconds` 未结束 |
| `UNKNOWN` | test_command 为空、不存在或无法执行 |

## 红绿规则
1. 修 bug：先写复现测试（RED），再修复（GREEN）。
2. 新功能：先写测试（RED），再实现（GREEN）。
3. 只有 `GREEN` 可声称"完成"。
4. `RED` 连续 3 次修复失败 → 停止并报告。
5. 不得通过删除、跳过、修改断言使 RED 变 GREEN（见 HR-3）。

## 对应测试判定
改动文件 `src/x/y.py` 对应测试为 `tests/**/test_y*.py` 或 `tests/**/y_test*.py`；项目可在 project.md 覆盖此规则。
