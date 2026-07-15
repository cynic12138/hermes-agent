---
name: scope-gate
description: 在实现新需求、扩大功能、改变架构或处理可能超出当前阶段的工作前使用；依据项目目标、MVP 范围和项目状态，将请求分类为 IN_SCOPE、NEEDS_APPROVAL 或 OUT_OF_SCOPE，防止范围持续发散。
---

# Scope Gate

## 工作流

1. 读取项目根目录 `AGENTS.md`。
2. 读取 `docs/MVP_SCOPE.md`。
3. 读取 `docs/PROJECT_STATE.md`。
4. 读取 `docs/ROADMAP.md`；若不存在，读取最接近的路线图文件。
5. 提取本次用户明确要求，不把暗示、顺便优化或未来可能需求算入范围。
6. 输出分类理由、涉及模块、预期修改和潜在新增复杂度。
7. 分类：`IN_SCOPE`、`NEEDS_APPROVAL` 或 `OUT_OF_SCOPE`。

## 决策规则

- 只有 `IN_SCOPE` 才能进入实现计划。
- `NEEDS_APPROVAL` 必须等待用户明确确认。
- `OUT_OF_SCOPE` 不得实现，只能进入 Parking Lot。
- 不得以“顺便优化”或“未来可能用到”为理由扩大范围。
- 优先选择最小、可逆、可验证的修改。
- 若范围文件缺失，列出缺失证据；不要凭空判定为 `IN_SCOPE`。
