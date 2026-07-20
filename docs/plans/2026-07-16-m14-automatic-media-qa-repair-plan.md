# M14 Automatic Media QA, Repair, and Learning Quality Plan

## 1. 状态

- 日期：2026-07-17
- 基线：M13 `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED_LIVE_GATE_PENDING`
- 状态：
  `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED_LIVE_GATE_AND_USER_ACCEPTANCE_PENDING`
- 源码策略：继续采用方案 1，Product Creative 留在 Hermes 内层插件；稳定后拆分。
- 本地实现和离线 Gate 已完成；真实 VLM/Provider Live Gate 与用户亲自验收仍待执行。
- 实施和恢复证据见 `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`。

## 2. 目标

让“生成了文件”与“可以交付”彻底分离：

```text
M13 Composite Manifest
→ 技术质量检查
→ 包装/OCR/视觉保真检查
→ 人物、场景、剧情与字幕连续性检查
→ QA Report
→ PASS / REPAIR / HUMAN_REVIEW / REJECT
→ 只返修失败镜头
→ 重新合成并再次 QA
→ 用户通过/修改/拒绝
→ Learning Proposal
```

M14 完成后，明显乱码、包装错误、空洞模板、黑帧、音轨缺失或剧情断裂不能被自动
标记为可发布。

## 3. 范围

### IN_SCOPE

- 图片/视频技术质量、包装、文字、字幕、连续性和剧情一致性 QA。
- 版本化 QA Report、Repair Decision 和 Human Override。
- 镜头级返修、重合成、再次 QA 和最大返修次数。
- 用户通过/修改/拒绝原因的结构化记录与 learning proposal。
- Desktop Review/Tasks/Assets/Learning 投影。
- 离线 fixture、可选 VLM adapter 和用户授权 Live 验收。

### OUT_OF_SCOPE

- 自动发布、自动投流、播放数据抓取和投放效果分析。
- 批量矩阵生产和 Mother Creative 变体队列。
- 完整时间线编辑器。
- 新 Provider、向量库、消息队列或平行 QA 数据库。
- 自动修改 Product Brain 或正式 Skill。

## 4. 架构决策

- 复用 M13 Media Execution Plan、Shot Results 和 Composite Manifest。
- 复用现有 artifact repository、Creative Task、Command Bus、confirmation、receipt、
  learning proposal 和 Desktop Plugin SDK。
- 确定性检查优先；VLM 只补充语义/视觉判断，不能覆盖硬失败。
- 包装保真以当前确认主图/Product Plate 为视觉基线。
- 返修单元是 shot，不是整条视频。
- 每轮 QA 和 Repair 都产生不可变工件，不覆盖旧结果。
- 最大自动返修轮数默认 2；超过后进入人工审阅，不无限循环。
- VLM/Provider 调用必须使用当前 task authorization；Brain 写回仍需独立确认。

## 5. 新增契约

### `product_creative.media_qa_report.v1`

- `plan_id`
- `manifest_id`
- `qa_run`
- `overall_result`: `PASS | REPAIR | HUMAN_REVIEW | REJECT`
- `checks`
- `failed_shot_ids`
- `hard_blockers`
- `warnings`
- `evidence_refs`
- `model_provenance`

### `MediaQualityCheck`

- `check_id`
- `category`
- `scope`: final/shot/frame/audio/subtitle/packaging
- `status`: PASS/WARN/FAIL/UNKNOWN
- `severity`: low/medium/high/critical
- `shot_id`
- `time_range`
- `expected`
- `observed`
- `evidence`
- `repairable`

### `product_creative.media_repair_decision.v1`

- `qa_report_id`
- `decision`
- `repair_round`
- `shot_repairs`
- `preserved_shot_ids`
- `estimated_provider_calls`
- `authorization_required`
- `reason`

### `product_creative.media_human_override.v1`

- `qa_report_id`
- `decision`: approve/reject/accept_with_warning
- `reason`
- `actor`
- `confirmation_id`
- `receipt_id`

## 6. 实施节点

### Node 1：QA 工件和状态契约

文件：

- Modify `contracts/creative_artifacts.py`
- Modify `contracts/__init__.py`
- Modify `runtime/professional_artifacts.py`
- Add `tests/hermes_cli/test_product_creative_m14_media_qa.py`

完成：

- 注册 QA Report、Quality Check、Repair Decision、Human Override。
- 验证 hash、extra field、workspace、状态组合和不可变来源。
- `PASS` 不允许存在 critical failure；`REPAIR` 必须有可修复 failed shot。

### Node 2：技术媒体检查器

新增 `runtime/media_technical_qa.py`：

- ffprobe 文件可读性。
- H.264/yuv420p/AAC、canvas、fps、时长、faststart。
- 黑帧、冻结帧、空音轨、峰值削波和静音比例。
- Shot 时长与 plan 容差。
- 最终镜头顺序与 manifest 一致。

输出确定性 checks，不调用网络或模型。

### Node 3：字幕和可读文字检查

新增 `runtime/media_text_qa.py`：

- 读取 ASS 源字幕和计划 caption。
- OCR 抽帧验证实际可见字幕。
- 检查乱码、缺字、错字、截断、安全区、对比度和显示时长。
- 品牌/包装文字与字幕分开判定。
- OCR 不确定时标记 `UNKNOWN/HUMAN_REVIEW`，不得自动 PASS。

首版 OCR adapter 使用可替换 port；没有可靠 OCR 时 fail closed，不引入静默伪结果。

### Node 4：包装视觉保真

新增 `runtime/packaging_visual_qa.py`：

- 从 Product Plate 生成基线特征和关键区域。
- 在产品出现镜头抽取代表帧。
- 比较轮廓、主色、长宽比、logo/关键文字区域和局部感知差异。
- 产品不存在、遮挡过大、严重变形、关键字乱码或比例异常为 hard failure。
- full-rect plate 只检查完整矩形保真；不假装拥有透明轮廓质量。
- 可选豆包 VLM 提供解释性判断，但不得覆盖确定性 hard failure。

### Node 5：人物、场景和剧情连续性

新增 `runtime/story_continuity_qa.py`：

- 逐镜头核对 Bible narrative function、角色、场景、产品出现时点和结尾。
- 检查人物身份/服装/物件突变、空间跳变、镜头缺失和剧情推进中断。
- 检查“剧情视频”是否真实具有钩子、推进和结尾。
- 结构规则先执行，VLM 负责视觉连续性补充。
- VLM 不可用时视觉语义项为 UNKNOWN，不能自动变成 PASS。

### Node 6：统一 QA Orchestrator

新增 `runtime/media_qa.py`：

```python
run_media_qa(task, manifest_id, *, mode) -> MediaQaReportArtifact
```

- 聚合技术、字幕、包装和连续性 checks。
- 确定性优先级：
  critical hard fail > high fail > repairable fail > unknown > warning > pass。
- 保存抽帧、OCR、probe 和 VLM evidence refs。
- 相同 manifest hash + QA policy version 形成稳定幂等键。

### Node 7：Repair Planner

新增 `runtime/media_repair.py`：

- 把失败 check 映射到 shot。
- 决定重新生成背景、重新渲染字幕、重新放置 plate 或只重新合成。
- `preserved_shot_ids` 必须显式记录。
- 包装/字幕本地问题优先本地返修，不消耗 Provider。
- 场景/人物生成问题才申请 Provider 调用。
- 预计调用超过授权余量时进入 `BLOCKED_AUTHORIZATION`。
- 最大自动返修 2 轮；之后 `HUMAN_REVIEW`。

### Node 8：Creative Task 集成

修改 `runtime/creative_tasks.py`：

- M13 完成后不直接视为交付完成，先进入 `QUALITY_REVIEW` 内部阶段。
- QA PASS 才进入 `AWAITING_FEEDBACK`。
- QA REPAIR 自动生成 Repair Decision；安全本地修复可直接执行。
- 需要真实 Provider 时返回新的/续用任务授权边界。
- 用户说“继续修复这个视频”从最后 Repair Decision 恢复。
- 不重复已通过 shot，不重复已付费幂等提交。

保持现有 Creative Task 公共 schema 兼容；细粒度状态放入专业工件和 summary。

### Node 9：人工审阅与豁免

通过现有 Command Bus 增加受控内部 command：

- approve media QA
- reject media QA
- accept with warning

所有决定要求原因、confirmation ID、receipt 和 event。人工豁免不修改原 QA Report。

是否新增公开 tool 必须再次运行 redundancy review；默认通过现有 review command/API
扩展，不扩大 84-tool 公共面。

### Node 10：Learning 接入

扩展现有 `result_evaluation_service.py`：

- 用户通过：成功模式候选。
- 用户修改：记录目标差异和失败类别。
- 用户拒绝：记录明确反模式。
- QA 自动失败：只进入 Production Knowledge evidence，不自动形成长期偏好。
- 多次相同失败可形成 Skill change proposal，但不得自动改 Skill。
- Canonical Product Brain 指纹在 proposal 确认前保持不变。

### Node 11：Desktop UX

现有插件页面扩展：

- Overview：最新 QA 结果、hard blockers、需要人工判断的 UNKNOWN。
- Tasks：QA/Repair 轮次、失败镜头和授权状态。
- Review：逐项检查、证据帧、预期/观察、修复建议和人工决定。
- Assets：原镜头、返修镜头、最终合成对比。
- Learning：用户判定如何进入 proposal。

不新增 Hermes core Product Creative 路由，不建设时间线编辑器。

### Node 12：离线 E2E

至少覆盖：

1. 正常本地视频 QA PASS。
2. 包装区域被修改 → critical fail。
3. 中文字幕乱码/截断 → repair。
4. 一个黑帧镜头 → 只重做该 shot。
5. 人物连续性不确定 → HUMAN_REVIEW。
6. 修复后重新 QA PASS。
7. “继续修复这个视频”重启恢复。
8. 两轮失败后停止自动循环。
9. 用户 reject 产生学习 proposal，Brain 不变。
10. workspace A/B 完全隔离。

主验收必须通过真实 Hermes 自然语言入口，不以直接 Python 函数调用替代。

### Node 13：Live Gate

用户单独授权后：

- 使用现有豆包 VLM 检查少量代表帧。
- 如果 M13 Live 媒体可用，完成一次真实 QA。
- 最大 VLM/图片/视频真实返回仍各按任务授权限制，默认不超过 5。
- 保存请求摘要、Provider task、耗时、receipt 和脱敏结果。
- 不输出 API key，不把 QA evidence 写入 Product Brain。

### Node 14：全量 Gate 与知识沉淀

- M10–M14 Python 回归。
- M9 review/recovery 和 public surface golden。
- Desktop UI/bundle/typecheck/build。
- 分发扫描和 enabled user-plugin 离线安装。
- `git diff --check`、版本、hash、文档引用和敏感扫描。
- 新增 `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`。
- 更新 AGENTS、AI_HANDOFF、PROJECT_STATE、ROADMAP、MVP_SCOPE、ARCHITECTURE、
  DECISION_LOG 和 PRODUCT_AGENT_DIRECTION。

## 7. 验收条件

M14 只有在以下全部成立时标记 DONE：

- 可播放文件不会自动等于可发布。
- 包装/文字 critical failure 必须阻断。
- 单镜头问题只返修对应镜头。
- 修复后重新执行完整 QA。
- UNKNOWN 不被模型自动补成 PASS。
- 用户可以从自然语言继续中断的 QA/Repair。
- 通过/修改/拒绝有结构化原因和审计。
- learning proposal 未确认时 Brain 不变。
- 离线 E2E、Desktop、分发和回归全部通过。
- 用户亲自验收至少一条 QA PASS 和一条自动返修案例。

## 8. 建议执行顺序

1. Node 1–2：契约和技术 QA。
2. Node 3–4：字幕和包装硬 Gate。
3. Node 5–6：连续性和统一报告。
4. Node 7–8：返修与任务恢复。
5. Node 9–11：人工审阅、学习和 Desktop。
6. Node 12：自然语言离线 E2E。
7. Node 13：单独授权 Live Gate。
8. Node 14：全量收口。

每个节点使用 RED → GREEN → regression；未经用户明确授权不 commit、push、tag、
release 或调用真实 Provider。
