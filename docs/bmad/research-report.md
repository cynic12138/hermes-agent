# Research Report: Product Creative Repository Recovery

- 日期：2026-07-12
- 类型：代码库/产品/技术二手证据研究
- 状态：完成（不等同用户验证）

## 目标与方法

回答产品、用户、闭环、真实架构、实现进度和下一衔接点。来源按可信度排序：当前代码/配置/测试 → Git diff/commit → 文档。采用 HEAD 与工作区对照、跨源三角验证和反证搜索；未使用互联网或市场研究。

## 关键发现

1. **CONFIRMED**：项目是 Product Brain 驱动的耐久化产品内容智能体，不是单次生成器。
2. **CONFIRMED**：HEAD 真实已提交阶段是 M9；工作区是 M9.1 未提交迁移。
3. **CONFIRMED**：SQLite 是 durable runtime 真源，媒体/artifact 在 workspace；旧 JSON 主存储文档已过时。
4. **PARTIAL**：真实 provider/sidecar 只在特定配置下可用，默认 mock/offline。
5. **PLANNED**：M10 guided launch 尚未实现。

## 限制

- Git 仅 4 条可见提交，M0–M8 细粒度演化不可恢复。
- 未完成 product-brief 用户访谈，目标用户仍为 INFERRED。
- 恢复阶段未启动 Desktop、真实 provider 或外部 sidecar。

## 建议

先保护并验证 M9.1 整体，不开始 M10；随后完成 product-brief 访谈并确认 MVP/版本/provider 支持策略。

详细证据：`docs/recovery/20260712-154151/`。

---

## 2026-07-14 产品发现补充：从 0 建立 Product Brain

### 用户确认

- Product Brain 不应由网上搜索结果直接预填。
- 用户可以从产品名称、少量素材或一个目标开始，Hermes 在自然语言对话中主动提出问题和资料需求，逐步建立产品认知。
- 网页/社交检索只进入 Evidence Inbox 或 Inspiration；高影响认知仍需人工确认。

### 实现交叉验证

- **CONFIRMED** `brain/wiki.py` 已能创建“待补充/Open Questions”的空白页面。
- **CONFIRMED** `runtime/conversation.py`、workflow plan 和 guard 已支持自然语言动作映射、通用缺参提示及确认门禁。
- **PARTIAL** 未发现完整的产品知识缺口模型、问题优先级、字段级证据审核和主动访谈编排。
- **PARTIAL** 现有自然语言 E2E 主要由 PowerShell 脚本输入预设句子，不能证明真实用户自由对话从 0 建脑已验收。

### 结论

项目已有对话执行和安全写回基础，但“从 0 自主了解产品”仍是未完成的产品体验层。M9.1 收口后，推荐将其与 guided generation 合并为 M10 的产品发现主线；设计和验收应先于实现。

详细目标流程：`docs/product-bases/zhou-shiwu-honeydew/ZERO_TO_PRODUCT_BRAIN.md`。
