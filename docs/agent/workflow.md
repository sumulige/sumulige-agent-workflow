# workflow.md — 任务流程

## 步骤
1. **读取**：AGENTS.md → project.md → memory.md → 任务 spec
2. **确认范围**：列出将改动的文件；涉及 protected_paths 则停止等待确认
3. **规格**：无 spec 时，先生成 `docs/specs/<name>/requirements.md`，等待确认
4. **设计**：跨模块改动写 `design.md`；架构级改动写 ADR
5. **任务分解**：写 `tasks.md`，每项 ≤ 300 行改动
6. **实现**：逐项完成，每项后运行 lint + test
7. **报告**：按 AGENTS.md §8 格式输出
8. **记忆**：写入 `.agent/memory.md`

## 状态转移
```
读取 → 确认范围 → [需 spec?] → 规格 → 设计 → 任务分解 → 实现 → 报告 → 记忆
                       ↓ 否
                     实现
```

## 中止条件
- 状态门未通过
- 测试进入 RED 且连续 3 次修复失败 → 报告并停止
- 用户指令与硬规则冲突
