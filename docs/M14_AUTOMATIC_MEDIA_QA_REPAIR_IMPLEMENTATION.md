# M14 自动媒体 QA、返修与学习质量实施说明

## 1. 当前状态

- 日期：2026-07-17
- 分支：`product-creative-rebaseline-20260716`
- HEAD：`0aa95637213f02eca2ef8f619daaf771150a7e11`
- 状态：
  `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED_LIVE_GATE_AND_USER_ACCEPTANCE_PENDING`
- 真实网络、豆包 VLM、图片/视频 Provider：本地实现阶段未调用；2026-07-17 用户已明确
  授权，但 Codex 租户策略仍拒绝外发 workspace 图片/提示词。本次没有发送或计费；已有
  真实 Provider 媒体的 `REPAIR` 复验证据见 `docs/M14_LIVE_GATE_20260717.md`
- Git：未 commit、未 push、未 tag、未 release

M14 的本地实现、离线自然语言 E2E、Desktop、分发和回归 Gate 已完成。真实 VLM/Provider
Live Gate 与用户亲自验收一条 QA PASS、一条自动返修案例仍需单独执行，不能把本地 fixture
结果描述成真实线上质量验收。

## 2. 目标和非目标

M14 把“生成了可播放文件”和“内容可以交付”拆成两个独立状态：

```text
M13 Composite Manifest
→ 技术 QA
→ 字幕/OCR QA
→ 包装保真 QA
→ 剧情结构与视觉连续性 QA
→ Media QA Report
→ PASS / REPAIR / HUMAN_REVIEW / REJECT
→ 只返修失败镜头
→ 重新合成并完整复检
→ 人工通过/警告接受/拒绝
→ Learning Evidence
```

本阶段不新增 Provider、抓取平台、数据库、公共 Hermes 工具、宿主专属 Product Creative
路由、自动发布、投流、矩阵生产或自动 Product Brain 写回。

## 3. 新增契约

`contracts/creative_artifacts.py` 新增：

- `MediaQualityCheck`
- `product_creative.media_qa_report.v1`
- `product_creative.media_repair_decision.v1`
- `product_creative.media_human_override.v1`

核心不变量：

- `PASS` 不允许包含 FAIL、UNKNOWN、hard blocker 或 failed shot。
- `REPAIR` 只允许由带 shot ID 的可修复失败组成。
- `HUMAN_REVIEW` 必须保存不确定或非自动失败原因。
- `REJECT` 必须有 critical failure 或 hard blocker。
- Repair 必须显式列出修复镜头和 preserved shots。
- Provider repair 与授权要求、预计调用次数必须一致。
- Human Override 不覆盖原 QA Report，并要求 reason、actor、confirmation 和 receipt。
- 所有专业工件拒绝额外字段并使用 SHA-256 content hash 防篡改。

M13 `MediaShotResultArtifact` 增加可选 `source_relative_path`。新结果保存原始背景源，
使字幕和 Product Plate 本地返修可以从干净源重新渲染；旧结果没有该字段时 fail closed
进入人工审阅，不对已合成视频重复叠加。

## 4. QA 实现

### 4.1 技术媒体 QA

`runtime/media_technical_qa.py` 使用本地 ffprobe/ffmpeg 检查：

- 文件存在、可读和 SHA-256。
- H.264、yuv420p、AAC、canvas、fps、时长和 faststart。
- manifest 镜头顺序与计划一致。
- 每个 shot 时长。
- 黑帧、冻结帧、静音比例和峰值削波。

该模块只读，不调用网络、LLM 或 Provider。

### 4.2 字幕和可见文字

`runtime/media_text_qa.py`：

- 校验计划 caption 与 ASS 源文件。
- 检查乱码、缺失和源文本不一致。
- 通过可替换 OCR port 检查实际可见文字、安全区和显示时长。
- 没有 OCR 或置信度不足时返回 `UNKNOWN`，不得静默 PASS。

### 4.3 包装视觉保真

`runtime/packaging_visual_qa.py`：

- 校验 Product Plate 文件 hash 和 shot input hash。
- 校验 compositor provenance 必须包含不可变 plate overlay。
- 按 M13 的确定性缩放/放置几何抽帧。
- 只比较 plate alpha 不透明像素，计算 mean absolute error。
- 严重遮挡、变形或来源不一致形成 critical failure。
- evidence frame 保存到当前产品 workspace，路径越界被拒绝。

### 4.4 剧情和连续性

`runtime/story_continuity_qa.py`：

- Production Bible、Media Plan 和 Manifest 镜头覆盖必须一致。
- 第一镜头必须承担钩子/问题，过程需要产品介入或转折，最后镜头需要结尾/收束。
- 可替换 visual adapter 检查相邻镜头人物和场景连续性。
- visual adapter 不可用或低置信度时返回 `UNKNOWN/HUMAN_REVIEW`。

## 5. 统一 QA 和修复

`runtime/media_qa.py` 聚合所有 checks，并使用确定性优先级：

```text
non-repairable critical → REJECT
all failed checks are shot-scoped and repairable → REPAIR
remaining FAIL or UNKNOWN → HUMAN_REVIEW
warnings only or all pass → PASS
```

每轮保存不可变 `MediaQaReportArtifact`。OCR/VLM adapter 只记录脱敏名称和 policy
version，不保存密钥、Cookie 或 token。

`runtime/media_repair.py`：

- 字幕失败 → `rerender_subtitle`
- 包装合成失败 → `recomposite_plate`
- 局部合成/时长问题 → `recompose_final`
- 黑帧、人物、场景、剧情视觉失败 → `regenerate_background`
- 同一 shot 多个问题按需要 Provider 的最高成本路线合并一次。
- 明确记录不受影响镜头。
- 自动返修最多两轮，第三次进入人工审阅。

## 6. Creative Task 和自然语言恢复

`runtime/media_production.py` 在生成 Composite Manifest 后立即执行 M14 QA：

- QA PASS：进入 `AWAITING_FEEDBACK`。
- QA HUMAN_REVIEW：任务保持 `READY`，内部阶段为 `QUALITY_REVIEW`。
- QA REPAIR：保存 Repair Decision；需要 Provider 且授权不足时进入
  `BLOCKED_AUTHORIZATION`。
- QA REJECT：进入 `FAILED_FINAL/QUALITY_REVIEW`。

`runtime/creative_tasks.py` 支持自然语言：

```text
“继续修复这个视频”
```

它读取最后的 Repair Decision：

- 只重新调用失败 shot。
- 已通过 shot 不重复生成。
- Provider repair 复用现有任务授权和幂等边界。
- 本地字幕/plate 修复从保留的原始 source 重新渲染。
- 修复后重新合成整条视频并执行完整 QA。
- 两轮仍失败时停止自动循环。

离线 E2E 已证明黑色 `shot-03` 首轮失败后只重做 `shot-03`，其余四个镜头调用次数
保持 1，第二轮 QA PASS 后进入 `AWAITING_FEEDBACK`。

## 7. 人工审阅、审计和学习

`runtime/media_review.py` 与 `dashboard/plugin_api.py` 增加插件内部受控决策：

- `approve`
- `accept_with_warning`
- `reject`

Desktop endpoint：

```text
POST /v1/products/{product_id}/media-qa/{qa_report_id}/decision
```

首次请求返回 confirmation ID；确认请求必须携带 reason、actor 和 confirmation ID。
执行后保存：

- `MediaHumanOverrideArtifact`
- confirmation decision
- M9 audit event
- 幂等 command receipt
- Creative Task result descriptor

人工决定不会修改原 QA Report。通过或警告接受后任务进入 `AWAITING_FEEDBACK`；拒绝后
进入 `FAILED_FINAL/QUALITY_REVIEW`。

人工决定还会形成现有 result feedback、result evaluation 和 rule candidates，作为
Production Knowledge/Learning evidence。`allow_evolve=False`，因此不会直接创建或应用
Canonical Product Brain 版本。离线 E2E 已验证用户 reject 后 Brain content hash 不变。

## 8. Desktop

插件拥有的五个视图继续复用，不新增 Hermes core 路由：

- Overview：最新自动 QA 结果、hard blockers、失败镜头和人工决定。
- Tasks：QA Report、Repair Decision、repair round 和当前 `QUALITY_REVIEW` 阶段。
- Review：逐项 check、observed evidence、失败镜头、修复建议和三种人工决定。
- Assets：Production Bible、Product Plate、shot outputs 和 final manifest。
- Learning：人工 QA 决定以及 feedback/evaluation evidence，明确 Brain writeback=false。

所有人工决定复用原确认对话框，原因不能为空。

## 9. 安全和信任边界

- 默认不配置 OCR/VLM adapter，视觉语义检查 fail closed。
- 本轮未读取或调用 `DOUBAO_API_KEY`、`SILICONFLOW_API_KEY`、`DEEPSEEK_API_KEY`。
- real provider 仍要求任务授权和 `PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1`。
- QA evidence 只能写当前产品 workspace。
- Product Plate hash、shot input hash、manifest hash 和 artifact hash 全程校验。
- 外部证据和 QA evidence 不进入 Product Brain。
- enabled Desktop plugin 仍是受信任同源插件，不是恶意插件沙箱。

## 10. 验证结果

| Gate | 结果 |
|---|---|
| M14 专项 | `25 passed` |
| M10–M14 Python 回归 | `145 passed` |
| M11/M13 定向回归 | `59 passed` |
| Desktop backend/distribution | `16 passed` |
| Desktop routes/registry/page/Product Creative | `16 passed` |
| Desktop bundle Node | `2 passed` |
| TypeScript typecheck | PASS |
| Desktop production build | PASS；Node 24.15.0，dirty/CSS/large chunk warning |
| M9 review/recovery | `25/25` |
| Public surface | `84 tools / 84 CLI`，golden hash 匹配 |
| 分发版本/hash/敏感扫描 | PASS |
| enabled user-plugin 离线安装 | PASS |
| exported distribution bundle registry | PASS |
| `git diff --check` | PASS |

当前 Desktop bundle SHA-256：

```text
1ef2752e91fd5590fa43ae1d21796cc9c267f8104d9a9c057f16141bef71e94e
```

2026-07-17 在依赖、授权和恢复边界修复后追加验证：M13 `39 passed`、M14
`30 passed`、M10–M14 与来源适配器组合 `191 passed in 210.85s`；Desktop 定向
5 文件 `17 passed`。这些是当前 worktree 的更新证据，不改写上表所记录的初次收口批次。

Node 22 仍是发布权威环境。本机 Node 24 的通过结果是补充证据，不替代 GitHub Actions。
真实执行的任务、数据披露边界、Provider 模型、调用上限、Product Brain hash 和中断恢复
步骤统一记录在 `docs/M14_LIVE_GATE_20260717.md`。

## 11. 已知限制

- 豆包 VLM/OCR adapter 尚未在本轮真实调用，默认结果会停在 HUMAN_REVIEW。
- 真实豆包/Seedance 逐镜头异步生成、下载、返修和 QA 仍是独立 Live Gate。
- 视觉连续性首版依赖结构化 adapter observation；真实模型稳定性需 Live Gate 校准。
- 音频首版检查编码、静音和峰值，不包含口播语义、唇形或音乐节拍一致性。
- 旧 M13 shot result 没有 `source_relative_path` 时无法安全本地重渲染，会进入人工审阅。
- 当前 ffmpeg/ffprobe 仍借用 AIMIXMaster 内置二进制，正式 Desktop 分发方案未完成。
- 用户尚未亲自验收一条 QA PASS 和一条自动返修案例。

## 12. 修改文件

### 契约和持久化

- `.hermes/plugins/product_creative/contracts/creative_artifacts.py`
- `.hermes/plugins/product_creative/contracts/__init__.py`
- `.hermes/plugins/product_creative/runtime/professional_artifacts.py`

### QA 和返修

- `.hermes/plugins/product_creative/runtime/media_technical_qa.py`
- `.hermes/plugins/product_creative/runtime/media_text_qa.py`
- `.hermes/plugins/product_creative/runtime/packaging_visual_qa.py`
- `.hermes/plugins/product_creative/runtime/story_continuity_qa.py`
- `.hermes/plugins/product_creative/runtime/media_qa.py`
- `.hermes/plugins/product_creative/runtime/media_repair.py`
- `.hermes/plugins/product_creative/runtime/media_review.py`

### 生产和任务接入

- `.hermes/plugins/product_creative/runtime/media_compositor.py`
- `.hermes/plugins/product_creative/runtime/media_production.py`
- `.hermes/plugins/product_creative/runtime/creative_tasks.py`

### Desktop/API

- `.hermes/plugins/product_creative/application/console_queries.py`
- `.hermes/plugins/product_creative/dashboard/plugin_api.py`
- `.hermes/plugins/product_creative/desktop_ui/index.js`
- `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`

### 测试

- `tests/hermes_cli/test_product_creative_m14_media_qa.py`
- `tests/hermes_cli/test_product_creative_m13_media_production.py`
- `tests/hermes_cli/test_product_creative_m11_artifacts.py`

### 知识

- `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`
- `AGENTS.md`
- `docs/AI_HANDOFF.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/MVP_SCOPE.md`
- `docs/ARCHITECTURE_CURRENT.md`
- `docs/DECISION_LOG.md`
- `docs/PRODUCT_AGENT_DIRECTION.md`

## 13. 丢失上下文后的恢复顺序

1. 读取 `AGENTS.md`、`AI_HANDOFF`、`PROJECT_STATE`、`MVP_SCOPE`、`ARCHITECTURE_CURRENT`。
2. 读取 M11、M12、M13 和本文。
3. 确认分支、HEAD、dirty worktree，不清理。
4. 运行 M14 专项和 M10–M14 回归。
5. 运行 Desktop UI、bundle、typecheck/build。
6. 运行 M9/public surface Gate。
7. 导出临时分发并执行隔离安装。
8. 真实 VLM/Provider Live Gate 按 `docs/M14_LIVE_GATE_20260717.md` 的最小披露授权、
   调用上限和恢复顺序执行。

建议提交时把 M11–M14 作为按里程碑可审阅的提交组；当前用户尚未授权本轮 commit。
