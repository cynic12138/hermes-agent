# Product Recovery

## 一句话定义

**CONFIRMED**：Product Creative 是运行在 Hermes Agent 上、围绕单一产品长期维护 Product Brain，编排文案/图片/视频生产，并将反馈经人工确认安全沉淀回长期认知的耐久化内容智能体。

证据：`.hermes/plugins/product_creative/README.md:3-5`、`docs/AI_DRIVEN_PRODUCT_CREATIVE_RUNTIME_ARCHITECTURE.md:7-18`、`docs/PRODUCT_CREATIVE_CONVERSATION_PROTOCOL.md:7-32`。

## 用户、问题与闭环

- **INFERRED** 目标用户：持续为同一商品制作小红书、抖音、电商和视频内容的品牌方、商家或内容运营人员；正式 persona/团队边界未定义。
- **CONFIRMED** 核心问题：单次生成缺乏长期产品上下文、素材和反馈难复用、外部模型可能改变产品事实/包装、长流程不可审计或恢复。
- **CONFIRMED** 闭环：自然语言目标 → workspace/Product Brain/素材读取 → LLM 结构化决策或确定性回退 → guarded workflow → artifact → 审阅/反馈 → rule/proposal → 显式确认 → 新 Brain 版本 → 下一轮 generation-safe context。

## 当前范围

- **DONE/CONFIRMED**：Product Brain、产品摄入、素材卡、文案、图片 brief/生成、视频 brief/异步任务、外部灵感、结果审阅、反馈/提案、exact-main-video、durable workflow、M9 review/recovery API。
- **PARTIAL**：真实 provider 仅特定 provider 支持，默认关闭且需凭据/确认；M9.1 Desktop plugin-owned UI 尚未提交和完整验收。
- **PLANNED**：M10 guided generation launch controls（当前生成仍由 Hermes 对话启动，README:5）。
- **UNKNOWN**：正式目标客户、多用户/团队、付费、生产 SLA、平台发布是否进入路线。

## 非当前范围

- 不扩成新爬虫平台、工具堆或脚本中心。
- 不自动执行付费 provider、外部发布、Product Brain 写入或核心素材变更。
- M9.1 收口前不进入 M10。

## 术语

- Product Brain/Product Wiki：已确认的产品事实、卖点、风格、渠道与学习。
- Workflow：可暂停、恢复、审计的步骤序列。
- Artifact/Material：生成或审阅产物 / 输入素材。
- Guard boundary：需要输入、确认、凭据或安全判断时停止。
- Writeback proposal：待审阅的长期认知更新。
- Exact-main-video：固定真实产品主图、不让模型重绘包装的视频路径。

## 产品问题

1. M9.1 是否是正式目标基线？
2. `0.9.0-alpha.1` 是否是预期发布版本？
3. MVP 是否只要求“对话启动 + Desktop 审阅/恢复”，还是包含 guided launch？
4. sidecar/真实 provider 是 MVP 还是可选实验能力？
