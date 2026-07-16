# M10 产品认知驱动的自主创作智能体：历史计划与实施状态

> 用户已于 2026-07-15 授权实施，基线已本地提交为 `33d096f`。2026-07-16 的真实样片证明技术链路可运行，但创意与包装质量未通过；本文不再是下一开发计划。当前方向与路线以 `docs/PRODUCT_AGENT_DIRECTION.md` 和 `docs/ROADMAP.md` 为准。

## 目标

让内部运营人员不需要掌握提示词、product ID 或 CLI 参数，只用自然语言即可让 Hermes：

```text
理解产品与目标 → 主动补齐关键认知 → 自主规划
→ 搜索灵感 → 选择本地素材 → 生成文/图/视频
→ 交付与解释 → 从反馈形成安全学习提案
```

Hermes 是 Agent Runtime；`product_creative` 插件拥有所有业务实现。Product Brain 围绕具体产品长期进化，热点/节日/剧情只作为 task context 或 inspiration，不建立平行 Theme Brain。

## 固定产品行为

- 支持了解产品、补资料、查询认知、研究灵感、生成文/图/视频、指定素材、修改结果、继续任务、查询状态、反馈、长期记忆、审阅/回滚 Brain。
- 默认 `adaptive`：产品真实性、包装、合规、授权和费用受影响时追问 1–3 项；低风险创意细节自主决定。
- “先给我看方案”使用 `preview_first`；信息充分时直接推进。
- 外部信息只能进入 Evidence/Task Context/Inspiration/Proposal，不能自动成为产品事实。
- Canonical Product Brain 只接受字段级确认后的更新。
- 包装必须不变时优先 exact-main-image/合成路线；不能证明保真则阻断。

## 数据与状态

认知分层：Evidence Inbox、Draft Understanding、Canonical Product Brain、Task Context。字段状态：`CONFIRMED`、`INFERRED`、`UNKNOWN`、`CONFLICTED`。

Creative Task：

```text
UNDERSTANDING → NEEDS_INPUT → READY → RESEARCHING → IDEATING
→ PREPARING_ASSETS → GENERATING → DELIVERING
→ AWAITING_FEEDBACK → COMPLETED
```

失败状态：`BLOCKED_PRODUCT`、`BLOCKED_AUTHORIZATION`、`BLOCKED_PROVIDER`、`FAILED_RETRYABLE`、`FAILED_FINAL`、`CANCELLED`。

持久化契约：

- `product_creative.creative_task.v1`
- `product_creative.discovery_session.v1`
- `product_creative.product_readiness.v1`
- `product_creative.creative_task_plan.v1`

## 实施清单

### 1. 公开入口与兼容

- [x] 保留 `product_workspace_resolve` 和 `product_workflow_run`。
- [x] `product_workflow_run` 增加 `task_id`、`autonomy_mode`、`authorization_id`，旧参数兼容。
- [x] 返回 task/status/stage/questions/blocker/auth/material/idea/result descriptors。
- [x] 不修改 Hermes core，不新增第二套聊天工具。

### 2. 产品认知与追问

- [x] Evidence、Draft 和 Canonical 分层。
- [x] 任务级 Readiness 与每轮最多 3 个问题。
- [x] UNKNOWN 保留且不机械重复。
- [x] 产品身份、SKU、claim boundary 字段级 proposal + confirmation。
- [x] 交付规格作为 Task Context 重排同一 task，不写 Brain。
- [x] 纯文字不能冒充当前包装素材。
- [x] 未确认 proposal 时 Canonical 指纹不变。

### 3. 目标驱动编排

- [x] 有界 Goal Planner 仅选现有 capability registry 动作。
- [x] 复用 Command Bus、guard、workflow/event/receipt、artifact repository。
- [x] 保留原始目标，修改通过 revision 记录。
- [x] task_id 自然语言继续与 workspace 隔离。
- [x] Provider 提交使用幂等键；视频状态可在调用额度消耗后继续恢复。

### 4. 搜索、灵感和素材

- [x] 通用网页/平台来源按 task authorization 暴露给 Hermes。
- [x] “渠道是抖音”与“授权抓取抖音”严格区分。
- [x] sanitized snapshot 强制 `not_product_fact=true`。
- [x] 单源/全源失败可明确降级，记录未使用实时信息。
- [x] 复用 Material Card/Pack/Resolver，当前主图优先并记录选择。
- [ ] Live XHS/Douyin sidecar 登录、Cookie、限流和结果现场验收。

### 5. 文/图/视频纵向闭环

- [x] 文案、图片、视频和图片→视频组合共享同一自然语言 task。
- [x] 复用 content/image/video brief、payload、readiness 与 review 能力。
- [x] Mock 文/图/视频 durable 交付。
- [x] Live 图片提交与异步视频提交/轮询 runner 接入现有 gateway，默认关闭。
- [x] task authorization 控制数据源、Cookie、图片/视频次数和有效期；Brain 写回始终排除。
- [ ] 用户授权的真实图片/视频 Provider 小调用验收。
- [ ] 用户亲自确认可播放视频文件和包装保真结果。

### 6. 学习与反馈

- [x] 一次性修改只影响当前 task 并申请新授权。
- [x] 长期偏好绑定具体 feedback 形成 proposal。
- [x] 用户确认后生成新 Brain version、receipt 和 event。
- [x] Skills 不保存产品事实，Agent 不自动改正式 Skill。

### 7. Desktop

- [x] Overview 展示 Readiness/问题。
- [x] Tasks 展示原始目标、计划、阶段、阻塞、授权、素材和结果。
- [x] Review 展示 task/proposal/result。
- [x] Assets 展示 task 输入与产物。
- [x] Learning 展示反馈影响和 Brain 版本。
- [x] 新增 product/workspace scoped Creative Task 只读 API。
- [x] 不新增大型画布、时间轴或模型配置中心。

## 验收矩阵

已离线覆盖：

1. 新产品仅名称时主动追问且不编造；
2. UNKNOWN 保留；
3. 成熟产品模糊/明确任务；
4. 图片、文本、视频与组合任务；
5. 当前主图和包装门禁；
6. 搜索授权、导入与失败降级；
7. 修改上一版、长期学习、确认写回；
8. task_id 恢复与 workspace 隔离；
9. Provider 缺开关/凭据和调用上限；
10. Fake live submit → consumed authorization → status recovery；
11. 真实 Hermes `AIAgent.run_conversation` 自然语言工具选择；
12. Desktop 五视图/API 与 M0–M9 public-surface/recovery 回归。

仍需用户 Live 验收：

1. 以新产品自然对话完成一次认知补齐和字段确认；
2. 以“周十五蜂蜜露”完成一次授权研究、当前主图选择、真实视频生成、播放与反馈；
3. 按用户授权选择网页/XHS/抖音来源及一个 Provider，并设置严格调用上限；
4. 确认外部 evidence 没有污染 Canonical Brain；
5. 确认中断后可自然语言继续且不重复扣费。

## 完成判定

M10 只能在以下全部成立后标为 DONE：

- 用户无需 product ID、脚本或 CLI 参数；
- 新产品可从自然语言建立可信 Product Brain；
- 成熟产品可从一句目标形成并执行计划；
- 系统可授权搜索、选择素材并交付实际图片或视频；
- 关键未知阻断、低风险创意不过度追问；
- 外部信息不污染产品事实；
- 中断任务可恢复且 Provider 不重复提交；
- 反馈通过确认安全进入下一 Brain 版本；
- 用户亲自验收一次建脑和一次真实视频。

## 下一开发任务建议（本轮不实施）

`M10.1 Live 纵向验收与适配器硬化`：在不扩展新平台/Provider 的前提下，选择现有一个视频 Provider 和已存在的网页/sidecar adapter，完成小调用上限、测试商品、可播放结果、失败恢复和 Brain 污染检查。开始前需要用户提供/确认测试 workspace、当前包装素材、Provider、凭据、允许数据源、Cookie 范围与费用上限。

GEO 自动发帖、矩阵生产、投放指标闭环、复杂子 Agent 群、Theme Brain 和 Skill 自动改代码继续不进入 M10.1。
