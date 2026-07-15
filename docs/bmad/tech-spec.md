# Technical Specification — As-Is Recovery

- 项目：Hermes Product Creative
- 日期：2026-07-12
- 状态：恢复规格；非 stakeholder-approved PRD

## 范围

当前规格描述本地提交 `83b4e8f` 的 M9.1 实现，不规划新功能；该提交尚未 push/release。

## 功能要求（从代码反向确认）

- **FR-001 [MUST/DONE]** 解析产品 workspace/Product Brain。
- **FR-002 [MUST/DONE]** 通过 guarded durable workflow 执行内容/素材/图片/视频/审阅/学习动作。
- **FR-003 [MUST/DONE]** 持久化 workflow/event/receipt/outbox/provider task。
- **FR-004 [MUST/DONE]** 反馈生成 proposal，确认后创建不可变 Brain 版本。
- **FR-005 [MUST/DONE]** Desktop 查询 overview/tasks/review/assets/learning 并执行受控恢复。
- **FR-006 [MUST/DONE]** real provider/外部副作用保持显式 opt-in 和确认。
- **FR-007 [MUST/DONE]** Product Creative 页面由 enabled user plugin bundle 交付并被 Desktop 动态加载。
- **FR-008 [SHOULD/PLANNED]** Guided generation launch controls（M10，非当前实现）。

## 非功能要求（证据状态）

- **NFR-001 数据完整性 [FULL]** SQLite WAL/FULL/foreign keys/transaction/receipt/lease。
- **NFR-002 副作用安全 [FULL]** confirmation、real-provider gate、path canonicalization。
- **NFR-003 安全 [PARTIAL]** token/auth/hash/size/path checks；workspace header 与 path exposure 待审。
- **NFR-004 可维护性 [PARTIAL]** capability/port 边界与大量验证；统一 coverage/E2E 缺失。
- **NFR-005 性能 [MISSING]** 无量化响应/轮询/内存目标。
- **NFR-006 可用性/恢复 [MISSING]** 有 recovery 机制但无 SLA/RTO/RPO 和 restore drill 目标。

## 组件与数据

组件：Hermes plugin loader/FastAPI、Desktop plugin host、CommandBus、capability registry、durable workflow、repository/provider ports、SQLite/filesystem、outbox/provider adapters。

数据表和 API 详见 `docs/ARCHITECTURE_CURRENT.md` 与 `docs/recovery/20260712-154151/data_and_api_recovery.md`。

## 验证

- 已安全验证：Node 22 bundle/UI tests、typecheck/build、Python API/distribution tests、M9 recovery/public surface、tracked-only export、敏感扫描和 user-plugin 隔离 E2E。
- 已知非门禁失败：宿主全量 UI 套件仍有既有失败，未在 M9.1 中顺带修复。
- 禁止默认运行：live provider、外部 sidecar、会改真实 config/workspace 的启动脚本。
