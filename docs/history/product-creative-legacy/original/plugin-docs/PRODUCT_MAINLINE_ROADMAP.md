# Product Creative Mainline Roadmap

本文档用于约束当前 `product_creative` 插件后续开发，防止从“围绕单一产品持续认知和自迭代”跑偏成孤立工具堆叠。

## 1. 产品主线

最终产品不是单次文案、图片或视频生成器，而是一个以 Hermes-Agent 为执行内核、以 Product Wiki / Product Brain 为认知层的产品内容智能体。

主线闭环：

```text
用户输入 / 素材 / 反馈
  -> Product Brain 更新或待确认提案
  -> 渠道目标与生成任务选择
  -> 文案 / 图片 brief / 视频分镜脚本 / provider prompt
  -> 可选外部模型执行
  -> 人工确认
  -> 反哺 Product Brain、channel playbook、素材使用规则
```

任何新能力都应回答三个问题：

```text
是否增强了对同一个产品的长期理解？
是否让下一次生成更贴合该产品和渠道？
是否能通过 Hermes 对话入口和 workflow 被智能体稳定调用？
```

不能回答这三个问题的功能，默认不进入当前主线。

### 1.1 当前阶段主验收口径

当前阶段的最高优先级不是继续增加图片、视频或 UI 功能，而是把已有 `product_creative` 能力从脚本验证推进到 Hermes 对话入口验证。

主验收必须满足：

```text
用户通过 Hermes chat / Hermes Agent 对话表达产品任务。
Hermes 能看到并调用 product_creative 工具，优先使用 product_workflow_run。
workflow-run 能读取 Product Brain、素材卡片和当前 workflow 状态。
系统在人工确认、Product Brain 写入或真实外部模型调用前停住。
脚本只作为诊断、隔离回归和开发辅助，不作为用户主入口。
```

在这条验收链路跑通前，不进入新的大版本能力开发。

## 2. 当前保留能力

当前已经形成的有效能力应继续保留：

- Product Brain / Product Wiki：保存产品事实、卖点、风格、渠道规则、学习偏好。
- 多渠道文案：支持小红书种草、抖音短视频脚本等目标内容生成。
- brief 能力：把产品认知转为图片 brief、视频 brief、provider-ready prompt。
- 外部图片生成：已接入图片 provider，能从 image brief 生成真实图片并保存结果。
- 素材库雏形：可注册本地素材，绑定 provider 可访问 URL，生成 material manifest。
- 主图理解链路：可对注册主图生成分析 artifact，再人工确认后对齐 Product Brain。
- 视频意图与分镜：可从产品理解、素材和用户意图生成视频 intent、storyboard brief、review package。
- Workflow 编排：可用 `workflow-status`、`workflow-next`、`workflow-plan`、`workflow-execute` 驱动下一步。
- 对话式入口：必须让 Hermes 对话模型通过 tool calling 调用 `product_workflow_run`，而不是由用户手动拼接业务脚本命令。

## 3. 已降级或移出 M2 主线的能力

以下能力不是当前 M2 主线，后续只有在真实产品需要时再独立评估：

- 视频任务轮询。
- 视频结果 URL 导入作为必经步骤。
- 生成视频二进制下载。
- 生成后视频多模态 QA。
- 围绕视频文件本身的默认评分闭环。

原因：用户目标里的视频质量主要由产品理解、素材理解、分镜脚本和 provider prompt 决定。M2 应优先打磨这些上游控制面，而不是过早建设视频后处理工程。

## 4. M2 收口状态

M2 当前进入冻结状态，不继续默认追加 M2.x 小功能。

后续 M2 只允许：

```text
bug fix
回归测试修复
文档纠偏
用户确认的安全边界修正
```

不再继续追加类似 `workflow-run review package` 的 M2.x 能力，除非该能力被证明是进入 M3/M4 的阻断项。

### M2.28 视频 brief 编辑与确认（已落地）

目标：在生成 provider payload 前，允许用户对分镜脚本、镜头顺序、字幕、音频、参考素材使用方式进行结构化修改。

验收：

```text
能读取现有 video brief
能生成 editable review patch
能保存用户确认后的 revised video brief
workflow-next 会优先推荐确认 brief，再推荐 provider payload
```

当前实现：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-review --id <product-id> --brief <video-brief-id>
```

审阅包会生成一个可编辑 patch：

```text
.hermes/product_creative/products/<product-id>/artifacts/video_brief_patches/<patch-id>.json
```

用户编辑 patch 后确认生成 revised brief：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-revise --id <product-id> --brief <video-brief-id> --patch <patch-id> --confirmed
```

确认后的 revised brief 状态为 `confirmed_for_provider_payload`，workflow 才会推荐 `build_video_provider_payload`。

### M2.29 视频脚本反馈反哺（已落地）

目标：用户不需要等视频生成，也可以直接评价脚本和分镜，形成 Product Brain / channel playbook proposal。

验收：

```text
能针对 video brief 记录反馈
反馈能生成 proposal
proposal 需要人工 apply
下一轮同产品视频 brief 能读取已确认偏好
```

当前实现：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-feedback --id <product-id> --brief <video-brief-id> --selected --rating 5 --allow-evolve --note "这个分镜结构适合当前产品，后续继续使用开场钩子和产品回看结构。"
```

可选评分维度：

```text
hook_strength
storyboard_clarity
product_grounding
prompt_specificity
channel_fit
factuality
```

该反馈不会直接修改 Product Brain。只有后续执行：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id <product-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id <product-id> --action apply_evolution_proposal --proposal <proposal-id> --confirmed
```

确认后的学习会进入 `learning.video_script_preferences`，下一轮 `video-brief` 会把它写入 prompt。

### M2.30 主图理解真实 VLM 接口（已落地）

目标：把当前主图理解的 mock / 结构化占位升级为可替换 provider 接口，优先支持真实多模态模型。

验收：

```text
本地图片仍是 canonical material
真实 VLM 输出保存为 image analysis artifact
人工确认后才能写入 Product Brain
无 key 或 provider 不可用时保留 dry-run 路径
```

当前实现：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-analyze --id <product-id> --asset <material-id> --provider volcengine-ark-vlm
```

关键边界：

```text
调用豆包 Responses 多模态模型 doubao-seed-2-1-pro-260628
优先使用素材绑定的 remote_url，没有 remote_url 时尝试 data-url 输入
输出保存为 artifacts/image_analysis/<analysis-id>.json
不直接修改 Product Brain / Product State
visual-align 会读取 VLM 风险；如果图片不是目标产品或 VLM 输出无法结构化，会阻断学习
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_vlm_image_analysis.ps1
```

该验证会真实调用一次 VLM，并使用一张非目标产品的公开视频 URL 确认安全门禁：能生成 image analysis artifact，但不能进入 Product Brain 学习。

### M2.31 一条对话式工作流验证（已落地）

目标：让 Hermes 工作流从“脚本命令可用”进一步靠近“智能体可连续对话调用”。

验收：

```text
conversation-adapter 能把用户自然语言映射到下一步 action
workflow-execute 能连续执行产品创建、素材注册、分析、brief、review
关键写入仍需人工确认
```

当前实现：

```text
新增 workflow actions:
register_material_asset
analyze_material_image
align_visual_analysis
```

对话式入口示例：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id <product-id> --message "上传主图作为当前产品视觉参考" --path "<local-image-path>" --role current_main_image
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id <product-id> --message "分析主图"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id <product-id> --message "对齐主图理解"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id <product-id> --message "用这张主图生成今日视频"
```

安全边界：

```text
默认图片分析 provider 为 mock-vision，不自动调用外部模型。
通过 workflow 使用非 mock provider 时需要 explicit confirmation。
image-analyze 和 visual-align 不直接修改 Product Brain。
Product Brain 正式写入仍必须走 proposal/apply，并由用户确认。
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_conversation_workflow.ps1
```

该验证会用自然语言连续执行 create -> ingest -> asset register -> image analyze -> visual align -> video intent -> video brief -> review package，且不调用外部模型。

### M2.32 安全多步 workflow-run（已落地）

目标：让 Hermes 不只执行单个 workflow step，而能从一个用户意图出发，连续推进多个安全步骤，并在需要用户输入、人工确认、Product Brain 写入或真实外部模型调用前停住。

当前实现：

```text
新增 CLI / tool:
workflow-run
product_workflow_run
```

自动推进规则：

```text
第一步使用用户 message/action 和参数执行。
后续只自动执行 ready_to_execute 的安全步骤。
不会自动执行需要用户输入的步骤。
不会自动执行需要 explicit confirmation 的步骤。
不会自动写入 Product Brain。
不会自动提交真实视频生成任务。
不会自动调用非 mock 的图片理解 provider。
达到 max_steps 后停止，默认 5，最多 10。
```

典型链路：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-run --id <product-id> --message "上传主图作为当前产品视觉参考" --path "<local-image-path>" --role current_main_image
```

自动执行：

```text
register_material_asset
-> analyze_material_image
-> align_visual_analysis
-> 停在需要用户输入的下一步
```

视频链路：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-run --id <product-id> --message "用这张主图生成今日视频"
```

自动执行：

```text
resolve_video_intent
-> create_video_brief
-> review_video_brief
-> 停在 revise_video_brief，因为需要人工确认
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_run.ps1
```

该验证确认 workflow-run 能自动推进素材理解和视频 brief 链路，同时不会写入 Product Brain，不会生成 provider payload，不会触发真实 VLM 调用。

### M2.33 workflow-run session record（已落地）

目标：让每一次自动 workflow-run 都留下可审阅、可追溯的执行记录，便于用户和 Agent 看清楚“系统自动做了什么、为什么停住、下一步需要什么”。

当前实现：

```text
workflow-run 每次执行都会保存:
artifacts/workflow_runs/<workflow-run-id>.json
artifacts/workflow_runs/<workflow-run-id>.md
structured/workflow_run_index.jsonl
```

记录内容：

```text
执行过的 action 列表
每一步是否执行成功
每一步的主要产物 id
stop_reason
recommended_next_action
safety contract
post_status
```

边界：

```text
session record 只是审计产物。
不额外执行任何 workflow action。
不修改 Product Brain。
不改变 M2.32 的自动推进安全规则。
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_run.ps1
```

该验证会确认 workflow-run record 被写入本地 artifact，并被 artifact-manifest 识别为 `workflow_run`。

## 5. 大版本路线

### M3 素材卡片与文件读取

状态：M3.1-M3.8 已落地并通过本地验证。

把素材从“已注册文件”升级为 Hermes 可读取、可判断、可用于生成前决策的素材卡片体系。

M3 不做复杂向量数据库，不做重型语义检索。M3 的主线是复用 M2 的图片理解产物，将 `material_assets`、`image_analysis`、`visual_alignments` 聚合为 AI-readable material cards，并在生成前准备 task material pack。

核心能力：

- 读取 M2 material asset / image analysis / visual alignment。
- 生成 Hermes 可读的 material card。
- 生成产品级 Material Library Map。
- 按任务生成 Task Material Pack。
- image brief / video brief / channel content 可读取素材卡片。
- 记录素材使用与用户反馈。

M3 开发前置设计已固定在：

```text
.hermes/plugins/product_creative/docs/M3_ASSET_RETRIEVAL_ARCHITECTURE.md
```

M3 小版本路线：

```text
M3.0 架构修订与确认：已完成
M3.1 M2 素材产物兼容层：已完成
M3.2 Material Card 生成：已完成
M3.3 Material Library Map：已完成
M3.4 Task Material Pack：已完成
M3.5 生成链路集成：已完成
M3.6 素材使用记录：已完成
M3.7 素材反馈与轻量偏好：已完成
M3.8 M3 验收与 M4 入口检查：已完成
```

当前实现入口：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 material-compat --id <product-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 material-card-rebuild --id <product-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 material-library-map --id <product-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 task-material-pack --id <product-id> --task video_brief --channel douyin --limit 3
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 material-feedback --id <product-id> --material <material-id> --task video_brief --channel douyin --selected --rating 5 --note "<note>"
```

Workflow 衔接：

```text
上传/注册素材后，workflow-run 可自动执行：
register_material_asset -> analyze_material_image -> align_visual_analysis -> rebuild_material_cards

随后停在 prepare_task_material_pack，因为 task/channel 属于生成目标决策，需要用户或对话消息提供。
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m3_asset_library_loop.ps1
```

已回归：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_visual_materials.ps1
.\.hermes\plugins\product_creative\scripts\verify_m2_visual_alignment.ps1
.\.hermes\plugins\product_creative\scripts\verify_m2_video_intent.ps1
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_run.ps1
```

进入 M4 的硬性条件：

```text
M3 能完整读取 M2 material_assets / image_analysis / visual_alignments。
每个 active material 都能生成 Hermes 可读 material card。
Material Library Map 能让 Hermes 快速知道素材库状态。
Task Material Pack 能为 image brief / video brief / channel content 准备少量相关素材。
不手动传 asset 的情况下，image brief / video brief 能引用 task material pack。
素材使用记录和反馈能影响下一轮 task material pack。
默认验证不调用真实外部模型。
Product Brain 高影响写入仍有人工确认门禁。
```

### M4 图片生成产品化

状态：M4.1-M4.9 已落地。M4.9 已通过项目内 Hermes chat 对话验证。

把已跑通的真实生图能力产品化，重点不是多接几个模型，而是让图片 brief、prompt、结果反馈形成稳定闭环。

核心能力：

- 图片 brief 编辑确认。
- 多 provider 适配。
- 多版本图片生成与对比。
- 用户选择结果后反哺 visual identity / ecommerce playbook。

M4 开发前置设计固定在：

```text
.hermes/plugins/product_creative/docs/M4_IMAGE_GENERATION_PRODUCTIZATION_ARCHITECTURE.md
```

M4 小版本路线：

```text
M4.0 架构确认：已完成
M4.1 Image Intent 与用户目标解析：已完成
M4.2 Image Brief Review / Patch / Confirm：已完成
M4.3 M3 Material Pack 与 Image Brief 深度衔接：已完成
M4.4 Image Provider Payload Gate：已完成
M4.5 Multi-Variant Image Run：已完成
M4.6 Image Result Feedback to Proposal：已完成
M4.7 Selected Image Asset Registration：已完成
M4.8 M4 综合验收与 M5 入口检查：已完成
M4.9 Hermes 对话入口产品化：已完成
```

当前实现入口：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-intent --id <product-id> --message "帮我生成3张电商主图，高级感" --count 3
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-brief --id <product-id> --intent <image-intent-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-brief-review --id <product-id> --brief <image-brief-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-brief-revise --id <product-id> --brief <image-brief-id> --patch <patch-id> --confirmed
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 batch-policy --id <product-id> --intent <image-intent-id> --brief <image-brief-id> --provider volcengine-ark-image --mode mock --count 3 --confirmed
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-provider-payload --id <product-id> --brief <image-brief-id> --provider volcengine-ark-image --batch-policy <policy-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-run --id <product-id> --payload <payload-id> --provider generic --mode mock --count 2
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 selected-image-asset --id <product-id> --result <image-result-id> --role generated_candidate
```

Workflow 衔接：

```text
用户可通过 workflow-run 说“帮我生成3张电商主图，高级感”。
系统会自动执行 resolve_image_intent -> create_image_brief -> review_image_brief。
随后停在 revise_image_brief，因为单次 brief 确认或 batch generation policy 需要人工确认。
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m4_image_productization_loop.ps1
```

该验证不调用外部模型，确认 image intent、image brief review、batch policy、provider payload、mock image run、result feedback、evolution proposal、selected image asset registration 均能闭环。

### M4.9 Hermes 对话入口产品化

状态：已完成，并通过项目内 Hermes chat 验证。

目标：把 M4 已有能力从脚本级验证收口到 Hermes chat / Agent 对话入口。

M4.9 不新增图片或视频业务能力，而是补齐产品化入口：

```text
product_workspace_resolve：用户说产品名时先定位本地 product_id。
product_workflow_run：继续作为自然语言主入口，支持 product_query 辅助解析。
user_next_message：工具结果返回用户下一句可以怎么继续，而不是要求用户运行脚本。
start_hermes_product_creative_dev.ps1：开发态 Hermes chat 启动入口。
Hermes Desktop 审阅文档：明确 Desktop 只是临时 UI 审阅，不替代 chat/tool 验收。
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m4_9_hermes_conversation_entry.ps1
```

真实 Hermes chat 验证已确认：

```text
Hermes 能调用 product_workspace_resolve / product_workflow_run。
返回 workflow_run_id、recommended_next_action.action、user_next_message。
Product Brain apply 停在明确确认边界。
```

M4.9 完成标准：

```text
Hermes chat 能加载 product_creative 插件。
Hermes 能调用 product_workspace_resolve 或 product_workflow_run。
用户可以用自然语言补充产品资料、生成内容、记录反馈。
反馈能生成 Product Brain proposal，但 apply 前必须停下确认。
工具结果优先给出 user_next_message。
脚本仍只作为诊断、回归和人工兜底入口。
```

### M5 视频生成执行

状态：M5.1-M5.8 已落地。

在 M4.9 对话入口收口后，再接入真实视频生成。

核心能力：

- image-to-video provider payload。
- 视频参考素材 URL readiness gate。
- live readiness gate。
- 人工确认的视频 execution policy。
- 豆包 Seedance live async video task 提交。
- video task status 查询。
- generated video result artifact 保存。
- 手动视频结果 URL 导入。
- 用户对生成视频结果的反馈反哺 proposal。

不开发视频编辑器、视频平台发布、复杂视频 QA。视频下载只做 best-effort；结果 URL 才是 M5 MVP 的稳定交付句柄。

M5 开发前置设计固定在：

```text
.hermes/plugins/product_creative/docs/M5_VIDEO_GENERATION_EXECUTION_ARCHITECTURE.md
```

M5 小版本落地结果：

```text
M5.0 架构确认：已完成
M5.1 Video Execution Readiness Audit：已完成
M5.2 Video Reference Access Gate：已完成
M5.3 Video Provider Payload Hardening：已完成
M5.4 Video Execution Policy / Approval：已完成
M5.5 Submit Live Video Task：已完成，真实提交 remote_task_id=cgt-20260708122312-r7lnb
M5.6 Task Status / Result Retrieval：已完成，异步任务最终状态 succeeded/completed，真实结果 video-result-20260708-123335 已保存
M5.7 Video Result Feedback to Proposal：已完成，反馈生成 proposal-20260708-122357
M5.8 Hermes Chat End-to-End Validation：已完成，workflow-run 可自然语言触发 check_video_task_status
```

验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m5_video_generation_execution.ps1
```

本验证脚本默认不提交 live 视频任务；它验证 M5 的非付费结构链路。真实 live 提交在开发时已执行 1 次。
视频 provider 为异步任务模型，提交后 `running / processing` 是正常等待态；只有后续 status 查询回写最终状态后，才算完成真实结果归档。
本次真实任务最终结果：

```text
remote_task_id: cgt-20260708122312-r7lnb
video_task_id: video-task-20260708-122312
final_status: succeeded / completed
result_id: video-result-20260708-123335
local_video: artifacts/generated_videos/video-result-20260708-123335.mp4
```

进入 M6 的硬性条件：

```text
Hermes workflow 能从视频意图推进到 confirmed video brief。
provider payload 能显式检查 reference readiness。
live readiness 和 execution policy 能阻止误触发外部视频模型。
真实视频任务能提交并保存 video_task。
系统能查询 video_task_status。
系统能保存 generated video result，至少包含 remote_url。
用户反馈能生成 Product Brain proposal，且 proposal apply 仍需人工确认。
```

### M6 Material Resolver 与外部灵感 Agent

状态：M6.1-M6.10 已完成；凭据配置后小红书/抖音 sidecar 小样本真实验证已跑通。

M6 不再按“remote_url 优先、竞品搜索随后”的旧理解推进。M6 的新锚点是：

```text
MaterialResolver：把本地素材、data-url、remote_url、asset://、对象存储 URL 统一解析成 provider execution input。
Inspiration Gateway：把通用网页、小红书、抖音、手动资料中的热点、梗、场景、钩子、评论洞察和竞品表达统一沉淀为可审计灵感候选。
```

M6 解决两个真实产品问题：

```text
用户不应该理解外部模型 image_url/video_url/audio_url 的底层差异。
外部资料应该帮助生成文/图/视频，但不能绕过 proposal 写入 Product Brain。
```

M6 开发前置设计固定在：

```text
.hermes/plugins/product_creative/docs/M6_ASSET_HOSTING_AND_EXTERNAL_INSPIRATION_ARCHITECTURE.md
```

M6 推荐小版本路线：

```text
M6.1 Schema and Boundary Refresh
M6.2 MaterialResolver MVP
M6.3 Generic Web and Manual Import Source Provider
M6.4 XHS Local Research Provider Adapter
M6.5 Douyin Local Research Provider Adapter
M6.6 Product Relevance and Inspiration Mining
M6.7 Inspiration Pack to Brief Integration
M6.8 MaterialResolver to Image/Video Payload Integration
M6.9 Hermes Conversational End-to-End Validation
M6.10 M6 Closeout
```

M6 closeout 记录：

```text
offline_verification: passed
offline_script: .hermes/plugins/product_creative/scripts/verify_m6_material_inspiration_loop.ps1
live_sidecar_script: .hermes/plugins/product_creative/scripts/verify_m6_sidecar_live_small.ps1
xhs_live_status: completed, snapshot=source-snapshot-20260708-170931, items_count=2, pack=inspiration-pack-20260708-171004
douyin_live_status: completed, snapshot=source-snapshot-20260708-170008, items_count=2, pack=inspiration-pack-20260708-170010
credential_policy: no cookies or API keys saved into Product Creative artifacts
status_fix: XHS sidecar may return usable notes while browser-cookie refresh fails; product_creative now avoids treating usable partial data as a total block.
llm_inspiration_validation: passed with Hermes ctx.llm using deepseek/deepseek-v4-pro
xhs_llm_pack: llm-inspiration-pack-20260708-174559, status=review_required
douyin_llm_pack: llm-inspiration-pack-20260708-174714, status=review_required
confirmation_guard: inspiration library write requires explicit user confirmation
next_required_validation: validate the same LLM inspiration path from Hermes chat / Agent conversation, not only from scripts.
```

M6.11-M6.15 closeout 记录：

```text
M6.11: LLM 深度灵感包正式化，写入 summary_type/status_reason/review_contract/llm.call_mode。
M6.12: inspiration-pack 按 target_channel 过滤并去重，不足时才补 secondary_reference。
M6.13: 新增真实产品 workspace 验证脚本，避免测试产品成为核心锚点。
M6.14: 新增 inspiration_library 确认沉淀验证，未确认不写入，确认后 generate 可读取 inspiration_library。
M6.15: 新增 Hermes chat 验证脚本，已通过真实 Hermes CLI chat 触发 product_llm_inspiration_pack。

offline_selection_script: .hermes/plugins/product_creative/scripts/verify_m6_11_12_llm_inspiration_selection.ps1
real_product_script: .hermes/plugins/product_creative/scripts/verify_m6_13_real_product_inspiration.ps1
library_confirm_script: .hermes/plugins/product_creative/scripts/verify_m6_14_inspiration_library_confirm.ps1
hermes_chat_script: .hermes/plugins/product_creative/scripts/verify_m6_15_hermes_chat_inspiration.ps1

latest_real_llm_pack: llm-inspiration-pack-20260709-101157
latest_hermes_chat_session: 20260709_101320_338235
latest_hermes_chat_pack: llm-inspiration-pack-20260709-101440
M6_status: closed for current architecture
```

核心能力：

- 本地素材仍是 canonical asset。
- data-url、remote_url、asset:// 都只是外部 provider 的执行句柄。
- Hermes 能解释素材可用方式：直接 data-url、已有 URL、需要 URL、需要对象存储或暂不可用。
- 现有 `asset-bind-url` 保留为 manual-bind remote provider。
- 小红书 / 抖音以 sidecar provider 或导出数据方式接入，不整套照搬。
- 外部资料只作为 source snapshot / inspiration candidate，不直接覆盖产品事实。
- 热点、梗、场景、评论洞察、视频钩子和竞品信息都可以成为灵感，但必须标记 not_product_fact。
- 渠道 playbook 只能吸收人工确认后的外部规律。
- 默认方向从规则抽取升级为 LLM 深度总结：规则抽取保留为 fallback；LLM pack 先进入 review_required，用户确认后才沉淀到 inspiration_library。

M6 结束条件：

```text
用户可以通过 Hermes chat/Agent 表达“抓取/整理外部灵感、用 LLM 深度总结、审阅后确认沉淀”的目标。
系统可以把外部平台/网页/manual 来源变成 source snapshot。
系统可以把 source snapshot 转成规则灵感包或 LLM 深度灵感包。
系统不会把外部灵感当产品事实写入 Product Brain。
用户确认后，灵感可以沉淀到 inspiration_library，并被后续文案/brief 生成读取。
```

M7 入口：

```text
M7 不再继续扩外部抓取或素材接入。
M7 聚焦“自迭代评估”：用户如何评价生成结果，系统如何从结果反馈中总结成功模式，并通过 proposal 机制在人工确认后更新长期认知。
M7 的验收标准不再是能生成更多内容，而是能解释为什么某个版本更适合当前产品，并把该规律安全沉淀。
```

### M7 自迭代评估

让系统知道哪些内容风格更适合当前产品，而不是只保存用户喜欢什么。

核心能力：

- 实验记录。
- 用户选择和修改痕迹。
- 版本对比。
- 可解释的偏好更新。

当前 M7 锁定范围：

```text
M7.0: 固定 M7 主线边界，不扩抓取、不扩 provider、不做 UI。
M7.1: 新增 generation_safe，生成只读干净产品认知，避免 URL/来源/测试记录污染 prompt。
M7.2: 新增 result-review-package，把真实图片/视频结果整理成人工审阅包。
M7.3: 增强 result-feedback，支持图像/视频结果维度化反馈。
M7.4: 新增 result-evaluate，Hermes runtime 内可用 LLM 评估结果，离线用规则 fallback。
M7.5: evolve proposal 读取 result_evaluation，把建议放入人工确认队列。
M7.6: apply proposal 后，学习进入 image_generation_preferences / video_script_preferences / successful_patterns / failed_patterns，并影响下一轮生成。
M7.7: 新增 Hermes tools 与 workflow actions：product_result_review_package、product_result_evaluate、review_generated_result、evaluate_generated_result。
M7.8: closeout checks，验证反馈、评估、proposal、apply、下一轮读取的闭环。
M7.9: full validation，输出完整测试产物和中间文件。
```

M7 的核心验收不是“多生成一个内容”，而是：

```text
用户对真实图/视频结果的评价，可以被系统转成可解释学习建议；
建议必须等待人工确认；
确认后的学习能影响下一轮图/视频相关生成；
原始证据和生成上下文分离，避免把来源、URL、测试样例写成产品事实。
```

M7 完成记录：

```text
status: closed
architecture_doc: .hermes/plugins/product_creative/docs/M7_SELF_ITERATION_EVALUATION_ARCHITECTURE.md
generation_safe: implemented
result_review_package_tool: product_result_review_package
result_evaluate_tool: product_result_evaluate
workflow_actions: review_generated_result, evaluate_generated_result
small_loop_validation: .hermes/plugins/product_creative/scripts/verify_m7_self_iteration_loop.ps1
hermes_chat_validation: .hermes/plugins/product_creative/scripts/verify_m7_7_hermes_result_iteration_entry.ps1 -RunChat -MaxTurns 4
hermes_chat_session: 20260709_121241_ab94ca
full_validation: .hermes/plugins/product_creative/scripts/verify_m7_9_full_validation.ps1
full_validation_report: .hermes/product_creative/products/jindouya-jinyinhuayouzi-20260709-demo/artifacts/m7_validation/m7-full-validation-20260709-121532.md
latest_image_result_used: image-result-20260709-105000
latest_video_result_used: video-result-20260709-111028
external_image_or_video_call_in_m7_validation: false
```

M8 入口：

```text
M8 可以开始，但不能回到脚本中心。
下一阶段应把现有 Hermes chat/tool/workflow 能力包装成用户可审阅的产品界面或 Desktop 对话体验：
- 用户能看到 Product Brain 当前学习。
- 用户能看到真实图/视频结果、review package、feedback、evaluation、proposal。
- 用户能一键确认或拒绝写回。
- 用户不需要理解底层脚本命令。
```

### M8 用户界面

状态：M8.0-M8.8 已完成 closeout 验证。M8 当前不直接进入完整 Web / Desktop UI，而是先把用户审阅体验和“固定主图视频”产品化。

核心能力：

- 产品空间。
- Product Brain 可视化。
- 素材库。
- 文案/图片/视频 brief 编辑器。
- 生成结果对比。
- 人工确认与回写队列。

M8 当前主线固定在：

```text
.hermes/plugins/product_creative/docs/M8_PRODUCT_REVIEW_AND_EXACT_VIDEO_ARCHITECTURE.md
```

M8.0-M8.8 已落地目标：

```text
M8.0 架构锁定：防止 M8 跑偏成新模型或新爬虫。
M8.1 任务总览包：把 Product Brain、素材、brief、payload、结果、反馈和 proposal 整理成用户可审阅包。
M8.2 视频结果审阅增强：当结果带有 main_image_policy 时，审阅包明确检查主图是否被改。
M8.3 Exact Main Image Composer：把“主图固定 + 外部动漫剧情推广”做成正式 provider/composer，输出标准 video result artifact。
M8.4 视频故事模板：anime_story、summer_refresh、problem_solution、three_claims、festival_topic。
M8.5 Hermes 对话路由：主图不能变时选择 compose_exact_main_video，不默认走外部视频模型。
M8.6 反馈到偏好：result-feedback -> result-evaluate，只生成可审阅学习建议。
M8.7 最小审阅面：task-overview-package + result-review-package + preview/video path。
M8.8 closeout：完整验证主图锁定、审阅、反馈、学习边界。
```

M8 的关键修正：

```text
如果用户要求主图不能变，系统不应默认调用会重绘产品的视频模型。
Hermes 应选择 compose_exact_main_video，把主图作为固定真实图层，只在外部生成剧情、角色、字幕和动效。
```

当前实现入口：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 task-overview-package --id <product-id> --result <result-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 exact-main-video --id <product-id> --asset <material-id> --theme "固定主图的动漫故事推广视频"
```

Hermes 工具入口：

```text
product_task_overview_package
product_exact_main_video
```

Workflow 动作：

```text
create_task_overview_package
compose_exact_main_video
```

M8 验证入口：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m8_closeout.ps1 -ProductId <product-id>
```

M8 防偏检查：

```text
它是否让用户更清楚地审阅同一产品的生成链路？
它是否保留 Product Brain proposal/apply 边界？
它是否通过 Hermes tools/workflow 可触发？
它是否避免把脚本作为用户主入口？
它是否解决真实产品主图被外部视频模型重绘的问题？
```

## 6. Hermes-Agent 使用边界

Hermes 应作为智能体执行内核：

- workflow action 是智能体可调用的稳定动作。
- tools schema 是 Agent 与插件之间的契约。
- Product Brain 是 Agent 的长期上下文来源。
- 人工确认是高风险写入的边界。

不要把 Hermes 只当成脚本启动器。脚本命令只是当前开发和验证入口，最终体验应是用户用自然语言表达目标，Hermes 根据 Product Brain 和 workflow 自动决定下一步，并在需要写入认知或调用外部模型时请求确认。

自当前阶段起，该边界进一步收紧：

```text
主线验收以 Hermes chat / Agent 对话触发为准。
product_creative.ps1 只能作为开发诊断、回归验证和人工兜底入口。
如果某项能力只能通过脚本命令触发，不能算作产品闭环完成。
Hermes.exe Desktop 不是当前阶段的必要前置，但项目内 Hermes chat 对话必须先跑通。
```
