# 周十五益生菌蜂蜜露严格证据基线

- 建立日期：2026-07-16
- 模式：`EVIDENCE_FIRST_STRICT`
- 隔离 workspace：`C:\data\work file\hermers-agent for me\product-creative-clean-workspace`
- Product ID：`zhoushiwu`
- 状态：`NEEDS_INPUT`

本文件记录全新 Product Creative workspace 的真实初始化结果。它不把公开网页、模型理解或用户原始健康描述直接写成 Canonical Product Brain。

## 分层结果

| 信息 | 所在层 | 状态 | 说明 |
|---|---|---|---|
| 产品名称“周十五益生菌蜂蜜露” | Canonical | CONFIRMED | 用户明确指定的产品身份 |
| 用户完整产品描述 | Evidence Inbox / Draft | INFERRED | 保留原话和结构化理解，不代表合规批准 |
| 两张本地产品图片 | Canonical asset registration | CONFIRMED | 仅确认文件、哈希、素材角色；不自动确认图片中视觉结论 |
| 当前主图 | Product Brain | UNKNOWN | 两张图均登记为 `product_photo`，尚未人工选择 `current_main_image` |
| SKU/包装版本 | Product Brain | UNKNOWN | 缺少背标、说明书或公司正式 SKU 信息 |
| 成分“蜂蜜和益生菌” | Evidence/Draft | INFERRED | 用户原话；正式资料到齐前不升级 |
| 适用人群“孕妇、便秘群体” | Evidence/Draft | CONFLICTED | 高风险健康/适用人群表述，必须由正式资料和合规负责人确认 |
| “快速有效通便” | Evidence/Draft | CONFLICTED | 禁止直接用于正式创作 |
| “温和不刺激” | Evidence/Draft | CONFLICTED | 禁止直接用于正式创作 |
| “安全有效” | Evidence/Draft | CONFLICTED | 绝对化安全/效果表述，禁止直接使用 |
| 外观可爱、便携、不尴尬 | Pending proposal | INFERRED | 可作为低风险候选，但仍需字段级确认 |

## 素材登记

| Material ID | 原文件 | SHA-256 | 角色 | 当前主图 |
|---|---|---|---|---|
| `material-20260716-164659-fd6735a1` | `周十五产品垫图\1.png` | `fd6735a1595eea489af7127f4a6adc408ef9bb831851376b0488c392405a8801` | `product_photo` | 否 |
| `material-20260716-164659-399bff8f` | `周十五产品垫图\2.jpg` | `399bff8f4ca88429dd6c7caa3582e1aee70ee41be9fef981b3e465f40bb05e0a` | `product_photo` | 否 |

图片的登记只证明用户提供了素材及其二进制身份。VLM/OCR 结果未来必须进入 Evidence/Draft；不得因模型看到包装文字就自动确认产品事实。

## 合规提案

- Proposal ID：`proposal-20260716-164659-bb6dce`
- 字段：`claim_boundaries`
- 状态：`proposed`
- Canonical 是否改变：否

建议允许的低风险方向：

- 产品名称。
- 可爱包装。
- 便携。

建议禁止或等待正式证据的方向：

- 快速/有效通便。
- 温和、不刺激。
- 安全、有效。
- 孕妇适用。
- 治疗便秘。
- 保证性、绝对化或未核验健康宣称。

## 当前 Readiness

目标示例：“帮我做一个今天能发的周十五产品视频”。

当前不可直接真实生成，代码实际记录的阻塞项：

1. `claim_boundaries` proposal 未确认。
2. 产品 SKU/当前包装版本未知。

Readiness resolver 把第一张 `product_photo` 识别为已有商品主体/包装证据，因此没有报“缺少包装素材”；但它仍不是人工确认的 `current_main_image`。在正式 exact-main 生成前，必须另外确认主图选择和包装保真路线。场景、人物、剧情和视觉风格等非阻塞信息可以在 Task Context 中临时决定，但必须标明它们不是产品事实。

## 下一次用户确认

按信息增益优先询问：

1. 两张图片中哪一张是当前正式主图，另一张是什么用途？
2. 当前素材对应哪个 SKU/规格/包装版本？
3. 是否确认采用本文件的保守宣称边界，直到公司正式资料替换？

确认后应通过现有 proposal/confirmation/receipt 流程更新，不得直接编辑 Canonical JSON。
