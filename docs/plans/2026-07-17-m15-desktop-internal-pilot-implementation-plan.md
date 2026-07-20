# M15 Desktop 内部试用版 Implementation Plan

> **For agentic workers:** Inline execution only. Do not spawn sub-agents without user permission. Track every step with checkbox syntax.

**Goal:** 让内部运营人员在 Hermes Desktop 中无需 CLI、Prompt 工程和 task ID，完成产品 onboarding、环境检查、自然语言任务、三个审阅节点、恢复和反馈。

**Architecture:** 扩展现有 Product Creative plugin-owned Desktop 页面和 dashboard API；业务执行继续进入 Hermes chat/Agent Runtime，后端适配只复用 Command Bus 与现有诊断能力，不建立平行任务系统。

**Tech Stack:** Python/FastAPI/Pydantic、现有 Product Creative runtime、vanilla Desktop plugin bundle、React host、Vitest/jsdom、pytest、Electron Builder。

## Global Constraints

- 不修改 Product Brain 数据结构、数据库 schema 或 Hermes 产品专属 core 行为。
- 不输出密钥值；`DOUBAO_API_KEY` 为豆包最高优先凭据。
- XHS/Douyin 是可选来源，离线不得阻断普通创作。
- 不真实调用 Provider、Cookie 或外部平台。
- 不 commit、push、tag、release；不清理现有脏工作区和临时目录。
- M14 Live Gate 保持 pending，不用 M15 UI 测试替代真实样片验收。

---

## Task 1：安全 Desktop 诊断服务

**Files:**
- Create: `.hermes/plugins/product_creative/runtime/desktop_diagnostics.py`
- Modify: `.hermes/plugins/product_creative/dashboard/plugin_api.py`
- Test: `tests/hermes_cli/test_product_creative_m15_desktop_pilot.py`

**Produces:** `collect_desktop_diagnostics() -> dict` 与 `GET /v1/diagnostics`。

- [x] 写失败测试：响应包含 Hermes、豆包三能力、DeepSeek、SiliconFlow、real-provider、ffmpeg、ffprobe、XHS 和 Douyin 检查。
- [x] 写失败测试：响应 JSON 不包含测试密钥字面量，缺失可选 Sidecar 不改变核心 `overall_status`。
- [x] 运行两个测试，确认因模块/路由不存在而失败。
- [x] 实现固定 loopback、短超时、只报告存在性的诊断服务。
- [x] 接入只读 API，并运行测试至通过。

## Task 2：产品 onboarding API

**Files:**
- Modify: `.hermes/plugins/product_creative/dashboard/plugin_api.py`
- Test: `tests/hermes_cli/test_product_creative_m15_desktop_pilot.py`

**Produces:** `POST /v1/products`。

- [x] 写失败测试：产品名称可创建当前 workspace 产品，描述进入 Evidence/Draft，Canonical Brain 未被自动确认。
- [x] 写失败测试：空名称返回 422；同名产品返回 409 且不摄入新描述。
- [x] 运行测试，确认路由不存在或方法不允许。
- [x] 复用 `product_workspace_resolve` 与 `product_ingest` 实现薄适配。
- [x] 运行 onboarding 与既有 Desktop API 测试至通过。

## Task 3：无产品 onboarding 界面

**Files:**
- Modify: `.hermes/plugins/product_creative/desktop_ui/index.js`
- Modify: `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`

**Produces:** 产品名称/可选 ID/描述表单、创建状态、进入聊天补资料/主图动作。

- [x] 写失败 UI 测试：无产品时出现 onboarding 表单而非终止空状态。
- [x] 写失败 UI 测试：提交调用 `POST /products`，创建后选择新产品并重新加载。
- [x] 运行 Vitest，确认新界面不存在而失败。
- [x] 实现 onboarding render、表单状态、提交和错误处理。
- [x] 运行 UI 测试至通过。

## Task 4：自然语言任务入口与恢复

**Files:**
- Modify: `.hermes/plugins/product_creative/desktop_ui/index.js`
- Modify: `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`

**Produces:** 自由目标输入、视频/图片/了解产品预设、`continueInChat`、任务继续/补充信息动作。

- [x] 写失败测试：运营人员输入“帮我做一个今天能发的产品视频”后，Desktop 将当前产品上下文与原始目标交给聊天。
- [x] 写失败测试：继续任务按钮生成包含 task ID 的内部恢复消息，但按钮文案不要求用户复制 ID。
- [x] 运行测试确认失败。
- [x] 实现任务 composer、预设按钮、继续/补充动作和空输入校验。
- [x] 运行 UI 测试至通过。

## Task 5：三个审阅节点和引导式 Overview

**Files:**
- Modify: `.hermes/plugins/product_creative/desktop_ui/index.js`
- Modify: `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`

**Produces:** 产品事实、创意方向、成片质量三节点的 `pending/attention/ready/approved` 投影。

- [x] 写失败测试：Overview 显示三个节点和阻塞原因。
- [x] 写失败测试：Review 按三个节点分区，并保留现有 confirmation reason 门禁。
- [x] 运行测试确认失败。
- [x] 从现有 snapshot/task/professional artifact 派生节点，不新增持久状态。
- [x] 运行 UI 测试和 confirmation 回归至通过。

## Task 6：Settings 与环境诊断体验

**Files:**
- Modify: `.hermes/plugins/product_creative/desktop_ui/index.js`
- Modify: `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`

**Produces:** 第六个 Settings 视图、诊断刷新、必需/可选状态与 Hermes 设置入口。

- [x] 写失败测试：Settings 展示 Provider/Media/Optional Sources，XHS/Douyin 离线标记为可选。
- [x] 写失败测试：刷新诊断只发 GET，不触发 durable mutation 或 Provider 调用。
- [x] 运行测试确认失败。
- [x] 实现 Settings 状态、诊断卡片、刷新和 `host.navigate('/settings')`。
- [x] 运行 UI 测试至通过。

## Task 7：工作区、语言与 cleanup 回归

**Files:**
- Modify: `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`
- Modify only if test proves needed: `.hermes/plugins/product_creative/desktop_ui/index.js`

- [x] 增加 workspace 切换重挂载测试，确认不复用旧产品/任务/诊断。
- [x] 增加 zh-CN/英文关键动作测试。
- [x] 增加 cleanup 后定时刷新和事件不再运行的测试。
- [x] 先运行并记录实际失败；仅修复被测试证明的问题。
- [x] 运行完整 Product Creative bundle 测试至通过。

## Task 8：内部试用分发与文档

**Files:**
- Create: `docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md`
- Modify: `AGENTS.md`
- Modify: `docs/PROJECT_STATE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/AI_HANDOFF.md`
- Modify: `docs/ARCHITECTURE_CURRENT.md`
- Modify: `docs/DECISION_LOG.md`
- Modify: `.hermes/plugins/product_creative/README.md`

- [x] 运行 Python M15、Desktop API、Product Creative UI、bundle、typecheck、production build。
- [x] 运行 M10–M14 相关回归、M9 recovery、public surface 和 `git diff --check`。
- [x] 导出临时分发包并执行敏感扫描、版本/哈希校验和 enabled user-plugin 离线安装。
- [x] 尝试现有 Hermes Desktop Windows NSIS 构建；若环境缺少签名/缓存/网络，记录准确阻塞，不修改安装器架构。
- [x] 写入完整文件清单、命令、结果、已知限制、恢复顺序和人工试用脚本。
- [x] 只有安装包构建与内部运营人工全链完成后，才把 M15 标记为 DONE；否则使用精确 PARTIAL 状态。
- [x] 在原生隔离环境验证“打包 Desktop 壳 + 当前 worktree runtime + enabled user plugin”的 backend、bundle、诊断和 onboarding。
- [x] 选择方案 A，并将实现提交 `25e26df` 推送到可获取的 origin pilot ref。
- [ ] 重建后确认 install stamp 对应最终 pilot HEAD，并执行隔离 fresh-install。
- [ ] 内部运营人员使用可复现的 Windows 安装形态完成一次全链并提交接受/修改记录。

## Completion Audit

- [x] 用户无需 CLI、payload、Prompt 工程或 task ID。
- [x] 无产品、成熟产品、任务阻塞、任务恢复、QA 审阅均有明确 UI 路径。
- [x] 诊断不泄露密钥且可选来源不阻断。
- [x] 所有 durable mutation 仍使用既有确认和审计边界。
- [x] 没有新增平行 Agent、任务存储、Provider 或创作画布。
- [x] Desktop 壳构建、本地组合试运行与未完成 standalone/operator Gate 如实分开记录。
