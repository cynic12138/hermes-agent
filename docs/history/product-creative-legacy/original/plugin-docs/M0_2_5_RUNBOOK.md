# M0.2-5 Runbook

## 目标

M0.2-5 固化 M0.2-4 已跑通的真实模型链路：

```text
Product Brain / Product State
  -> product_creative project plugin
  -> Hermes ctx.llm
  -> 当前 Hermes 默认模型
  -> product-copy-pack artifact
```

当前本机默认模型已验证为：

```text
provider = deepseek
model = deepseek-v4-pro
```

## 为什么不用裸 `hermes.exe product ...`

本轮验证发现：安装版 `hermes.exe` 的插件管理命令没有发现当前工作区的 project plugin，所以裸命令不会注册 `product` 子命令。

M0.2-5 使用项目内 runner：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 ...
```

runner 会：

- 使用本机 Hermes 安装 venv 的 Python，复用已安装依赖与模型认证。
- 从当前工作区运行 Hermes 源码，因此能加载本项目 `.hermes/plugins/product_creative`。
- 临时设置 `HERMES_ENABLE_PROJECT_PLUGINS=1`。
- 临时把 `product_creative` 加入 `plugins.enabled`。
- 命令结束后恢复原始 `config.yaml`，不长期修改用户配置。

## 常用命令

创建产品：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 create --id demo-product --name "新疆吊干杏"
```

注入产品资料：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 ingest --id demo-product --text "新疆吊干杏，自然成熟，口感清甜，有果香，适合作为办公室零食和送礼。"
```

生成 copy pack：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generate --id demo-product --target product-copy-pack --variants 3
```

评估 copy pack：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evaluate --id demo-product --artifact copy-pack-xxx
```

导出标准化主图/视频 brief：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 brief --id demo-product --artifact copy-pack-xxx --variant 1 --kind all
```

使用平台预设和参考素材导出 brief：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 brief --id demo-product --artifact copy-pack-xxx --variant 1 --kind all --preset xiaohongshu-cover --asset C:\path\to\reference.png
```

当前支持的 `--preset`：

- `default`
- `taobao-main-image`
- `douyin-9x16`
- `xiaohongshu-cover`

生成 dry-run provider payload：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-generate --id demo-product --brief image-brief-xxx --provider generic
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-generate --id demo-product --brief video-brief-xxx --provider generic
```

M0.5 的 `image-generate` / `video-generate` 只生成外部模型请求草案，不调用真实生图/生视频服务。

查看和校验 provider：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 provider-list
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 provider-validate --id demo-product --payload provider-payload-xxx --provider generic
```

创建 M0.5.1 mock generation job：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generation-job --id demo-product --payload provider-payload-xxx --provider generic --mode mock
```

M0.5.1 的 `generation-job` 只支持 `dry_run` 和 `mock`，不支持真实 live 调用。

重建统一 artifact manifest：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 artifact-manifest --id demo-product
```

创建人工审阅包：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 review-package --id demo-product --job generation-job-xxx
```

## M2.17 视频意图解析

M2.17 新增 `video-intent`，用于把用户的一句话视频需求解析成下一步准备计划：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-intent --id demo-product --message "用这张主图帮我做一个抖音短视频"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-intent --id demo-product --message "帮我生成当前产品的今日视频"
```

它会读取：

- Product Brain / Product State
- Material Library
- image_analysis artifact
- visual_alignment artifact

输出位置：

```text
.hermes/product_creative/products/<product_id>/artifacts/video_intents/
.hermes/product_creative/products/<product_id>/structured/video_intent_index.jsonl
```

当前版本不会直接生成视频，也不会写入 Product Brain。它只判断当前是否缺少素材注册、主图理解、视觉对齐或主题/趋势上下文，并给出下一步推荐动作。真实视频 brief 与外部视频模型调用将在后续版本接入。

也可以从对话工作流入口触发：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 conversation-adapter --id demo-product --message "用这张主图帮我做一个抖音短视频"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --message "用这张主图帮我做一个抖音短视频"
```

`conversation-adapter` 只生成计划，不执行工具；`workflow-execute --message` 会在 guard 通过后调用 `product_video_intent` 并写入 `video_intents` artifact。普通的“生成抖音短视频脚本”仍然走 `run_channel_review`，不会被误判为图生视频准备流程。

## M2.18 视频 Brief

M2.18 将 `video_intent` 转成标准化 `video_brief`：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief --id demo-product --intent video-intent-xxx
```

输出位置：

```text
.hermes/product_creative/products/<product_id>/artifacts/video_scripts/
```

它会使用：

- Product Brain 的产品名称、简介、卖点、风格偏好、已确认学习
- Material Library 中被选中的主图/素材
- image_analysis 的视觉理解合同
- visual_alignment 的产品视觉对齐结果
- video_intent 中的平台、主题和生成路线

当前版本只生成 provider-agnostic 视频说明书，不调用外部视频模型，不写入 Product Brain。生成后的 brief 兼容已有 `video-generate` dry-run：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-generate --id demo-product --brief video-brief-xxx --provider generic
```

也可以通过 workflow 动作触发：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-plan --id demo-product --action create_video_brief
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --action create_video_brief
```

## M2.19 视频 Brief 审阅包

M2.19 将视频 brief 转成面向人工确认的审阅包：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-review --id demo-product --brief video-brief-xxx
```

输出位置：

```text
.hermes/product_creative/products/<product_id>/artifacts/review_packages/
```

审阅包会展示：

- 视频主题和平台
- 分镜表
- 外部视频模型 prompt 草案
- 使用的参考素材
- 主图/视觉理解风险
- 人工审阅 checklist
- 下一步 dry-run provider payload 命令

也可以通过 workflow 动作触发：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-plan --id demo-product --action review_video_brief
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --action review_video_brief
```

M2.19 仍然不调用真实视频模型，也不直接修改 Product Brain。用户确认应优先沉淀为视频脚本、分镜和渠道 playbook 的改进提案。

## M2.20 豆包 Seedance 视频 Payload 草案

M2.20 将 `video_brief` 转成更贴近 Volcengine Ark / 豆包 Seedance 的 provider payload。当前仍然是 dry-run / mock，不真实创建视频任务：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-generate --id demo-product --brief video-brief-xxx --provider volcengine-ark-video
```

生成的 `provider_payload` 会包含：

- `request.prompt`：经过视频 provider 适配后的 prompt
- `request.prompt_adapter.schema_version = product_creative.video_prompt_adapter.v2.20`
- `request.provider_request_draft.body`：Ark `/api/v3/contents/generations/tasks` 请求体草案
- `model = doubao-seedance-2-0-mini-260615`
- `content`：text + reference image 占位
- `ratio`
- `duration`
- `generate_audio`
- `watermark`
- `unresolved_reference_assets`

校验 payload：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 provider-validate --id demo-product --payload provider-payload-xxx --provider volcengine-ark-video
```

创建 mock job：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generation-job --id demo-product --payload provider-payload-xxx --provider volcengine-ark-video --mode mock
```

如果参考素材是本地文件，`body_ready_for_live` 会是 `false`，并在 `unresolved_reference_assets` 中说明需要先上传成本模型可访问的公网 URL。M2.20 不上传素材、不真实调用视频模型、不轮询任务结果。

记录生成结果反馈契约（当前主线优先用于图片结果；视频阶段优先反馈脚本、分镜和 prompt）：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 result-feedback --id demo-product --result image-result-xxx --note "风格接近，但主体不够清楚。" --rating 4 --issue "subject clarity"
```

检查 live provider readiness：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 live-readiness --id demo-product --provider generic --kind image --payload provider-payload-xxx
```

当前 mock provider 的 readiness 正常结果应是 `blocked`，因为 M0.5.x 不允许 live 调用。

M0.6 真实图片生成使用火山 Ark / 豆包图片 provider：

```powershell
$env:PRODUCT_CREATIVE_ARK_API_KEY="your-key"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-generate --id demo-product --brief image-brief-xxx --provider volcengine-ark-image
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 live-readiness --id demo-product --provider volcengine-ark-image --kind image --payload provider-payload-xxx
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generation-job --id demo-product --payload provider-payload-xxx --provider volcengine-ark-image --mode live
```

M0.6 的 live image provider：

- `volcengine-ark-image`
- endpoint: `https://ark.cn-beijing.volces.com/api/v3/images/generations`
- model: `doubao-seedream-5-0-260128`
- auth env: `PRODUCT_CREATIVE_ARK_API_KEY`
- request prompt: M0.6.5 adapted mapping from `image_brief.generation_contract.prompt`
- watermark: `true`

M0.6 也提供 `generic-http-image` 模板 provider，用于后续适配其他 HTTP 图片模型。视频 live 暂缓到 M0.7。

M0.6.1-M0.6.5 图片生成闭环：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 creative-run --id demo-product --artifact copy-pack-xxx --variant 1 --preset xiaohongshu-cover --provider generic --mode mock --count 2
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-qa --id demo-product --result image-result-xxx
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 comparison-package --id demo-product --job generation-job-xxx --job generation-job-yyy
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 result-feedback --id demo-product --result image-result-xxx --note "选择这张作为后续风格学习样本。" --selected --rating 5 --allow-evolve
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product
```

版本含义：

- M0.6.1 `creative-run`：从 copy pack 串起 image brief、provider payload、validation、generation job、review package、comparison package、manifest。
- M0.6.2 `image-qa`：检查真实图片文件存在、尺寸可读、比例是否偏离预期，并输出可审阅 QA。
- M0.6.3 `result-feedback -> evolve`：选中图片结果后生成 Product Brain 演进提案，但不自动 apply。
- M0.6.4 `comparison-package`：多图/多 job 对比包，方便人工选择最佳结果。
- M0.6.5 prompt adapter：为图片 provider 生成可追溯的 adapted prompt，同时保留 `base_prompt` 和 adapter 规则。

M0.6.6-M0.6.10 图片迭代闭环增强：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 creative-run --id demo-product --artifact copy-pack-xxx --variant 1 --preset xiaohongshu-cover --provider volcengine-ark-image --mode live --count 1
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 result-feedback --id demo-product --result image-result-xxx --note "主体清晰，风格更高级，减少画面内文字。" --selected --rating 5 --allow-evolve --subject-clarity 5 --product-recognizability 5 --composition 4 --style-fit 5 --copy-fit 4 --dislike-reason "avoid generated text"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product --apply proposal-xxx
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-generate --id demo-product --brief image-brief-xxx --provider volcengine-ark-image
```

版本含义：

- M0.6.6 `creative-run live`：一条命令串起真实图片生成、QA、review、manifest；不会自动修改 Product Brain。
- M0.6.7 `result-feedback`：新增结构化反馈维度：主体清晰度、产品识别度、构图、风格匹配、文案适配、不喜欢原因。
- M0.6.8 `evolve`：把结构化反馈拆到 `learning.image_generation_preferences`、`learning.successful_patterns`、`learning.failed_patterns`，仍需人工 apply。
- M0.6.9 prompt adapter：读取已经 apply 的 Product Brain 学习，把成功/失败模式带入下一轮图片 prompt。
- M0.6.10 多产品泛化验证：确认新产品拥有独立 Product State / Product Wiki，不依赖当前测试样例。

M0.6.6-M0.6.10 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_6_10.ps1 -ProductId demo-product -Artifact copy-pack-xxx
```

默认会真实调用图片生成 API 1 次，并在测试产品上 apply 一条演进提案，用来验证 Product Brain 学习会影响下一轮 prompt adapter。若只做非 live 检查，可加 `-SkipLive`。

M0.6.1-M0.6.5 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_6_5.ps1 -ProductId demo-product -Artifact copy-pack-xxx -LiveResult image-result-xxx
```

该验证默认复用已有 live 图片结果，`live_call_count = 0`，不会额外调用图片生成 API。

记录反馈：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 feedback --id demo-product --artifact copy-pack-xxx --note "更喜欢克制、高级、不要叫卖。" --selected
```

如果用户选择了具体版本，可以记录版本和评分：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 feedback --id demo-product --artifact copy-pack-xxx --note "这个版本最适合主图。" --selected --variant 1 --rating 5
```

创建或应用 Product Brain 更新提案：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product --apply proposal-xxx
```

## 一键验证

执行：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_2_5.ps1
```

通过标准：

- `success = true`
- `generation_method = llm`
- `llm_provider = deepseek`
- `llm_model = deepseek-v4-pro`
- `grounding_status = passed_lite_audit`
- `grounding_warning_count = 0`
- `product_brain_changed_by_generate = []`
- `variant_count = 3`

如果模型轻微扩写了未证实词，生成器会先做确定性的 grounding repair，再重新审核。修复记录会写入：

```text
grounding_audit.repairs
```

如果只想验证离线 fallback 链路，可加：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_2_5.ps1 -AllowFallback
```

M0.3 评估闭环验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_3.ps1
```

它会先生成一个真实 copy-pack，再执行 `product evaluate`，并确认评估过程没有修改 `structured/product_state.json`。

## 产物位置

每个产品的工作区在：

```text
.hermes/product_creative/products/<product_id>/
```

生成产物在：

```text
.hermes/product_creative/products/<product_id>/artifacts/copy/
```

核心产物是 `copy-pack-*.json`，用于后续：

- 文案版本优化
- 电商主图 prompt 生成
- 视频分镜 prompt 生成
- 用户反馈与 Product Brain 迭代

M0.3 评估产物在：

```text
.hermes/product_creative/products/<product_id>/artifacts/evaluations/
```

评估报告会检查：

- 结构完整度
- Product State 事实边界
- 电商主图文案可用性
- 图片 prompt 可用性
- 视频分镜完整度
- 是否需要人工修订

M0.4 标准化 brief 产物在：

```text
.hermes/product_creative/products/<product_id>/artifacts/image_briefs/
.hermes/product_creative/products/<product_id>/artifacts/video_scripts/
```

M0.4/M0.4.1 只生成 provider-agnostic brief，不直接调用外部生图/生视频模型。brief 里会包含：

- source artifact / source variant
- platform preset / channel / aspect ratio
- product name / selling points
- main image copy or storyboard
- source assets from Product State and manual `--asset`
- provider-agnostic generation contract
- grounding audit snapshot

M0.4 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_4.ps1 -ProductId demo-product -Artifact copy-pack-xxx
```

M0.4.1 平台预设与素材槽位验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_4_1.ps1 -ProductId demo-product -Artifact copy-pack-xxx
```

M0.5 provider payload 产物在：

```text
.hermes/product_creative/products/<product_id>/artifacts/provider_payloads/
```

每个 provider payload 都会同时输出：

- `.json`：机器可读、后续真实 provider adapter 使用
- `.md`：人类可读、便于检查 prompt / 分镜 / 参考素材

M0.5 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_5.ps1 -ProductId demo-product -Artifact copy-pack-xxx
```

M0.5.1 provider registry / validation / generation job 产物在：

```text
.hermes/product_creative/products/<product_id>/artifacts/provider_validations/
.hermes/product_creative/products/<product_id>/artifacts/generation_jobs/
.hermes/product_creative/products/<product_id>/artifacts/generated_images/
.hermes/product_creative/products/<product_id>/artifacts/generated_videos/
```

M0.5.1 新增的固定边界：

- provider registry 在插件内声明 provider 能力、支持类型、支持模式和 adapter contract。
- provider validation 检查 payload 是否适合某个 provider。
- generation job 记录一次准备生成的任务。
- mock result 只记录结果 schema 和占位说明，不生成真实图片/视频文件。
- `external_call_performed` 必须保持 `false`。

M0.5.1 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_5_1.ps1 -ProductId demo-product -Artifact copy-pack-xxx
```

M0.5.2-M0.5.5 产物治理层：

```text
.hermes/product_creative/products/<product_id>/artifacts/manifest.json
.hermes/product_creative/products/<product_id>/artifacts/manifest.jsonl
.hermes/product_creative/products/<product_id>/artifacts/review_packages/
.hermes/product_creative/products/<product_id>/artifacts/result_feedback/
.hermes/product_creative/products/<product_id>/artifacts/live_readiness/
```

版本含义：

- M0.5.2 `artifact-manifest`：统一索引 copy、evaluation、brief、payload、job、result、review、feedback、readiness。
- M0.5.3 `review-package`：把 generation job 关联的 product / brief / payload / result 打成可读审阅包。
- M0.5.4 `result-feedback`：记录生成结果反馈契约，不直接修改 Product Brain；视频阶段优先反馈脚本、分镜和 prompt，而不是围绕视频文件扩展后处理闭环。
- M0.5.5 `live-readiness`：检查 provider 是否具备 live 条件，但不调用真实外部 API。

M0.5.2-M0.5.5 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_5_5.ps1 -ProductId demo-product -Artifact copy-pack-xxx
```

M0.6 真实图片生成产物仍在：

```text
.hermes/product_creative/products/<product_id>/artifacts/generated_images/
```

live 图片结果会包含：

- downloaded image file
- `image-result-*.json`
- `image-result-*.md`
- `external_call_performed = true`
- `review.ready_for_feedback = true`

M0.6.1-M0.6.5 新增产物在：

```text
.hermes/product_creative/products/<product_id>/artifacts/creative_runs/
.hermes/product_creative/products/<product_id>/artifacts/image_qa/
.hermes/product_creative/products/<product_id>/artifacts/comparison_packages/
```

M0.6 真实图片链路验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m0_6_image_live.ps1 -ProductId demo-product -Artifact copy-pack-xxx
```

该验证会真实调用图片生成 API 1 次。若需要超过 5 次 live 调用，必须先说明原因并获得确认。

## 当前边界

M0.2-5 到 M0.5.5 只固化运行入口、文案闭环、brief、provider payload、provider registry、validation、mock job/result、manifest、review、result feedback contract、live readiness，不接入真实生图/生视频模型。

M0.6 只接入真实图片生成；视频生成仍保持非 live，等待 M0.7 补齐视频 task 查询与结果获取接口。

`generate` 只允许生成 artifact，不允许直接修改 Product Brain。Product Brain 更新仍必须走：

```text
feedback -> evolve -> apply
```

## M1 Canonical Product Brain

M1 的目标是把 M0.6 已跑通的产品生成闭环补上认知治理层，重点不是新增生成能力，而是防止 Product Brain 被测试产品、单次反馈或跨产品资料污染。

M1 新增命令：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 wiki-upgrade --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 wiki-lint --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 state-export --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 context --id demo-product
```

版本含义：

- `wiki-upgrade`：补齐 M1 Product Wiki 页面骨架，只写通用结构和占位符，不写任何测试产品卖点。
- `wiki-lint`：检查 frontmatter、product_id、sources、跨产品 id / workspace 引用。
- `state-export`：从当前产品 Wiki 导出 `structured/product_state.json`，并记录 `_export.source = product_wiki`。
- `context`：升级为读取更完整的 Product Brain 页面，并返回 `lint_summary` 与 `page_list`。

M1 新增 Wiki 页面骨架：

```text
product/Product.md
product/positioning.md
product/selling-points.md
product/brand-voice.md
product/visual-identity.md
channels/ecommerce.md
channels/ecommerce-main-image.md
content-patterns/visual-patterns.md
content-patterns/proven-patterns.md
content-patterns/failed-patterns.md
compliance/forbidden-claims.md
eval/content-quality-rubric.md
```

M1 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m1_canonical_brain.ps1
```

该验证会创建三个全新产品并确认：

- 页面结构一致。
- Wiki 不包含其他产品 id。
- 新产品 B/C 不包含测试产品 A 的关键词。
- `wiki-lint` 全部通过。
- `state-export` 只从当前产品 Wiki 导出。
- `context` 不返回其他产品内容。
- `live_call_count = 0`，不会调用真实图片 API。

M1.7-M1.12 Product Brain 硬化层：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 fingerprint --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 context --id demo-product --target image-generation
.\.hermes\plugins\product_creative\scripts\verify_m1_hardening.ps1
```

版本含义：

- M1.7 `evolve` typed proposal：每条更新都包含 `update_type`、`target_page`、`target_section`、`risk_level`、`source_ids` 和 `preview`。
- M1.8 source registry：产品输入、图片输入、用户反馈会登记到 `structured/source_index.jsonl`，演化学习必须能追溯证据。
- M1.9 `state-export` v2：导出的 Product State 保留旧字段，同时新增 `_provenance` 和 `_warnings`。
- M1.10 context pack policy：`context --target ...` 按任务读取不同 Product Wiki 页面，避免所有页面无差别塞进上下文。
- M1.11 product fingerprint guard：`fingerprint` 生成 `structured/product_fingerprint.json`，`wiki-lint` 会把跨产品 id / workspace 作为错误，把强指纹词命中作为 warning，避免同类产品实验被误伤。
- M1.12 hardening verification：创建多产品，验证 typed proposal、source registry、provenance、context profile 和跨产品 guard，全程 `live_call_count = 0`。

## M2 多渠道内容生成基础层

M2.1-M2.3 把 `generate` 从单一 `product-copy-pack` 扩展为多渠道目标，但仍然不接真实视频生成。

查看支持的生成目标：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 target-list
```

当前支持：

```text
product-copy-pack
ecommerce-main-image-copy
xiaohongshu-seeding-note
douyin-short-video-script
```

生成电商主图文案：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generate --id demo-product --target ecommerce-main-image-copy --variants 3
```

生成小红书种草文案：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generate --id demo-product --target xiaohongshu-seeding-note --variants 3
```

生成抖音短视频脚本草案：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generate --id demo-product --target douyin-short-video-script --variants 3
```

版本含义：

- M2.1 target registry：固定生成目标、context profile、artifact 类型、产物目录和是否允许进入反馈演化。
- M2.2 channel content artifact：新增 `artifacts/channel_content/`，渠道内容输出 JSON + Markdown，进入 artifact manifest。
- M2.3 context policy：不同渠道读取不同 Product Wiki 页面，避免所有渠道共用同一上下文。

M2.1-M2.3 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_channel_targets.ps1
```

该验证会禁用 LLM，使用 deterministic fallback 检查结构稳定性；不会调用真实图片或视频 API，`live_call_count = 0`。

M2.4-M2.6 渠道评估与反馈学习闭环：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 channel-evaluate --id demo-product --artifact xiaohongshu-note-xxx
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 channel-feedback --id demo-product --artifact xiaohongshu-note-xxx --variant 2 --selected --rating 5 --allow-evolve --note "标题不错，正文广告感再弱一点，更像真实分享。" --like-reason "真实分享语气" --dislike-reason "广告感偏强" --channel-fit 5 --factuality 5 --tone-fit 5 --actionability 4
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product --apply proposal-xxx
```

版本含义：

- M2.4 `channel-evaluate`：按渠道评估 `channel_content`，输出 `artifacts/channel_evaluations/`，不修改 Product Brain。
- M2.5 `channel-feedback`：记录用户对渠道内容和具体 variant 的反馈，输出 `artifacts/channel_feedback/`。
- M2.6 `evolve`：把已选择且允许演化的渠道反馈转为 typed proposal；apply 后写入 `learning.channel_preferences`、成功/失败模式和对应 Wiki 页面。

M2.4-M2.6 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_channel_learning.ps1
```

该验证会跑通 `generate -> channel-evaluate -> channel-feedback -> evolve -> apply -> regenerate`，确认下一轮同渠道生成能吸收已确认渠道偏好；全程 `live_call_count = 0`。

M2.7 渠道审阅包：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 channel-review-package --id demo-product --artifact xiaohongshu-note-xxx
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 channel-review-package --id demo-product --artifact xiaohongshu-note-xxx --evaluation channel-eval-xxx
```

版本含义：

- M2.7 `channel-review-package`：把 `channel_content` 与可选/自动匹配的 `channel_evaluation` 合并为人工审阅包，输出 `artifacts/channel_review_packages/`。
- 审阅包包含多版本摘要、评分/推荐、最佳候选、人工审阅清单和 `channel-feedback` 命令模板。
- 该命令不修改 Product Brain；只有用户后续执行 `channel-feedback --allow-evolve` 并确认 `evolve --apply` 后，渠道偏好才会进入 Product Brain。

M2.7 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_channel_review_package.ps1
```

该验证会跑通 `generate -> channel-evaluate -> channel-review-package -> artifact-manifest`，确认审阅包能自动挂接最新渠道评估、进入 manifest，并且 Product State hash 不变化；全程 `live_call_count = 0`。

M2.8-M2.8.2 一键渠道审阅 run：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 channel-review-run --id demo-product --target xiaohongshu-seeding-note --variants 3
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 channel-review-run --id demo-product --target douyin-short-video-script --variants 3
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 channel-review-run --id demo-product --target ecommerce-main-image-copy --variants 3
```

版本含义：

- M2.8 `channel-review-run`：把 `generate -> channel-evaluate -> channel-review-package -> artifact-manifest` 封装成一次可重复的渠道审阅流水线。
- M2.8.1 run artifact/index：输出 `artifacts/channel_review_runs/` 和 `structured/channel_review_run_index.jsonl`，记录每次渠道实验的链路、best variant、相关产物路径。
- M2.8.2 structured next actions：`channel_review_package` 和 `channel_review_run` 都包含结构化 `next_actions.record_selected_feedback`，后续 UI 或 agent 可以直接读取下一步反馈命令，不需要解析 Markdown。
- 该命令不修改 Product Brain；Product Brain 仍只会在用户执行 `channel-feedback --allow-evolve`、再人工确认 `evolve --apply` 后更新。

M2.8 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_channel_review_run.ps1
```

该验证会跑通一键渠道审阅 run，确认 run artifact、review package、structured next actions、manifest 和 Product State 不变性；全程 `live_call_count = 0`。

M2.9 Workflow State / Agent Operating Contract：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-status --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-next --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-summary --id demo-product
```

版本含义：

- M2.9 `workflow-status`：从 Product State、source index、channel review runs、feedback、proposal 推导当前工作流状态，不新增独立状态库。
- M2.9 `workflow-next`：返回推荐下一步动作、命令模板、是否需要用户输入、是否需要明确确认、是否会修改 Product Brain。
- M2.9 `workflow-summary`：给 Hermes agent / CLI / 未来 UI 一个紧凑摘要，用于对话接续和人工交接。
- M2.9 不新增生成能力，也不自动学习；它是智能体执行前的操作契约层。

状态枚举：

```text
no_product
product_initialized
ready_for_channel_run
channel_run_ready_for_review
feedback_recorded
proposal_ready_for_confirmation
brain_updated
```

安全约束：

- `workflow-status / workflow-next / workflow-summary` 永不修改 Product Brain。
- `channel-feedback` 只记录反馈，不修改 Product Brain。
- `evolve` 只创建 proposal，不修改 Product Brain。
- 只有 `evolve --apply proposal-xxx` 会修改 Product Brain，且必须用户明确确认。

M2.9 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_contract.ps1
```

该验证会从 `no_product -> product_initialized -> ready_for_channel_run -> channel_run_ready_for_review -> feedback_recorded -> proposal_ready_for_confirmation -> brain_updated` 跑完整状态链路，并确认只读状态命令不改变 Product State；全程 `live_call_count = 0`。

M2.10 Agent Action Guard / Confirmation Guard：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 action-guard --id demo-product --action run_channel_review
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 action-guard --id demo-product --action apply_evolution_proposal --proposal proposal-xxx
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 action-guard --id demo-product --action apply_evolution_proposal --proposal proposal-xxx --confirmed
```

版本含义：

- M2.10 `action-guard`：在执行具体动作前，检查该动作是否符合当前 workflow 状态。
- 它只读，不执行动作，不写 artifact，不修改 Product Brain。
- 它区分 `writes_product_workspace` 与 `mutates_confirmed_product_brain`：生成 run、记录反馈、创建 proposal 会写入 workspace 证据，但不会修改已确认 Product Brain 学习；`apply_evolution_proposal` 才会修改已确认 Product Brain 学习。
- `apply_evolution_proposal` 必须满足：当前状态为 `proposal_ready_for_confirmation`、proposal id 匹配最新 proposed proposal、并且传入 `--confirmed`。
- 后续 Hermes 对话入口、CLI 自动下一步、Web UI 按钮都应先调用 `action-guard`，再执行具体命令。

M2.10 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_action_guard.ps1
```

该验证会确认：错误状态下动作被 blocked，run/feedback/proposal 前置条件正确，未确认或 proposal id 不匹配时禁止 apply，确认且匹配时才允许 apply；全程 `live_call_count = 0`。

M2.11 Workflow Execution Plan：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-plan --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-plan --id demo-product --action run_channel_review --target xiaohongshu-seeding-note --variants 3
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-plan --id demo-product --action apply_evolution_proposal --proposal proposal-xxx --confirmed
```

版本含义：

- M2.11 `workflow-plan`：把 M2.9 的状态判断和 M2.10 的 action guard 合并成结构化执行计划。
- 输出包含 `plan_id`、`workflow_status`、`recommended_action`、`guard_result`、`steps`、`tool`、`args_template`、`missing_inputs`。
- 它只生成计划，不执行任何工具，不写 artifact，不修改 Product Brain。
- 后续 agent / UI 应读取 `ready_to_execute` 与 `steps[0].tool + steps[0].args_template`，再决定是否调用真实工具。

M2.12 Conversation Adapter：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 conversation-adapter --id demo-product --message "帮我生成小红书种草文案"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 conversation-adapter --id demo-product --message "我喜欢第2版，但广告感弱一点"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 conversation-adapter --id demo-product --message "确认应用这个 proposal" --proposal proposal-xxx
```

版本含义：

- M2.12 `conversation-adapter`：把用户话语映射到 workflow action、target、confirmation intent，然后调用 `workflow-plan` 生成执行计划。
- 它不是自由聊天引擎，不直接执行工具，不自动 apply Product Brain。
- 它会返回 `interpreted_intent`、`plan`、`agent_reply`、`executes_tools=false`、`mutates_product_brain=false`。
- 后续真正的 Hermes 对话入口应先调用 `conversation-adapter`，再根据 plan 和 action-guard 决定是否执行工具。

M2.11-M2.12 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_agent_plan_adapter.ps1
```

该验证会确认：workflow-plan 可生成 guarded tool invocation contract，conversation-adapter 可从用户消息推导 target/action/confirmation，且二者都不直接执行工具或修改 Product State；全程 `live_call_count = 0`。

M2.13 Supervised Workflow Execute：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --action create_product --name "周十五蜂蜜露"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --action ingest_product_source --text "周十五蜂蜜露，适合..."
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --message "帮我生成小红书种草文案" --variants 3
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --message "我喜欢第1版，但广告感弱一点"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-execute --id demo-product --action apply_evolution_proposal --proposal proposal-xxx --confirmed
```

版本含义：

- M2.13 `workflow-execute`：消费 `workflow-plan` / `conversation-adapter` 的结果，只执行一个 `ready_to_execute` step。
- 如果缺少 `target`、`name`、`text`、`note` 等必要输入，它返回 `executed=false`，不会调用底层工具。
- 如果执行 `apply_evolution_proposal` 且没有 `--confirmed`，它返回 `blocked_for_confirmation`，不会修改 Product Brain。
- 它是对话式 Hermes 入口的执行层雏形：用户话语先解释成 plan，再由 executor 执行受 guard 保护的一步。
- 它不是无限自动循环，也不会绕过人工确认。

M2.13 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_execute.ps1
```

该验证会确认：executor 可串起 create / ingest / 对话生成 / 对话反馈 / proposal / 确认 apply；未确认 apply 不执行且 Product State hash 不变；全程 `live_call_count = 0`。

M2.14 Material Library / Visual Source Registry：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 asset-register --id demo-product --path C:\path\to\main-image.png --role current_main_image --description "当前产品主图" --usage product_reference --usage video_first_frame
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 asset-list --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 material-manifest --id demo-product
```

版本含义：

- M2.14 把用户上传图片从普通路径升级成 Product Material Library 里的素材资产。
- 素材角色包括 `current_main_image`、`product_photo`、`detail_image`、`style_reference`、`video_first_frame`、`generated_candidate`、`reference_image`。
- 注册素材会复制文件到 `assets/images/`，生成 `artifacts/material_assets/`，登记 `structured/source_index.jsonl`，并在 Product State 的 `assets.materials` 里留下素材引用。
- 注册素材不代表系统已经理解图片内容，也不会把视觉结论写入 Product Brain。

M2.15 Image Understanding Contract：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-analyze --id demo-product --asset material-xxx
```

版本含义：

- M2.15 建立主图解析 artifact 的稳定数据契约，输出 `artifacts/image_analysis/`。
- 当前默认 provider 是 `mock-vision`，只做本地元数据与 schema 固化，不调用真实多模态模型，`external_call_performed=false`。
- 解析结果会说明哪些字段还未经过 OCR/VLM 验证，且 `direct_write_to_product_brain=false`。
- 后续 M2.16 才会基于 image analysis 生成 Visual Brain proposal，并由用户确认后写入 Product Brain。

M2.14-M2.15 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_visual_materials.ps1
```

该验证会确认：主图可注册为 `current_main_image`，素材库 manifest 与 Product State 引用正确，`image-analyze` 生成只读视觉解析 artifact，且解析过程不改变 Product State；全程 `live_call_count = 0`。

M2.16 Visual Alignment / Visual Brain Proposal：

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 visual-align --id demo-product --analysis image-analysis-xxx --note "这张图后续优先作为图生视频首帧参考。"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id demo-product --apply proposal-xxx
```

版本含义：

- M2.16 `visual-align`：把 `image_analysis` 与当前 Product Brain / Product State 做对齐，输出 `artifacts/visual_alignments/`。
- `visual-align` 不直接写 Product Brain；它只生成 `eligible_for_evolution_proposal` 和 `proposed_learning`。
- `evolve` 现在可以把最新合格的 visual alignment 转成 Product Brain proposal。
- 视觉学习写入仍必须人工确认 `evolve --apply proposal-xxx`。
- 当前 mock-vision 下，visual alignment 只允许沉淀“素材可作为视觉参考/首帧参考”这类保守学习，不允许从图片推断包装文字、成分、认证或功效。

M2.16 验证：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_visual_alignment.ps1
```

该验证会确认：`visual-align` 生成只读视觉对齐 artifact，Product State 在 align 阶段不变化，artifact manifest 可索引 visual alignment，`evolve` 能生成视觉 proposal，确认 apply 后才把视觉参考偏好写入 Product Brain；全程 `live_call_count = 0`。
