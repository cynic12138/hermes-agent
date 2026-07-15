# Project State

- 日期：2026-07-15
- 分支：`product-creative-runtime`
- M9.1 实现提交：`83b4e8f`
- 已提交阶段：M9.1 Desktop Plugin SDK 迁移（DONE、本地已提交）
- 发布阶段：未 push、未 tag、未 release
- 工作区保护状态：存在大量 tracked/untracked M9.1 与恢复文档；未执行 clean/stash/reset/checkout。

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
- 真实 image/video/VLM provider：仅特定 adapter 支持，默认关闭。
- XHS/Douyin sidecar：仓库外依赖；历史 workspace 迁移完成度 UNKNOWN。

## PLANNED

- M10 从 0 对话建脑/guided generation；实施计划位于 `docs/plans/2026-07-14-m10-zero-to-product-brain-plan.md`，尚未获得编码授权。

## BLOCKED

- production provider 演示：被凭据、网络、外部服务、费用与确认阻塞。
- M10 实现：等待用户批准，并先完成产品访谈与设计门禁。

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

## 下一步推荐

下一唯一推荐任务是由用户审阅并确认 `docs/plans/2026-07-14-m10-zero-to-product-brain-plan.md`，再决定是否实现。M9.1 push/release 和 `pytest-of-unknown/` 清理仍需分别授权。

待确认问题见 `docs/OPEN_QUESTIONS.md`。
