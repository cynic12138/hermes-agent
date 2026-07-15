# Repository Inventory

- 审计时间：2026-07-12 15:41:51（Asia/Shanghai）
- 调研工作目录：`C:\data\work file\hermers-agent for me`
- 实际 Git 根：`C:\data\work file\hermers-agent for me\hermes-agent`
- Git：是；分支 `product-creative-runtime`
- HEAD：`822d879125a0fd20f784efe3f75626c720b608ab`
- upstream：`origin/product-creative-runtime`，ahead/behind `0/0`
- remote：`origin=https://github.com/cynic12138/hermes-agent.git`；`upstream=https://github.com/NousResearch/hermes-agent.git`
- tag：`product-creative-durable-runtime-v1`（指向 `1d223d3`）
- worktree：仅当前 worktree；submodule：无
- 可见 Git 历史：4 条（浅化/嫁接历史，早期细粒度历史不可恢复）

## 恢复前工作区状态

**CONFIRMED — 高风险脏工作区**：23 个 tracked 变更项、7 个 untracked 顶层项；tracked diff 约 `+282/-851`。未执行 clean、stash、reset、checkout、commit 或 push。

主要 tracked 变化：

- 删除 4 个 `apps/desktop/src/app/product-creative/*` 固定页面文件。
- 修改 Desktop/Electron、`hermes_cli/web_server.py`、插件 manifest/API/发布脚本。

主要 untracked 变化：

- `apps/desktop/src/app/desktop-plugins/`
- `apps/desktop/electron/desktop-plugin-bundle*.cjs`
- `.hermes/plugins/product_creative/desktop_ui/`
- `.hermes/plugins/product_creative/scripts/build_desktop_bundle.py`
- `tests/hermes_cli/test_desktop_plugin_pages.py`

这些文件共同构成 M9.1 迁移；只保留 tracked diff 或删除 untracked 文件会造成替代实现缺失。

## 关键文件存在性（恢复前）

| 项目 | 状态 |
|---|---|
| `AGENTS.md` | 存在，约 72KB，上游 Hermes 总体开发指南 |
| `.agents/skills/` | 不存在 |
| `.codex/config.toml` | 不存在 |
| `bmad/` / `docs/bmad/` | 不存在 |
| `docs/AI_HANDOFF.md` | 不存在 |
| `docs/PROJECT_STATE.md` | 不存在 |
| `docs/MVP_SCOPE.md` | 不存在 |
| README | 根目录多语言 README；Product Creative README 位于插件目录 |
| PRD | 未发现正式 PRD |
| Roadmap | `.hermes/plugins/product_creative/docs/PRODUCT_MAINLINE_ROADMAP.md` |

## 仓库规模与技术入口

- Git tracked files：约 6,280；其中 tests 1,911、apps 851、Product Creative 插件约 330。
- Python/Hermes：`pyproject.toml`、`run_agent.py`、`hermes_cli/`。
- Desktop：`apps/desktop/`（Electron + React + TypeScript）。
- Product Creative：`.hermes/plugins/product_creative/`。
- 数据：workspace 内 SQLite + artifact/media 文件。
- Product Creative 验证脚本：64 个已跟踪 `verify*.ps1`。

## 最近提交

1. `822d879`（2026-07-12）Windows 插件只读 Git clone 删除修复。
2. `f8bdb0c`（2026-07-12）M9 review/recovery console。
3. `1d223d3`（2026-07-12）M0–M8 durable runtime 汇总基线。
4. `88d1d62` 上游 streaming 修复/分支基点。
