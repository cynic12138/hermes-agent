# M10 从 0 自然语言建立 Product Brain 实施计划

> 本文是 M9.1 完成后的唯一推荐开发任务。未经用户再次授权，不执行本计划中的代码修改。

## 1. 这项开发是为了什么

M9.1 解决“Product Creative 能否作为稳定插件加载、审阅和恢复”的底座问题。M10 开始解决用户真正能感知的核心问题：运营人员不需要先写 PRD、整理字段表或设计提示词，只需要自然地介绍一个产品，Hermes 就能主动发现缺口、索要证据、形成可审阅理解，并在用户确认后逐步建立 Product Brain。

本阶段只跑通以下最小闭环：

```text
自然语言提出产品与创作目标
-> 解析或建议创建产品工作区
-> 判断完成当前任务还缺什么
-> 每轮追问 1–3 个问题
-> 保存 evidence/draft，UNKNOWN 保持未知
-> 形成字段级 proposal
-> 用户确认后写入 Canonical Product Brain
-> 判断是否满足真实图片/视频生成前置条件
```

完成 M10 后，系统应“更会了解产品”，但本阶段不新增抓取平台、不新增 provider，也不执行真实付费生成。

## 2. 范围与固定决策

### IN_SCOPE

- `product_workflow_run` 继续作为唯一自然语言业务入口。
- 用户只说产品名称、少量素材或创作目标时，可以开始 discovery。
- 每轮只问 1–3 个信息增益最高的问题。
- Evidence Inbox、Draft Understanding、Canonical Product Brain 三层隔离。
- 用户说“不知道/不确定”时记录 `UNKNOWN`，不虚构答案。
- 字段级 proposal、确认、拒绝、修正和审计。
- 图片/视频生成前的最小知识与包装保真 readiness gate。
- 真实自由对话 E2E，使用临时 workspace 和 mock/offline provider。

### OUT_OF_SCOPE

- 自动抓取小红书、抖音、官方店铺或普通网页。
- 把外部搜索结果自动写入 Product Brain。
- 新 image/video/VLM provider、真实付费调用或生产 API。
- Desktop 新建脑向导；M10 仍以 Hermes chat 为入口，Desktop 只审阅/恢复。
- 矩阵生产、自动投放、效果归因、多人/云/计费。
- 数据库 schema 重构、向量库、消息队列和无关宿主重构。

## 3. 复用与数据边界

不新建第二套 agent 或 workflow engine。复用：

- `product_workspace_resolve`：按名称/别名解析已有产品。
- `product_create`：用户明确同意后创建最小空白产品。
- `product_workflow_run`：自然语言入口和安全 workflow 执行。
- `brain/wiki.py`：Canonical Product Brain 页面。
- `brain/provenance.py`、现有素材/source index：Evidence Inbox。
- `product_ingest`：把用户文字和资料登记为 evidence，而不是直接当正式事实。
- 现有 learning proposal、`product_proposal_decide` 和 confirmation gate：字段写回。
- Command Bus、SQLite event/receipt 和 recovery：审计与恢复。

新增的 Draft Understanding 只保存到产品工作区 `structured/discovery_session.json`。它保存当前目标、待确认回答、UNKNOWN 和问题队列，不复制整份 Canonical Wiki。正式事实仍以 Wiki 为真源，执行/审计状态仍以 SQLite 为真源。

## 4. 对外行为契约

### 4.1 `product_workflow_run`

保持现有参数兼容；继续接受 `product_id/product_query/create_if_missing/message/...`。返回值新增可选 `discovery`：

```json
{
  "stage": "EMPTY|DISCOVERING|AWAITING_CONFIRMATION|READY_FOR_TASK",
  "current_goal": {
    "output_type": "image|video|understanding",
    "channel": "",
    "request": "用户原始目标"
  },
  "confirmed_facts": [],
  "draft_understanding": [],
  "conflicts": [],
  "unknowns": [],
  "questions": [],
  "proposal_ids": [],
  "generation_readiness": {
    "ready": false,
    "missing": [],
    "blocked_reasons": []
  }
}
```

旧调用方不读取 `discovery` 时行为不变。discovery 计算和提问本身不调用 provider、不写 Canonical Brain。

### 4.2 字段状态

每个候选字段只能处于：

- `CONFIRMED`：用户确认且已在 Canonical Product Brain 中有来源记录。
- `INFERRED`：模型或多项 evidence 推断，只能留在 draft/proposal。
- `UNKNOWN`：用户明确不知道或证据不足。
- `CONFLICTED`：不同 evidence 或用户陈述冲突，必须追问。

允许进入 Canonical 的唯一通路是现有 proposal + explicit confirmation。网页、社交内容和模型推断不能绕过此通路。

### 4.3 最小生成 readiness

准备真实图片或视频任务前，至少确认：

- 产品和具体 SKU 可识别。
- 当前包装/商品主体素材已经确认。
- 包装中不可改变的视觉元素已经确认。
- 与本次任务有关的可用和禁用表述已经确认。
- 输出类型、用途和规格已经确认。

任一关键项缺失时，Hermes 可以继续了解产品或生成不涉及产品主体的创意草案，但不能声称可以包装保真地生成真实商品图/视频。

## 5. 实施任务

### Task 1：Discovery 领域模型和派生快照

**主要文件**：新增 `brain/discovery.py`；扩展 workspace repository；新增 M10 verification fixture。

- [ ] 为 discovery session、field candidate、question 和 readiness 定义稳定 schema/version。
- [ ] 从 Wiki、source index、draft session 和 pending proposal 派生四类字段状态。
- [ ] 使用原子写入保存 `structured/discovery_session.json`，拒绝跨产品路径。
- [ ] 编写行为测试：空产品、已有事实、UNKNOWN、冲突和跨 workspace 隔离。

验收：同一份 Canonical Wiki 不被 discovery 读取过程修改；删除 draft session 后可从 Wiki/evidence 安全重建基础快照。

### Task 2：按任务目标计算知识缺口和问题优先级

**主要文件**：扩展 `runtime/state.py`、`runtime/planning.py`；复用 capability registry。

- [ ] 将目标归一为 `understanding/image/video`，渠道只作为次级上下文。
- [ ] 基于目标计算关键字段；每轮最多返回 3 个问题。
- [ ] 排序固定为：安全/合规阻塞 > 产品/SKU 身份 > 当前包装保真 > 当前交付规格 > 可延后偏好。
- [ ] 已有 evidence 能回答的问题不重复询问；冲突问题优先于普通 UNKNOWN。

验收：相同状态和目标产生稳定问题顺序；用户说“不确定”后不会在下一轮重复强迫回答同一非关键问题。

### Task 3：把 discovery 接入现有自然语言入口

**主要文件**：扩展 `runtime/conversation.py`、`runtime/execution.py`、product capability schema/handler 和 operator Skill。

- [ ] 未找到产品时返回创建建议，不自动发明 product ID 或创建 workspace。
- [ ] 用户明确同意后复用 `product_create` 创建 `EMPTY/DRAFT` 产品。
- [ ] `product_workflow_run` 在产品知识不足时进入 discovery，不错误跳到内容生成。
- [ ] `agent_reply` 固定展示：已确认事实、合理推断、冲突、未知、影响和下一批问题。
- [ ] 保持原有 generation/review/recovery workflow 兼容。

验收：用户只输入“我有一个周十五蜂蜜露产品，想先让你了解它，以后持续帮我做图片和视频”，系统会建议创建/解析产品并开始追问，不把“蜂蜜露”猜成饮品。

### Task 4：用户回答、evidence 和字段级 proposal

**主要文件**：扩展 `product_ingest` 编排、现有 learning proposal service 和 discovery session repository。

- [ ] 用户回答先作为带来源的 evidence/draft 保存。
- [ ] “不确定”生成 UNKNOWN，不产生猜测值。
- [ ] 单轮回答可映射多个字段，但每个字段保留独立 source、status 和影响说明。
- [ ] 候选事实通过现有 learning proposal 格式提交；高影响字段逐项或小批次确认。
- [ ] 拒绝/修正保留审计，不污染 Canonical Wiki。

验收：未确认 proposal 前 Wiki 内容和 canonical fingerprint 不变；确认后产生新 Wiki 版本、receipt/event 和可恢复记录。

### Task 5：生成前置门禁

**主要文件**：扩展 `runtime/guard.py`、provider readiness 和 workflow planning。

- [ ] image/video action 在执行前读取 discovery readiness。
- [ ] 缺少包装、SKU 或表述边界时返回可理解的阻断原因和下一问题。
- [ ] 外部 inspiration 只能补充 evidence/proposal，不能自动解除 readiness 阻断。
- [ ] 保持 mock brief、无商品主体的背景/剧情草案与真实商品生成边界清晰。

验收：没有当前包装素材时，系统不会声称能保持包装不变；补齐并确认关键字段后，原有生成 workflow 可以继续。

### Task 6：真实自然语言 E2E

**主要文件**：新增 `scripts/verify_m10_zero_to_product_brain.ps1` 和对应 fixture；更新 conversation protocol。

- [ ] 使用临时 HOME/workspace，不预先创建产品，不预写周十五产品事实。
- [ ] 连续输入自然语言：提出产品目标、同意创建、提供部分信息、回答“不确定”、补充包装 evidence、确认一个字段 proposal。
- [ ] 断言每轮通过 `product_workspace_resolve/product_workflow_run`，而不是要求用户运行脚本命令。
- [ ] 断言 UNKNOWN、冲突、proposal、confirmation、Wiki 版本和 recovery event。
- [ ] 断言全程没有真实 provider、网络抓取、消息发送或费用。

验收：这条 E2E 是 M10 的主验收，不得只用预填参数直接调用底层函数替代真实多轮自然语言输入。

### Task 7：兼容、文档和交接

- [ ] 运行 M0–M9 public-surface、conversation、learning、recovery 和 M9.1 Desktop 回归。
- [ ] 更新 `PROJECT_STATE`、`ROADMAP`、`AI_HANDOFF`、`ARCHITECTURE_CURRENT` 和 conversation protocol。
- [ ] 在 Desktop Review 中确认 M10 proposal/recovery 可见；不增加 Desktop 启动向导。
- [ ] 输出迁移说明：已有产品无 discovery session 时按需派生，不批量重写 workspace。

## 6. 测试矩阵

必须覆盖：

- 新产品不存在、同名/别名多匹配、用户拒绝创建。
- 空产品、部分事实、已成熟 Product Brain。
- 用户一次回答一个字段、多个字段和“不确定”。
- evidence 冲突、模型推断、官方资料和社交灵感来源边界。
- 未确认 proposal 不写 durable canonical state；确认/拒绝/修正均有审计。
- workspace 切换和两个同名产品不串库。
- image/video readiness 阻断与解除。
- 自由中文表达、短句、纠正前文和多轮上下文。
- 旧 `product_workflow_run` generation/review 调用兼容。
- 全程 credential scrub，禁止 live provider 和网络。

## 7. 完成条件

M10 只有在以下条件全部满足时才能标记 DONE：

1. 用户可从一句自然语言开始，不需要提供 product ID 或脚本参数。
2. 系统每轮主动问 1–3 个高价值问题，并正确保存 UNKNOWN。
3. Evidence/Draft/Canonical 三层在代码、存储和回复中都可区分。
4. 未确认内容绝不进入 Canonical Product Brain。
5. 图片/视频 readiness 能阻止包装和表述证据不足的真实生成。
6. 周十五蜂蜜露自由对话 E2E、既有回归和隔离审计全部通过。
7. 用户亲自审阅实际对话记录后确认体验可以进入下一轮优化。

## 8. 开发前仍需用户确认

计划已锁定技术边界，但开始编码前需要用户确认两项产品偏好：

1. 第一版允许 Hermes 在用户同意创建产品后直接进入连续追问；默认采用该方案，不增加表单向导。
2. 字段 proposal 默认每批最多 3 项，产品定位、核心卖点、包装规则和合规表述始终逐项确认。

若用户没有修改，实施时采用以上默认值。
