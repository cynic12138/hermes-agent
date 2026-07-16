# M5 Video Generation Execution Architecture

状态：M5.1-M5.8 已落地，真实视频任务提交与结果回收已验证  
创建日期：2026-07-08  
落地日期：2026-07-08  
适用范围：`product_creative` 插件 M5 大版本开发  

本文档用于固定 M5 的开发方向。后续 M5.x 维护和 M6 入口判断都应对齐本文档。

本次 M5 落地范围：

```text
M5.1 Video Execution Readiness Audit：已落地
M5.2 Video Reference Access Gate：已落地
M5.3 Video Provider Payload Hardening：已落地
M5.4 Video Execution Policy / Approval：已落地
M5.5 Submit Live Video Task：已落地并完成 1 次真实豆包任务提交
M5.6 Task Status / Result Retrieval：已落地，支持 provider 查询与手动结果 URL 导入
M5.7 Video Result Feedback to Proposal：已落地
M5.8 Hermes Chat End-to-End Validation：已通过 workflow-run 自然语言入口验证
```

真实验证记录：

```text
provider: volcengine-ark-video / doubao-seedance-2-0-mini-260615
remote_task_id: cgt-20260708122312-r7lnb
video_task_id: video-task-20260708-122312
status_check: video-task-status-20260708-122720
final_status_check: video-task-status-20260708-123341
manual_result_import: video-result-20260708-122340
live_result: video-result-20260708-123335
local_video: artifacts/generated_videos/video-result-20260708-123335.mp4
feedback: result-feedback-20260708-122355
proposal: proposal-20260708-122357
```

说明：

```text
1. `video-result-20260708-122340` 是为了验证结果导入路径而使用的手动公开视频 URL，不冒充 `remote_task_id` 的真实完成结果。
2. 豆包视频生成是异步任务，提交后出现 `running / processing` 属于正常等待态，不代表失败。
3. 后续查询 `video-task-status-20260708-123341` 后，真实任务 `cgt-20260708122312-r7lnb` 已返回 `succeeded / completed`。
4. 真实任务结果已登记为 `video-result-20260708-123335`，并在 M5 closeout 中归档到本地 mp4。
```

---

## 1. M5 的核心判断

M5 不是“重新设计视频脚本系统”，也不是“做一个视频剪辑平台”。

M5 的职责是：

```text
把 M2 已经形成的视频 intent / storyboard brief / provider payload，
在 M4.9 已跑通的 Hermes 对话入口下，
转成真实可执行的视频生成任务，并把结果回收到产品自迭代闭环。
```

一句话：

```text
M5 的目标是让用户通过 Hermes 对话，从当前产品理解和素材库出发，生成一个真实视频交付物，并把结果反馈反哺 Product Brain。
```

M5 的质量杠杆仍然是：

```text
Product Brain
M3 Material Pack
主图/素材理解
视频分镜 brief
provider prompt
用户对结果和脚本的反馈
```

外部视频模型只是执行层，不能代替产品理解。

---

## 2. M5 与最终产品目标的关系

最终产品目标仍然是：

```text
围绕单一产品 / 单一主题持续理解、生成内容、接收反馈，并让下一次文案 / 图片 / 视频更贴合该产品。
```

M5 对这个目标的贡献：

```text
Product Brain 提供产品事实、卖点、禁用表达和历史学习。
M3 Material Pack 提供当前可用主图、参考图、素材理解和使用偏好。
M2 Video Brief 提供分镜、镜头、字幕、音频、provider prompt。
M5 Execution Approval 控制真实视频模型调用的成本和风险。
Video Task Record 保存外部任务请求、状态、远端 task id 和失败原因。
Generated Video Result 保存可交付视频 URL / 本地缓存 / 元数据。
Video Result Feedback 记录用户对视频成片、分镜、产品识别、节奏的选择和评价。
Evolution Proposal 把确认后的成功/失败经验反哺 Product Brain 和 video pattern playbook。
```

这条链路让视频生成不再是一次性输出，而是：

```text
视频 brief -> provider payload -> 真实视频任务 -> 视频结果 -> 用户反馈
  -> Product Brain proposal -> 下一次分镜和 prompt 更贴合产品
```

---

## 3. M5 的入口条件

M5 只有在 M4.9 完成后才允许开始。

已满足的入口条件：

```text
Hermes chat 能加载 product_creative 插件。
Hermes 能调用 product_workspace_resolve / product_workflow_run。
workflow-run 能读取 Product Brain、素材库和 workflow 状态。
Product Brain 写入前会停下等待确认。
真实外部 provider 调用前会停下等待确认。
M2 已有视频 intent、video brief、review、revise、provider payload。
M3 已有素材卡片和 task material pack。
M4 已有图片生成、结果回收、反馈和素材库闭环。
```

M5 不能回退到脚本主入口。脚本仍然只用于：

```text
诊断
回归测试
开发期兜底
失败定位
```

---

## 4. M5 范围

### 4.1 M5 必须做

```text
通过 Hermes 对话启动视频生成链路。
从 Product Brain + M3 素材库创建或复用 video intent。
复用 M2 video brief review / revise / confirm。
加固 confirmed video brief -> provider payload。
检查参考素材是否具备 provider-accessible remote_url。
创建真实视频执行 approval / execution policy。
调用默认视频 provider 提交真实任务。
保存 video task record，包括 remote_task_id、request、provider response、状态。
支持最小 task status / result retrieval 或 result import。
生成 normalized video result artifact。
把结果作为交付物展示给用户。
记录用户对视频结果或视频 brief 的反馈。
把可学习反馈生成 Product Brain proposal。
Hermes chat 验证整条链路。
```

### 4.2 M5 可以做，但必须保持轻量

```text
best-effort 下载视频文件到本地 generated_videos 目录。
如果 provider 只返回远端 URL，则先保存 URL 和元数据。
支持一次 live 验证调用，默认 1-2 次，最多按用户确认上限执行。
支持用户手动粘贴 provider result URL 作为兜底导入。
```

### 4.3 M5 不做

```text
不做复杂视频编辑器。
不做自动剪辑时间线 UI。
不做生成后视频多模态 QA 作为默认主线。
不做平台发布。
不做热点搜索和趋势灵感系统。
不做素材托管/CDN服务。
不做跨产品素材检索。
不自动把视频结果当成成功经验。
不自动写入 Product Brain。
```

说明：

```text
M2 中“视频任务轮询、结果导入、下载”不是主线，是因为当时 M2 的主线是视频脚本和 prompt。
到了 M5，真实视频交付成为目标，因此最小 task status / result retrieval 和 generated video artifact 成为 M5 必要执行能力。
但 M5 只做交付闭环，不扩展成视频后处理系统。
```

---

## 5. 目标用户体验

### 5.1 用户只说“生成今日视频”

用户在 Hermes 中说：

```text
帮周十五蜂蜜露生成今天的抖音视频。
```

Hermes 应执行：

```text
1. product_workspace_resolve 定位产品。
2. product_workflow_run 读取 Product Brain 和素材库。
3. 如果已有可用素材，生成 video intent。
4. 生成 video brief。
5. 生成 video brief review package。
6. 停下让用户确认或修改分镜。
7. 用户确认后，生成 provider payload。
8. 检查 live readiness。
9. 真实调用视频 provider 前再次请求用户确认。
10. 提交视频任务并保存 video task record。
11. 查询或导入结果。
12. 输出视频 URL / 本地文件 / review summary。
13. 用户反馈。
14. 生成 Product Brain proposal，等待用户确认 apply。
```

### 5.2 用户上传一张主图并要求图生视频

用户说：

```text
用这张主图为基础生成一个抖音视频。
```

Hermes 应执行：

```text
1. 注册本地主图为 material asset。
2. 默认使用 mock-vision 分析；如需真实 VLM，必须确认。
3. visual-align 生成可审阅视觉对齐。
4. rebuild material cards。
5. prepare task material pack。
6. 生成 video intent / video brief / review。
7. 进入 M5 视频执行 approval / provider payload / live task。
```

关键边界：

```text
本地图片是 canonical material。
provider 需要访问图片时，必须使用已绑定 remote_url 或用户提供的可访问 URL。
M5 不默认上传本地图片到外部托管。
```

### 5.3 用户已有确认过的视频分镜

用户说：

```text
这个分镜我确认了，可以生成真实视频。
```

Hermes 应执行：

```text
1. 确认 latest video brief 状态是 confirmed_for_provider_payload。
2. build video provider payload。
3. live readiness。
4. 若 remote_url、API key、model、endpoint 均就绪，则请求外部调用确认。
5. 提交任务并保存 task record。
6. 等待或查询结果。
```

---

## 6. M5 目标架构

```text
User Message
  -> Hermes product_workspace_resolve
  -> product_workflow_run
  -> Product Brain read
  -> M3 Material Pack read
  -> Video Intent
  -> Video Brief Draft
  -> Video Brief Review Package
  -> Human confirm / revise
  -> Provider Payload
  -> Reference URL Readiness
  -> Live Readiness
  -> Human execution approval
  -> Submit Video Task
  -> Video Task Record
  -> Task Status / Result Retrieval
  -> Generated Video Result Artifact
  -> User feedback
  -> Evolution Proposal
  -> Human apply
  -> Product Brain learning update
```

Hermes 在 M5 中的角色：

```text
读取产品认知，而不是凭空写视频 prompt。
读取素材卡片，而不是要求用户每次手动指定素材。
把分镜方案交给用户确认，而不是直接生成视频。
在真实外部调用前停住。
保存任务记录和结果，便于审计和复盘。
把用户反馈转成 proposal，而不是自动学习。
```

---

## 7. Provider 接入策略

M5 默认 live provider：

```text
volcengine-ark-video
```

当前 provider registry 已有：

```text
name: volcengine-ark-video
adapter: async-video-task
endpoint: https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks
auth_env: PRODUCT_CREATIVE_ARK_API_KEY
model: doubao-seedance-2-0-mini-260615
request_defaults:
  generate_audio: true
  ratio: 9:16
  duration: 10
  watermark: false
```

M5 不把 provider 写死到业务层。provider contract 继续是：

```text
confirmed video brief
  -> provider payload
  -> readiness
  -> execution approval
  -> task submit
  -> task status/result normalization
```

M5 需要补齐：

```text
视频 task status / result endpoint 配置。
任务查询返回结构 normalization。
result URL / local file 保存。
失败原因 normalization。
```

待确认：

```text
豆包视频任务查询/结果获取的 curl 示例或官方 endpoint。
若 provider 支持直接返回最终视频 URL，则 M5 可不做轮询，只做结果导入。
若 provider 是异步任务，则 M5 需要最小 status check。
```

---

## 8. 参考素材访问策略

M5 必须继续坚持：

```text
本地素材文件是 canonical asset。
remote_url 只是给外部 provider 访问的执行句柄。
```

原因：

```text
用户上传的图片应在本地素材库有注册信息。
Product Brain 和 Material Card 不能依赖外部 URL 作为唯一来源。
外部 URL 可能过期、失效或不可审计。
```

M5 不默认实现素材托管服务。

M5 只要求：

```text
如果调用图生视频 provider，素材必须已经绑定 provider-accessible remote_url。
如果没有 remote_url，workflow 停下，提示用户绑定 URL 或先使用纯文生视频 brief。
```

后续可在 M6/M8 或单独 provider 阶段增加：

```text
本地素材上传到对象存储。
自动生成临时 signed URL。
素材 URL 生命周期管理。
```

---

## 9. M5 数据与文件结构

继续沿用：

```text
.hermes/product_creative/products/<product-id>/
```

M5 新增或强化 artifact：

```text
artifacts/video_execution_policies/<policy-id>.json
artifacts/video_execution_policies/<policy-id>.md

artifacts/video_tasks/<video-task-id>.json
artifacts/video_tasks/<video-task-id>.md

artifacts/video_task_status/<status-id>.json
artifacts/video_task_status/<status-id>.md

artifacts/generated_videos/<video-result-id>.json
artifacts/generated_videos/<video-file>.mp4
artifacts/generated_videos/<video-result-id>.md

artifacts/result_feedback/<feedback-id>.json
```

结构化索引：

```text
structured/video_execution_policy_index.jsonl
structured/video_task_index.jsonl
structured/video_task_status_index.jsonl
structured/generated_video_index.jsonl
structured/result_feedback.jsonl
```

已有 artifact 继续复用：

```text
artifacts/video_intents/
artifacts/video_scripts/
artifacts/review_packages/
artifacts/video_brief_patches/
artifacts/provider_payloads/
artifacts/live_readiness/
artifacts/generation_jobs/
structured/evolution_proposals/
```

---

## 10. M5 Workflow Actions

M5 推荐新增或强化以下 workflow actions：

```text
resolve_video_intent
create_video_brief
review_video_brief
revise_video_brief
build_video_provider_payload
check_video_reference_readiness
check_video_live_readiness
create_video_execution_policy
submit_video_generation_task
check_video_task_status
import_video_result
record_video_result_feedback
create_evolution_proposal
apply_evolution_proposal
```

其中可自动执行的安全步骤：

```text
resolve_video_intent
create_video_brief
review_video_brief
build_video_provider_payload（仅 confirmed brief 后）
check_video_reference_readiness
check_video_live_readiness
check_video_task_status（只读）
```

必须停下等待用户的步骤：

```text
revise_video_brief：确认分镜和 prompt。
create_video_execution_policy：确认调用范围、provider、数量、预算。
submit_video_generation_task：真实外部调用。
import_video_result：如果用户手动粘贴外部 URL，需要确认它属于当前产品任务。
record_video_result_feedback：需要用户选择/评分/原因。
apply_evolution_proposal：写入 Product Brain。
```

---

## 11. 安全边界

M5 必须保留以下边界：

```text
真实视频生成必须显式确认。
真实视频任务必须记录 external_call_performed=true。
Product Brain 写入必须 proposal / apply，且显式确认。
生成视频不自动成为产品事实。
生成视频不自动证明某个分镜或 prompt 成功。
用户反馈前，视频结果只是一份交付物，不是学习结论。
本地图片没有 remote_url 时，不自动上传或伪造外部 URL。
```

预算/调用边界：

```text
默认验证不调用 live provider。
live 验证必须用户确认。
单轮建议 1 次真实视频调用。
如果超过 2 次，需要说明原因并再次确认。
```

---

## 12. M5 小版本路线

### M5.0 架构确认

目标：

```text
确认 M5 的主线、边界、provider 策略、数据结构、workflow 方向和验收标准。
```

产物：

```text
M5_VIDEO_GENERATION_EXECUTION_ARCHITECTURE.md
PRODUCT_MAINLINE_ROADMAP.md 更新 M5 入口说明
```

验收：

```text
用户确认 M5 方向。
确认 M5 聚焦真实视频生成执行闭环。
确认 M5 不做视频编辑器、平台发布、复杂 QA。
```

### M5.1 Video Execution Readiness Audit

目标：

```text
盘点当前产品是否具备生成真实视频的条件。
```

开发内容：

```text
新增/强化 video execution readiness summary。
检查 Product Brain、video brief、confirmed status、provider payload、remote_url、API key、provider config。
Hermes 对话能告诉用户缺什么。
```

验收：

```text
对任意产品，能输出是否可进入视频生成。
缺素材、缺 remote_url、缺 confirmed brief、缺 key 时给出明确下一步。
不调用外部模型。
```

### M5.2 Video Reference Access Gate

目标：

```text
把“本地素材”和“provider 可访问 URL”分清楚，避免图生视频时使用不可访问文件。
```

开发内容：

```text
检查 video brief source_assets 中每个参考图的 remote_url。
新增 check_video_reference_readiness。
没有 remote_url 时 workflow 停下并提示绑定 URL。
支持继续使用 asset-bind-url 绑定 URL。
```

验收：

```text
本地图片仍是 canonical material。
provider payload 不会把本地路径误当成可访问 URL。
没有 remote_url 时不能 live submit。
```

### M5.3 Video Provider Payload Hardening

目标：

```text
加固 confirmed video brief 到 provider payload 的映射。
```

开发内容：

```text
复用 build_video_provider_payload。
检查 prompt 长度、shot 数、ratio、duration、generate_audio、reference images。
保存 provider_request_draft。
让 payload 明确 body_ready_for_live 和 blockers。
```

验收：

```text
confirmed brief 可以生成 provider payload。
未确认 brief 被阻断。
payload 中有完整 text prompt 和 reference_image。
body_ready_for_live 正确反映 remote_url 状态。
```

### M5.4 Video Execution Policy / Approval

目标：

```text
真实视频调用前，让用户确认执行范围和成本边界。
```

开发内容：

```text
新增 video execution policy artifact。
记录 provider、mode、count、duration、ratio、generate_audio、external_call_limit、source_payload_id、expires_at。
单条视频默认只允许一次 live submit。
```

验收：

```text
没有 policy 或 explicit confirmation 时不能 live submit。
policy 不写 Product Brain。
policy 超出范围时 workflow 停下。
```

### M5.5 Submit Live Video Task

目标：

```text
把 confirmed payload 真实提交到默认视频 provider，并保存 task record。
```

开发内容：

```text
强化 submit_video_generation_task。
调用 volcengine-ark-video。
保存 generation job 和 video task artifact。
记录 remote_task_id、provider response、request body、external_call_performed=true。
失败时保存失败原因。
```

验收：

```text
mock / dry-run 默认回归不调用外部模型。
live 调用只有用户确认时执行。
成功时保存 video_task_id 和 remote_task_id。
失败时保存可读失败原因。
```

### M5.6 Task Status / Result Retrieval

目标：

```text
让异步视频任务产生可交付结果，而不是只停在 remote_task_id。
```

开发内容：

```text
新增 check_video_task_status。
支持 provider status endpoint 或用户手动 result URL import。
保存 video_task_status artifact。
生成 normalized generated_video result artifact。
如果 result URL 可下载，best-effort 下载 mp4 到 generated_videos。
```

验收：

```text
能从 video_task_id 查询或导入结果。
结果包含 remote_url、local_path（如已下载）、provider、source_payload_id、source_brief_id。
失败/处理中/完成三类状态清晰。
```

### M5.7 Video Result Feedback to Proposal

目标：

```text
用户评价视频成片后，系统能把反馈转成可确认学习。
```

开发内容：

```text
复用或强化 result feedback。
支持 video result 的 selected、rating、issues、like/dislike reasons。
质量维度优先围绕 prompt/brief：product_recognizability、storyboard_following、pacing、style_fit、caption_fit。
evolve 从视频结果反馈生成 proposal。
```

验收：

```text
用户反馈不会直接写 Product Brain。
allow_evolve=true 且反馈合格时生成 proposal。
apply 后下一轮 video brief 能读取 video_script_preferences / successful_patterns。
```

### M5.8 Hermes Chat End-to-End Validation

目标：

```text
确认 M5 不是脚本系统，而是 Hermes 对话可用的视频生成闭环。
```

开发内容：

```text
新增 verify_m5_video_execution_loop.ps1 默认无 live 验证。
新增可选 live 验证参数。
使用 start_hermes_product_creative_dev.ps1 做至少一次项目内 Hermes chat 验证。
更新 roadmap 状态。
```

验收：

```text
Hermes chat 能从自然语言进入视频链路。
能停在分镜确认、live 调用确认、Product Brain apply 确认。
默认回归不消耗外部费用。
可选 live 验证能真实提交并保存视频 task/result artifact。
```

---

## 13. M5 验证策略

### 13.1 默认验证

默认验证必须：

```text
不调用真实外部视频模型。
不消耗 API 费用。
不写入 Product Brain，除非测试中显式 apply 到隔离测试产品。
可重复运行。
验证 Hermes chat/tool 入口。
```

建议脚本：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m5_video_execution_loop.ps1
```

默认覆盖：

```text
workspace resolve
product ingest
material register / mock analyze / visual align
material cards / task material pack
video intent
video brief
video brief review
video brief confirm
provider payload
reference readiness
live readiness blocked or mock-ready
mock task/result record
video result feedback
proposal boundary
```

### 13.2 可选 live 验证

live 验证必须：

```text
用户明确确认。
默认 1 次真实视频调用。
保存 external_call_performed=true。
保存 provider request 和 response。
保存 video task artifact。
如果 provider 返回结果 URL，保存 generated_video artifact。
```

建议脚本：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m5_video_live.ps1
```

### 13.3 回归验证

M5 完成后至少回归：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m4_9_hermes_conversation_entry.ps1
.\.hermes\plugins\product_creative\scripts\verify_m4_image_productization_loop.ps1
.\.hermes\plugins\product_creative\scripts\verify_m3_asset_library_loop.ps1
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_run.ps1
```

---

## 14. 进入 M6 的条件

只有满足以下条件，才进入 M6 联网搜索与趋势灵感：

```text
用户可以通过 Hermes chat 自然语言启动视频生成链路。
Hermes 能读取 Product Brain 和 M3 素材包。
视频 brief 必须经过 review / confirm。
provider payload 必须通过 reference readiness 和 live readiness。
真实视频调用必须有 execution policy 或 explicit confirmation。
系统能保存 video task record。
系统能保存 generated video result artifact，至少包含 remote_url 或 local_path。
用户能对视频结果反馈。
反馈能生成 Product Brain proposal。
Product Brain 写入仍需人工 apply。
默认回归不调用外部模型。
```

如果这些条件未满足，不进入 M6。

原因：

```text
M6 的热点/趋势输入会影响视频选题和脚本方向。
如果 M5 的视频执行闭环不稳定，引入联网趋势会把问题复杂化，难以判断是产品理解问题、趋势问题、素材问题还是 provider 执行问题。
```

---

## 15. 待确认关键决策

### 15.1 默认视频 provider

建议：

```text
默认 live provider 使用 volcengine-ark-video / doubao-seedance-2-0-mini-260615。
```

原因：

```text
当前 provider_registry 已有该 provider。
用户之前已提供豆包视频生成示例。
M5 重点是执行闭环，不是多 provider marketplace。
```

### 15.2 视频任务状态 / 结果获取方式

需要确认：

```text
豆包视频任务查询/结果获取 endpoint 或 curl 示例。
```

可选策略：

```text
优先 provider status endpoint 自动查询。
如果暂时没有 endpoint，则先支持用户粘贴 result URL 导入。
```

### 15.3 本地素材如何给 provider 访问

建议：

```text
M5 继续使用 asset-bind-url。
用户或上游流程负责把本地图片绑定为 provider-accessible remote_url。
M5 不实现自动上传/托管服务。
```

原因：

```text
本地素材是 canonical asset；remote_url 是执行句柄。
自动托管涉及对象存储、权限、有效期和成本，不应混入 M5 MVP。
```

### 15.4 live 调用预算

建议：

```text
M5 开发期默认可做 1 次真实视频调用验证。
如需要第 2 次，说明原因后再执行。
超过 2 次必须重新确认。
```

### 15.5 视频结果保存方式

建议：

```text
MVP 必须保存 remote_url 和 provider metadata。
如果 URL 可下载，best-effort 下载 mp4 到 artifacts/generated_videos。
下载失败不阻断结果 artifact，但记录失败原因。
```

### 15.6 视频反馈学习对象

建议：

```text
反馈重点学习分镜、prompt、产品识别、节奏和风格。
不默认做视频内容多模态 QA。
不把 provider 画质好坏直接写入 Product Brain。
```

### 15.7 UI 入口

建议：

```text
M5 仍以 Hermes chat / Agent 对话为主入口。
不开发新 UI。
Hermes Desktop 只作为可选审阅入口。
```

---

## 16. 主线防偏检查

M5 每个小版本完成后都必须回答：

```text
它是否增强了对同一个产品的视频生成理解？
它是否让下一次视频 brief / prompt / result 更贴合该产品？
它是否能通过 Hermes chat / Agent 对话和 workflow 被智能体稳定调用？
它是否保留了真实外部调用确认边界？
它是否保留了 Product Brain proposal / apply 边界？
它是否复用了 Product Brain 和 M3 素材库，而不是做孤立视频工具？
它是否避免把脚本命令当成最终用户入口？
```

如果答案不能成立，该功能不进入 M5。
