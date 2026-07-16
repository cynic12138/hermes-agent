# M11 专业创意工作流与质量门禁实施计划

- 日期：2026-07-16
- 前置基线：M10.1 Live 技术链路可运行；真实样片创意质量未通过
- 开发方式：方案 1，继续在 Hermes 仓库内开发 `product_creative` 插件
- 首条纵向验收：周十五产品剧情短视频
- 状态：`READY_FOR_IMPLEMENTATION`

## 1. 本阶段解决什么

M11 不新增 Provider，也不追求一次生成更多视频。它解决当前最大的产品缺口：系统虽然能搜索、选素材和调用模型，却可能在没有有效创意、剧情和生产方案时直接生成，最终得到“主图加空话”或包装乱码的视频。

本阶段把一句用户目标转换为可审阅、可测试的专业创意产物：

```text
用户目标
→ Creative Task Brief
→ Product Grounding Pack
→ Research Insight Pack
→ 3 个 Creative Candidates
→ Creative Decision
→ Story Package
→ Production Bible
→ Preflight QA
→ Provider-ready
```

任何关键产物缺失或不合格，真实生成都必须停止。

## 2. 范围

### 本阶段必须完成

- 专业创意中间产物的版本化契约与持久化。
- Goal Planner 按产物和 Gate 推进，而不是按静态动作列表推进。
- 一个完整的产品剧情短视频 workflow。
- 三方向创意候选：稳定、变化、探索。
- 独立 Creative Decision 与拒绝理由。
- 具体钩子、冲突、推进、转折和结尾。
- Production Bible 与 Provider 输入之间的字段级追踪。
- 生成前质量门禁和失败诊断。
- Hermes 自然语言离线 E2E。

### 本阶段不做

- 新增图片/视频/VLM Provider。
- 真实 XHS/Douyin/付费调用作为日常自动测试。
- 自动媒体 QA 和自动返修闭环（M14）。
- 逐镜头混合合成引擎（M13）。
- 全部视频类型、矩阵批量、自动发布或效果分析。
- 多 Agent 自由讨论群。
- 正式拆分独立源码仓库。

## 3. 复用边界

继续复用：

- `product_workspace_resolve`、`product_workflow_run` 公共入口。
- Product Brain、Discovery、Readiness、Evidence/Proposal。
- Material Card、Task Material Pack、Material Resolver。
- Web/XHS/Douyin snapshot 与 inspiration candidate。
- Command Bus、Guard、Confirmation、Receipt/Event。
- Creative Task durable state、provider task 和 recovery。
- Desktop Tasks/Review/Assets/Learning。

不新建第二套任务数据库、聊天工具、素材库、Provider registry 或 Product Brain。

## 4. 新增内部契约

所有产物包含 `schema_name`、`schema_version`、`task_id`、`product_id`、`created_at`、`source_refs`、`status` 和内容哈希。

### 4.1 `creative_task_brief.v1`

- 用户原始消息。
- 解释后的目标。
- 渠道、交付物、时长、比例、日期约束。
- 自主模式与授权范围。
- 必须满足和明确禁止的要求。
- 可由系统自主决定的低风险字段。
- 未知字段和假设。

### 4.2 `product_grounding_pack.v1`

- Product Brain 版本/指纹。
- SKU、当前包装和主图。
- 已确认卖点、禁用表述和素材权利。
- Creative Profile/渠道偏好（如有）。
- 任务级 Readiness 与 blocker。
- 所有字段的 evidence refs。

### 4.3 `research_insight_pack.v1`

- 研究目标与数据源。
- Web/XHS/Douyin/历史素材的来源专属洞察。
- 近期性、来源日期和可信度。
- 可复用钩子、场景、结构和风险。
- `not_product_fact=true`。
- 研究失败和降级说明。

### 4.4 `creative_candidate.v1`

默认生成三个：

- Stable：产品明确、易执行、低风险。
- Variation：基于已验证模式做明显变化。
- Exploration：新叙事或新视觉，但仍受产品边界约束。

每个候选必须包含：

- 一句话创意。
- 用户为什么会停留。
- 产品为何自然进入剧情。
- 目标情绪和渠道适配。
- 0–3 秒钩子。
- 剧情冲突与推进。
- 结尾/CTA。
- 所需素材与制作路线。
- 来源引用。
- 风险、成本和可执行性。
- 与历史内容的差异。

### 4.5 `creative_decision.v1`

- 候选评分。
- 评分维度：产品匹配、渠道适配、新鲜度、可执行性、包装安全、合规风险。
- 选中候选和明确理由。
- 未选候选的淘汰原因。
- 是否需要用户预览/确认。
- 允许后续步骤偏离的范围。

### 4.6 `story_package.v1`

- 核心命题。
- 角色及动机。
- 场景和世界规则。
- 0–3 秒视觉/声音钩子。
- 起因、冲突、升级、转折、产品介入和结尾。
- 口播/对白/字幕文案。
- 每段承担的叙事功能。
- 禁止出现的内容。

### 4.7 `production_bible.v1`

- 总规格：比例、时长、语言、风格、音频。
- 逐镜头编号、时长、构图、动作、角色、场景。
- 每镜头输入素材及其角色。
- 产品 plate、背景生成、人物生成和字幕的边界。
- 包装保真策略。
- 连续性规则。
- Provider capability 与 payload 映射。
- 单镜头失败后的重试/降级策略。
- 最终合成与可审阅文件要求。

### 4.8 `qa_report.v1`

M11 只实现生成前 QA：

- Grounding 是否完整。
- 创意是否具体且非通用模板。
- 剧情是否有钩子、推进和结尾。
- 来源是否真正进入创意。
- 包装路线是否与保真要求一致。
- 文案是否碰触禁用表述。
- Production Bible 是否可执行。
- Gate 结果：`PASS`、`NEEDS_REVISION`、`BLOCKED`。

生成后自动媒体 QA 延后到 M14，但 M11 必须保留扩展位置。

## 5. 状态与 Gate

在现有 Creative Task 状态之上增加阶段产物状态，不新建平行状态机：

| Gate | 通过条件 | 失败状态 |
|---|---|---|
| Brief Gate | 目标、交付物、产品和关键规格可解释 | `NEEDS_INPUT` |
| Grounding Gate | 产品/SKU/包装/宣称满足当前任务 Readiness | `BLOCKED_PRODUCT` |
| Research Gate | 有可用 insight，或明确记录离线降级 | `FAILED_RETRYABLE` 或带降级继续 |
| Creative Gate | 至少 3 个有效候选且存在可解释决策 | `NEEDS_REVISION` |
| Story Gate | 钩子、冲突/推进、产品介入和结尾完整 | `NEEDS_REVISION` |
| Production Gate | Production Bible 字段齐全且包装路线安全 | `BLOCKED_PRODUCT` / `BLOCKED_PROVIDER` |
| Preflight QA | 无高风险未解决项 | 禁止进入 `GENERATING` |

硬性不变量：

- `selected_idea` 为空时不得生成。
- 只有通用形容词、通用字幕或“产品细节”占位词时不得生成。
- Research refs 存在但未进入候选/剧情时不得声称“基于热点/平台灵感”。
- 要求包装不变时，不得把整个产品交给生成式模型重绘。
- Gate 失败不得消耗真实 Provider 次数。

## 6. 实施节点

### M11.1 契约与仓储

1. 在现有 contracts/artifact repository 增加八类 schema。
2. 为每类产物实现校验、hash、版本与 source refs。
3. 复用 workspace artifact 存储和 SQLite event/receipt 索引。
4. 增加向后兼容读取：旧 M10 任务缺少产物时标记 `legacy_incomplete`，不伪造内容。

验收：契约单测、序列化 round-trip、非法空产物拒绝、旧任务可读。

### M11.2 Brief 与 Grounding

1. 从用户消息生成 Creative Task Brief。
2. 从 Canonical Brain、素材和确认记录生成 Grounding Pack。
3. 每轮最多提出 1–3 个高价值问题。
4. 用户“不确定”保留 UNKNOWN。

验收：周十五严格基线会因 SKU/宣称/主图选择而阻断，不会编造补齐。

### M11.3 Research Insight

1. 将现有 snapshot 转为来源专属 insight。
2. Web 输出时间事实/事件背景；XHS 输出消费者语言/场景；Douyin 输出前 5 秒、口播和节奏结构。
3. 所有 insight 保留 refs 和 `not_product_fact`。
4. 数据源失败按现有降级策略处理。

验收：fixture 研究结果可追踪进入候选，不修改 Brain。

### M11.4 Creative Director

1. 生成 Stable/Variation/Exploration 三候选。
2. 独立评分与选择，不让生成者自己给自己无条件通过。
3. `preview_first` 返回候选；`adaptive/direct` 自动选第一名。
4. 用户修改目标时形成 decision revision。

验收：三候选实质不同；每个候选能解释产品角色、钩子和制作路线。

### M11.5 Story 与分镜

1. 把选中候选展开为 Story Package。
2. 生成逐镜头 Production Bible。
3. 将主图、产品 plate、背景、人物、字幕和音频分开声明。
4. Provider payload 只由 Production Bible 编译，不直接从用户原话拼接。

验收：选择理由、剧情和镜头字段都进入最终 payload；无硬编码“从一个细节开始”等旧 fallback。

### M11.6 Preflight QA 与 Planner

1. 实现结构化 preflight QA。
2. Goal Planner 每步重新读取 durable artifacts。
3. Gate 通过后才生成下一阶段动作。
4. 重启时从最后 receipt 恢复，不重复创建候选或消耗 Provider。

验收：对每个缺失/风险给出可诊断 blocker；补齐后自然语言继续。

### M11.7 Desktop 审阅

在现有页面增量展示：

- Tasks：Brief、阶段和 blocker。
- Review：三候选、Decision、Story、Preflight QA。
- Assets：选中素材和 Production Bible。
- Overview：Grounding readiness。

不新建画布或时间轴。

### M11.8 E2E 与文档

主验收输入：

> 帮我做一个今天能发的周十五产品视频。

测试路径：

1. 严格基线下先追问并阻断。
2. fixture 回答补齐 SKU、主图和保守宣称。
3. fixture Web/XHS/Douyin 研究。
4. 形成三个候选并选择。
5. 形成 Story Package 与 Production Bible。
6. Preflight QA 通过。
7. Mock Provider 生成可审阅结果。
8. 用户要求修改后生成 revision，不覆盖原目标。
9. 中断后用自然语言继续。

必须保存：用户消息、Hermes 工具选择、task events、所有中间产物、Provider payload 和最终 descriptor。

## 7. 测试矩阵

- 单元：契约、问题排序、候选差异、评分、剧情完整性、包装路由、QA。
- 集成：artifact repository、Command Bus、Planner、durable resume、幂等。
- 离线自然语言 E2E：真实 Hermes agent loop + fixture LLM/source/provider。
- Desktop：阶段、候选、错误、加载、workspace/locale 切换。
- 回归：M9 recovery、M10、Live adapters、public surface、distribution、typecheck/build。
- 用户授权 Live：M11 离线完成后，只用 1 次小额度真实视频验收；不作为日常 CI。

## 8. 完成条件

M11 只有全部成立才可标记 DONE：

1. 用户不需要 product ID、CLI、JSON 或 Prompt。
2. 每个视频任务都有完整 Brief、Grounding、Decision、Story 和 Production Bible。
3. 三候选有实质差异且选择理由可解释。
4. 平台灵感可以追踪到具体创意，不污染 Product Brain。
5. 缺失关键产物时真实 Provider 零调用。
6. 包装不变要求选择安全路线。
7. 旧通用字幕模板不能作为剧情交付。
8. 任务中断后可自然语言恢复。
9. Desktop 能查看关键产物和 blocker。
10. 用户亲自审阅至少一次完整创意包，再决定是否运行真实生成。

## 9. 拆仓观察点

M11 继续方案 1。满足下列条件后，为 M12/M13 之间单独制定拆仓计划：

- 连续两个里程碑的公共契约无破坏性变化。
- 插件分发包在临时 user-plugin 安装后不依赖 Hermes 仓库隐式路径。
- Hermes 兼容版本和 CI 矩阵已自动化。
- 数据库 migration、workspace schema 和回滚责任明确。
- 独立仓库能运行契约、自然语言 E2E、Desktop bundle 和安全扫描。

在此之前，`hermes-product-creative` 继续是生成式分发仓库，不作为第二源码真源。

## 10. M11 之后

下一阶段为 M12“专业业务 Skills 与创意导演”：把已经由 M11 契约证明必要的任务导演、研究、创意策略、编剧、分镜、卡审和学习方法沉淀成稳定 Skills。不得在 M11 未形成可靠中间产物前提前扩张 Skill 数量。
