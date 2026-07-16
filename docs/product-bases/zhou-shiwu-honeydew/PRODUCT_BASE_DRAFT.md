# 研究快照：候选产品事实

> 本文件是 Evidence Inbox 的人工整理视图，不是 Product Brain 初始化模板。新建产品时不得把下列候选值自动写入 canonical 字段；Hermes 应在对话中重新向用户展示证据、缺口和冲突，并逐字段请求确认。

## 产品身份

| 字段 | 当前值 | 状态 | 证据 | 备注 |
|---|---|---|---|---|
| 品牌/产品家族名称 | 周十五蜂蜜露 | CONFIRMED | USR-001、WEB-001 | 可作为检索和工作区名称 |
| 本次产品名称 | 周十五益生菌蜂蜜露 | CONFIRMED | USR-002、用户确认的 `1.png` | 可用于本次工作区定位；仍需公司正式 SKU 名称核验 |
| 产品用途类别 | 多个公开页面指向“外用蜂蜜露” | INFERRED | WEB-004、WEB-005、WEB-006、WEB-008 | 必须由当前包装/说明书确认 |
| 饮品属性 | 否定候选：不应按饮品建模 | CONFLICTED | CODE-001 对比 WEB-004/005/006 | 在正式资料到齐前，至少禁止“饮用、补水、口感、第一口”等表达 |
| 当前在售 SKU | 成人蜂蜜露、益生菌款、花朵益生菌款等分类 | INFERRED | WEB-001 | 这是店铺分类，不等于完整 SKU 清单 |
| 首个验证 SKU | 用户确认的 `1.png` 所示益生菌蜂蜜露包装 | CONFIRMED | USR-002、PKG-001 | 作为本次创作保真基线；规格和法定名称仍需背标/说明书核验 |
| 当前创作包装 | `周十五产品垫图\1.png` | CONFIRMED | PKG-001 | 用户于 2026-07-15 明确确认；不得据此推断背标、适用人群或功效 |

## 用户原始描述的隔离状态

用户提供了“外用通便、孕妇和便秘群体、快速有效通便、温和不刺激、肛门给入、蜂蜜和益生菌、安全有效、便携”等描述，并明确要求修正其中的高风险健康表述。当前处理如下：

| 描述项 | 当前状态 | 当前用途 |
|---|---|---|
| 外用产品 | INFERRED | 可作为待核对的 Draft Understanding；需包装背标/说明书确认 |
| 具体使用方法 | UNKNOWN | 禁止生成操作演示或指导，直至说明书和公司口径确认 |
| 蜂蜜、益生菌等成分 | UNKNOWN | 不作为正式成分或功效依据，直至背标/说明书确认 |
| 孕妇、便秘群体等适用人群 | UNKNOWN | 禁止对外生成适用承诺 |
| “快速有效通便” | UNKNOWN / HIGH_RISK | 禁止生成；需要公司合规批准的可用原句和证据 |
| “温和不刺激” | UNKNOWN / HIGH_RISK | 禁止生成；不得改写为安全保证 |
| “安全有效” | UNKNOWN / HIGH_RISK | 禁止生成；属于绝对化安全/效果承诺 |
| 可爱、不尴尬、便于携带 | INFERRED | 仅可作为视觉/体验方向候选；应避免羞辱或医疗效果暗示 |

以上内容只保留在 Evidence Inbox / Draft Understanding；不得自动写入 Canonical Product Brain。

## 候选市场表达

以下内容仅表示公开页面曾出现过，不能作为正式功效或合规宣称：

| 表达 | 状态 | 可用范围 | 证据 |
|---|---|---|---|
| “百亿益生菌/100 亿好菌” | INFERRED | 市场表达研究；正式使用前需包装和合规审核 | WEB-002、WEB-003 |
| “云朵”包装概念 | INFERRED | 历史包装设计和视觉研究 | WEB-002 |
| “音符”便携装/软管 | INFERRED | SKU 和包装版本研究 | WEB-004、WEB-006 |
| 便携、轻量、易携带 | INFERRED | 场景候选；需具体包装验证 | WEB-002、WEB-004 |
| 孕妇/产妇等人群适用 | UNKNOWN | 禁止生成 | WEB-004 等零售营销页，缺正式依据 |
| 任何治疗、缓解疾病、临床有效率 | UNKNOWN | 禁止生成 | WEB-010 为被拒绝来源 |

## 产品内容目标

- **CONFIRMED** 产品图片和短视频是当前主线交付物。
- **CONFIRMED** 小红书文案、电商文案、抖音口播脚本属于图片/视频生成的中间创意材料，不是本轮最终交付物。
- **CONFIRMED** 后续可调用本地小红书和抖音抓取能力作为外部灵感 sidecar，但抓取结果只能进入 raw/inspiration/proposal。
- **CONFIRMED** Product Brain 高影响字段继续使用人工审核后写入。
- **PLANNED** 最终面向公司内部运营人员提供易安装的桌面端软件；当前不作为本轮产品资料验证范围。

## 暂定受众与场景

由于缺少公司正式用户研究和商品说明，真实消费者画像保持 `UNKNOWN`。当前只记录创作系统用户：

- **CONFIRMED** 系统用户是公司内部运营人员。
- **INFERRED** 他们不应被要求自行编写复杂提示词，系统应在工作流节点内提供稳定提示和模型编排。
- **UNKNOWN** 周十五蜂蜜露的法定/建议使用人群、核心购买动机和禁用人群。

## 禁止复用的历史认知

以下仓库内容仅为冲突测试数据，不得进入真实 Product Brain：

- “清爽蜂蜜饮品”
- “清爽果蜜饮品”
- “夏季补水”
- “办公室补水”
- “自然蜜香、轻甜口感”
- “第一口不是甜腻，是清爽回甘”

主要证据位置：

- `docs/history/product-creative-legacy/original/verification-scripts/verify_m2_conversation_workflow.ps1:54`
- `docs/history/product-creative-legacy/original/verification-scripts/verify_m2_video_brief_review.ps1:46`
- `docs/history/product-creative-legacy/original/verification-scripts/verify_m2_workflow_run.ps1:61`
- `docs/history/product-creative-legacy/original/plugin-docs/M6_ASSET_HOSTING_AND_EXTERNAL_INSPIRATION_ARCHITECTURE.md:736`

这些脚本已归档为历史证据，不是当前验证入口；本轮只记录冲突，不把示例内容写入真实 Product Brain。
