# MVP Scope

> 仓库证据重建稿。Product brief 用户访谈尚未完成；目标用户和发布口径需确认。

## 当前目标

用户可以从产品名称、少量素材或一个内容目标开始；Hermes 通过自然语言主动询问和索要证据，逐步建立经用户确认的 Product Brain，再围绕同一产品持续生成、审阅和改进真实图片/视频。系统保存可恢复状态，并只在显式确认后更新长期 Product Brain。

## 必须完成

- workspace/Product Brain 解析与 generation-safe 读取。
- 空白产品工作区、Evidence Inbox、Draft Understanding 和 Canonical Product Brain 明确分层。
- Hermes 根据当前任务主动识别知识缺口、小批次追问、复述理解，并提交字段级确认 proposal。
- 用户回答“不确定”时保留 UNKNOWN，不让模型或网页自动补为产品事实。
- 素材、文案、图片/视频 brief 和结果的 durable workflow。
- 审阅、反馈、proposal、确认后新 Brain 版本。
- provider/外部副作用 guard、receipt、事件与恢复。
- Hermes 对话启动；Desktop 浏览和受控恢复。
- M9.1 plugin-owned 页面完成 build、user-plugin 安装和隔离 workspace E2E。（工作区已完成，待用户决定提交/发布）
- 无密钥/产品 DB/artifact 进入 Git 或分发。

## 可选

- 明确 opt-in 的真实 image/video/VLM provider。
- XHS/Douyin sidecar 小样本采集；exact-main-video。

## 不做

- 未完成 product brief、PRD、UX/架构和自然语言 E2E 设计前实现 M10 对话式产品发现/guided launch。
- 新 provider/抓取平台/向量库/消息队列。
- 完整 Web 工作台、多人/租户/权限/计费、云 SLA。
- 自动发布、自动付费调用、未经确认的 Brain/素材变更。

## 二期候选

Guided launch、结构化 brief 编辑/结果对比、经确认的 provider/sidecar 扩展、团队/云/平台发布。

## 新需求准入

必须直接补齐核心闭环或 M9.1 可交付性；有证据与验收；复用现有 capability/CommandBus/repository/plugin SDK；不绕过安全边界；不建平行实现；有无外部副作用的验证路径。

修改前使用 `.agents/skills/scope-gate` 与 `redundancy-review`；`NEEDS_APPROVAL` 等待用户，`OUT_OF_SCOPE` 写入 `docs/PARKING_LOT.md`。
