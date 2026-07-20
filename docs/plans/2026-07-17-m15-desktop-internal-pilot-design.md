# M15 Desktop 内部试用版设计

## 状态与范围

- 日期：2026-07-17
- 分支：`product-creative-rebaseline-20260716`
- 基线 HEAD：`0aa95637213f02eca2ef8f619daaf771150a7e11`
- Scope Gate：`IN_SCOPE`
- Redundancy Review：`EXTEND/REFACTOR_EXISTING`
- 状态：设计已由 `docs/PRODUCT_AGENT_DIRECTION.md`、M15 Roadmap 和用户“开始下一阶段开发”授权；本文件将既有方向收敛为可实现边界。
- 不提交、不推送、不发布；M14 真实 Provider/VLM 用户验收仍保持独立未完成 Gate。

## 目标

让不懂 Prompt、CLI、payload 和 task ID 的内部运营人员，在 Hermes Desktop 的 Product Creative 插件内完成：

```text
选择或创建产品
→ 补充资料与主图
→ 检查模型/媒体环境
→ 用自然语言发起创作
→ 审阅产品事实、创意方向、成片质量三个关键节点
→ 继续或恢复中断任务
→ 查看结果并反馈
```

M15 不重新实现创作编排。Product Brain、Creative Task、Business Skills、Production Bible、Provider、媒体合成、QA、Repair、Learning 和 Recovery 仍是唯一业务真源。

## 方案选择

采用“插件内工作台 + Hermes 对话执行”的渐进方案：

1. Product Creative Desktop 插件提供产品 onboarding、准备度、任务入口、三个审阅节点、素材结果、学习和设置诊断。
2. 用户输入自然语言目标后，插件调用现有 `continueInChat`，进入 Hermes 对话；不建立第二个 Agent loop。
3. 后端只新增面向 Desktop 的薄适配：安全诊断与 onboarding；所有业务写入继续复用 Command Bus/Capability。
4. Windows 打包继续复用 Hermes Desktop thin-installer。M15 首先验证插件内部试用闭环，不在同阶段重写安装器或分叉 Hermes。

没有采用的方案：

- 独立 React 创作应用：会复制任务状态、API 和认证边界。
- Desktop 页面直接执行 Goal Planner：会形成第二个聊天入口，破坏 Hermes 统一 Agent Runtime。
- 将 XHS/Douyin 设为必需设置项：与当前“按需可选灵感源”决策冲突。

## 信息架构

插件保留现有视图并增加 `Settings`：

- Overview：产品准备度、三个关键节点、自然语言任务入口、高价值下一动作。
- Tasks：任务列表、阶段、阻塞原因、授权、逐镜头进度和“自然语言继续”按钮。
- Review：按“产品事实 → 创意方向 → 成片质量”分区，保留确认原因门禁。
- Assets：输入主图、Product Plate、逐镜头输出、最终成片和历史素材。
- Learning：一次性修改、长期提案、Brain 版本、规则和回滚。
- Settings：Hermes/插件、模型凭据、真实 Provider 开关、ffmpeg/ffprobe、可选 Sidecar 状态。

无产品时不显示空白错误页，而显示 onboarding：产品名称为必填；产品 ID 可选；描述只进入 Evidence/Draft，不直接进入 Canonical Product Brain。资料和主图通过 Hermes 聊天附件补充，避免新增任意文件系统读取能力。

## 后端契约

### `GET /api/plugins/product_creative/v1/diagnostics`

只读、无外部 Provider 调用、无密钥值。返回：

- `schema_name=product_creative.desktop_diagnostics.v1`
- `overall_status=READY|ACTION_REQUIRED|DEGRADED`
- `checks[]`：`id/category/label/status/required/detail/action/metadata`
- Provider 检查只报告所需环境变量名和 `configured: true|false`。
- `DOUBAO_API_KEY` 始终是豆包图片/VLM/视频的最高优先凭据。
- ffmpeg/ffprobe 只返回是否可用与来源类型，不返回无关系统信息。
- XHS/Douyin 使用固定 loopback health URL、短超时；离线为 `OPTIONAL_OFFLINE`，不降低核心创作 readiness。

### `POST /api/plugins/product_creative/v1/products`

输入：`name`、可选 `product_id`、可选 `description`。

- 复用 `product_workspace_resolve(create_if_missing=true)` 创建唯一工作区。
- 同名现有产品不得被静默写入；返回冲突并要求用户选择。
- 描述经现有 `product_ingest` 进入 Evidence/Draft。
- 不自动确认 Product Brain 字段，不调用网络和模型。

## 三个关键审阅节点

1. 产品事实：SKU、当前包装、主图、允许/禁止表述和任务 Readiness。未知保持 `UNKNOWN`。
2. 创意方向：三个候选、选择理由、剧情、Skill provenance 和 Preflight QA。preview-first 时等待用户选择。
3. 成片质量：媒体依赖、逐镜头状态、自动 QA、返修决定和人工通过/警告接受/拒绝。

任何长期 Brain 写回、媒体 QA 人工决定、rollback、rule revoke 和 workflow retry/cancel 继续使用现有 confirmation ID + reason + receipt/event。

## 状态、恢复与隔离

- 插件不保存任务真源，仅保存当前 workspace 下的活动产品选择。
- workspace 切换后重新挂载并重新读取所有数据；不得复用上一 workspace 的产品、任务或媒体路径。
- “继续任务”由 Desktop 生成自然语言消息并携带内部 task ID，用户不需要看到或输入 ID。
- 已成功 Provider shot 继续由 durable receipt/event 去重；Desktop 刷新不触发生成。
- 诊断和 onboarding 错误必须可读，不静默跳回聊天。

## 安全边界

- 诊断不得返回 API Key、Cookie、Token 或环境变量值。
- Sidecar 健康检查只允许固定的 `127.0.0.1` 地址，不接受请求参数 URL。
- Settings 不在 M15 写系统环境变量；只提供状态与进入 Hermes 设置的动作。
- 产品创建、Evidence 摄入发生在当前 workspace；不得跨 workspace。
- 真实 Provider、Cookie 和 Product Brain 写回仍使用既有授权与确认边界。

## 验收

- 空 workspace 可从产品名称创建产品，并清楚提示下一步补充资料/主图。
- 已有产品可从预设或自由自然语言目标进入 Hermes 对话，无需 Prompt 工程。
- 用户可看到三个关键节点及明确阻塞/下一动作。
- 用户可一键继续中断任务，无需复制 task ID。
- Settings 可诊断模型凭据、真实调用开关、媒体工具和可选 Sidecar，且响应不含密钥值。
- XHS/Douyin 离线不阻断普通 Web/本地素材创作。
- workspace/locale/mount cleanup 保持隔离。
- Backend、Desktop UI、typecheck、production build、M9 public surface 和分发安装回归通过。
- Windows 安装包构建和内部人工全链验收作为 M15 最终 Gate；未实际执行不得标记完成。
