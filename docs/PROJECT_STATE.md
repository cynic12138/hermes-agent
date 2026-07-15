# Project State

- 日期：2026-07-15
- 分支：`product-creative-runtime`
- M9.1 实现提交：`83b4e8f`
- 当前 HEAD：`8ba592cdca0e835580771795cafea424e3618e0d`
- 已提交阶段：M9.1 Desktop Plugin SDK 迁移（DONE、本地已提交）
- 当前工作区阶段：M10 产品认知驱动的自主创作智能体（PARTIAL、未提交）
- 发布阶段：未 push、未 tag、未 release
- 工作区保护状态：存在 tracked/untracked M10 实现与知识文档；未执行 clean/stash/reset/checkout；既有 `pytest-of-unknown/` 保持未跟踪。

## DONE

- M0–M8 durable runtime 汇总基线（`1d223d3`；阶段细粒度历史不可恢复）。
- Product Brain、产品摄入、素材、文案、图片、视频、灵感、审阅、反馈/学习、exact-main-video。
- SQLite workflow/event/receipt/outbox/provider task/learning/recovery 数据模型。
- M9 backend、6 个受控恢复命令、HEAD 固定 Desktop 控制台（`f8bdb0c`）。
- Windows plugin clone 只读文件删除修复（`822d879`）。
- M9.1 通用 Desktop Plugin SDK v1：认证 discovery/bundle API、enabled bundled/user gate、project plugin executable page 禁止、路径/大小/哈希/API/版本/身份校验。
- 冷启动深链、完整宿主保留路由、bundle 注册事务隔离、loading/error 诊断、mount/cleanup 与 workspace/locale 重挂载。
- Product Creative plugin-owned Overview/Tasks/Review/Assets/Learning 五视图及确认原因门禁。
- `9.1.0-alpha.1` 版本统一、tracked-only 分发、`SOURCE.json` 双层哈希、敏感数据扫描、离线 enabled user-plugin 安装 E2E。
- Node `22.23.1` 定向 UI/typecheck/production build；M9 recovery 25/25、public surface 84 tools/84 CLI 回归通过。
- 发布 workflow 的 Desktop Vitest 调用已改为通过 `apps/desktop` 的 `test:ui` script 执行，避免从仓库根目录丢失 Vite alias 和 bundle 相对路径。
- M9.1 实施、恢复顺序、文件职责和验证证据已固化到 `docs/M9_1_DESKTOP_PLUGIN_SDK_IMPLEMENTATION.md`。

## PARTIAL

- M9.1 尚未 push/release；云端分发仓库未修改。
- M10 自然语言 Creative Task：已实现产品认知分层、任务 Readiness、主动追问、有界编排、任务授权、素材/灵感、Mock 文图视频、反馈学习、Desktop 可见性和 Fake live provider 恢复；工作区未提交。
- M10 Live：真实 image/video/VLM provider 默认关闭，未使用真实凭据/网络验收；XHS/Douyin sidecar 是仓库外依赖，未现场验证。
- M10 用户验收：尚未完成一次新产品自然语言建脑和一次真实可播放视频交付。

## PLANNED

- M10.1 Live 纵向验收与适配器硬化：只选择一个现有 Provider 和已存在数据源，不扩展平台；需用户另行确认测试素材、凭据、Cookie/来源和费用上限。

## BLOCKED

- production provider 演示：被凭据、网络、外部服务、费用与确认阻塞。
- M10 DONE：等待用户 Live 验收、外部凭据/服务和费用授权。

## DEPRECATED

- Product Creative 专属 Desktop core route/component 是 HEAD 可用实现，但工作区目标已改为通用插件页面。
- 将脚本作为用户主入口；M2 继续追加小功能；M6 remote-url-first 旧理解。

## UNKNOWN

- MVP 发布口径、生产 SLA、多用户/平台发布路线。

## 技术债与风险

- enabled Desktop plugin 与宿主同源且被视为受信任；renderer workspace header 不是恶意插件隔离边界。
- media descriptor 使用本地绝对路径，remote Desktop 预览未验收。
- 宿主全量 UI 套件存在多项与 M9.1 无关的既有失败；M9.1 定向门禁已通过。
- `pytest-of-unknown/` 是规范测试包装器在当前 Windows 环境产生的未跟踪临时目录；未获用户授权前不删除、不提交。
- `verify_m2_workflow_run.ps1` 在 Windows 嵌套 PowerShell 下长时间无输出，未完成，不能列为通过或失败。

## 2026-07-15 M10 工作区验证

- M10 Python：24 passed（真实 Hermes agent loop + fixture/mock/Fake Gateway；无网络/费用）。
- Desktop SDK Node bundle：2 passed。
- Desktop routes/registry/page/Product Creative UI：16 passed。
- Desktop backend API/distribution：15 passed（使用仓库现有 `.venv`；系统 Python 因缺 `python-multipart` 未进入收集）。
- Distribution bundle registry：1 passed；离线 user-plugin install passed；版本/哈希/敏感数据 validation passed。
- TypeScript typecheck passed；Desktop production build passed（dirty stamp、既有 CSS 和大 chunk warning）。
- M9 review/recovery：25/25；Product Brain boundary：0 failures；contract invariants：51 actions / 84 tools / 84 CLI；public-surface golden hash 匹配。
- `git diff --check`：通过，仅 CRLF 转换 warning。
- 未运行真实网页/XHS/抖音、Cookie、图片/视频/VLM Provider 或生产 API。

## 下一步推荐

先审阅并提交当前 M10 工作区（需用户单独授权）；随后唯一推荐开发任务是 M10.1 Live 纵向验收与适配器硬化。开始 Live 前必须由用户确认测试产品/素材、Provider、数据源、Cookie 范围和费用上限。实施细节见 `docs/M10_PRODUCT_COGNITION_AUTONOMOUS_CREATION_IMPLEMENTATION.md`。

待确认问题见 `docs/OPEN_QUESTIONS.md`。
