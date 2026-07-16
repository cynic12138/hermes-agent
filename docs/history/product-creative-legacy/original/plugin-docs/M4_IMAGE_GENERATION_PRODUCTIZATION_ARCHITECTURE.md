# M4 Image Generation Productization Architecture

状态：M4.1-M4.9 已落地；M4.9 已通过项目内 Hermes chat 对话验证  
创建日期：2026-07-07  
适用范围：`product_creative` 插件 M4 大版本开发  

本文档用于固定 M4 的开发方向。M4 开发开始前，必须先确认本文档；后续 M4.x 小版本开发和验收都应对齐本文档。

当前实现摘要：

```text
已新增 image_generation.py。
已新增 CLI / Hermes tools：image-intent、image-brief、image-brief-review、image-brief-revise、batch-policy、image-provider-payload、image-run、selected-image-asset。
已接入 workflow / conversation / workflow-run。
已新增 product_workspace_resolve，支持 Hermes 按用户可见产品名定位 product_id。
workflow / tool 返回新增 user_next_message，用于自然语言引导用户继续反馈或确认。
已新增 verify_m4_image_productization_loop.ps1 综合验收脚本。
默认验证不调用外部模型，live_call_count = 0。
批量生成采用 batch generation policy，不要求用户逐张确认 brief。
生成图默认回收为 generated_candidate，不自动成为 current_main_image。
Product Brain 学习仍必须 proposal / apply，M4 默认验证确认未绕过 apply 写入 image_generation_preferences。
```

---

## 1. M4 的核心判断

M4 不是“第一次接入图片生成模型”。

当前系统已经具备以下基础：

```text
M0.6：已有 image brief -> provider payload -> generation job -> image result -> QA / review / feedback 的基础链路。
M2：已有主图注册、图片理解、visual-align、安全学习门禁。
M3：已有素材卡片、Material Library Map、Task Material Pack，让 Hermes 能读取当前产品已有素材。
```

因此 M4 的主线应是：

```text
把已跑通的图片生成能力产品化，让 Hermes 能从产品认知和素材库出发，稳定生成、审阅、选择、登记并学习图片结果。
```

一句话：

```text
M4 的目标不是“多生成几张图”，而是让每一次生图都成为当前产品认知闭环的一部分。
```

---

## 2. M4 与最终产品目标的关系

最终产品目标仍然是：

```text
围绕单一产品 / 单一主题持续理解、生成内容、接收反馈，并让下一次文案 / 图片 / 视频更贴合该产品。
```

M4 对这个目标的贡献：

```text
Product Brain 提供产品事实、卖点、风格、渠道规则。
M3 Material Pack 提供本次任务可用的主图、参考图、素材理解和使用偏好。
M4 Image Brief 把产品认知和素材转成可确认的图片生成意图。
Provider Payload 把确认后的图片意图转成外部模型可执行请求。
Image Result 保存真实或 mock 生成结果。
Review / Comparison 让用户选择更符合产品的版本。
Feedback / Proposal 把选择原因沉淀为 visual identity、ecommerce playbook、image generation preferences。
Selected Image Registration 把优秀生成图重新登记进素材库，成为后续文案、图片、视频任务的参考素材。
```

这条链路让图片生成不再是一次性输出，而是：

```text
图片生成 -> 用户选择 -> 产品视觉偏好学习 -> 生成图回到素材库 -> 下一次生成更准确
```

---

## 3. M4 范围

### 3.1 M4 必须做

```text
图片任务意图解析与 workflow action。
基于 Product Brain + M3 Task Material Pack 生成 image brief。
image brief 的审阅、修改、确认门禁。
provider payload 的图片生成适配加固。
mock / dry-run / live 三种模式边界明确。
多版本图片生成和 comparison package。
图片结果 QA 与 review package。
用户选择与结构化反馈。
反馈生成可确认的 Product Brain evolution proposal。
被选中生成图登记回素材库。
workflow-run 可推进安全步骤，并在真实外部调用、认知写入前停住。
```

### 3.2 M4 不做

```text
不做视频生成执行。
不做视频结果下载、轮询、QA。
不建设 Web / Desktop UI。
不做复杂向量数据库。
不做跨产品素材检索。
不做大规模 provider marketplace。
不自动写入 Product Brain。
不默认调用真实外部模型。
不以模型生成质量评分取代人工选择。
```

### 3.3 M4 的安全边界

```text
live 图片生成必须显式确认。
Product Brain 写入必须 proposal / apply 且显式确认。
mock / dry-run 可用于默认验证。
生成图默认只是 candidate，不能自动成为 current_main_image。
素材登记可自动保存 artifact，但成为核心视觉参考需要用户确认。
图片 QA 只做工程可检查项，不能假装理解商业审美。
```

---

## 4. 当前已有能力盘点

### 4.1 Provider 层

当前已有 provider：

```text
generic：mock provider，支持 image / video dry-run 和 mock。
mock-image：图片 mock provider。
generic-http-image：通用 HTTP 图片 provider 模板。
volcengine-ark-image：豆包 Seedream 图片生成 provider，支持 live。
volcengine-ark-vlm：豆包多模态图片理解 provider，已在 M2.30 使用。
volcengine-ark-video：视频 provider，占位在 M2 视频 payload 链路，不属于 M4 主线。
```

M4 默认图片 live provider：

```text
volcengine-ark-image
```

M4 保留通用适配边界：

```text
generic-http-image
```

### 4.2 已有图片生成链路

当前已有函数/能力：

```text
prepare_provider_payload(product_id, brief, provider, "image")
validate_provider_payload(product_id, payload, provider)
check_live_readiness(product_id, provider, "image", payload)
create_generation_job(product_id, payload, provider, mode)
create_creative_run(product_id, artifact, variant, preset, provider, mode, count)
qa_image_result(product_id, result)
create_review_package(product_id, job)
create_comparison_package(product_id, jobs)
record_result_feedback(product_id, result, note, selected, rating, allow_evolve, quality_scores)
```

这些能力可以继续使用，M4 重点补足：

```text
更清晰的 image workflow action。
图片 brief 的确认态。
M3 task material pack 到 image brief / provider payload 的显式追踪。
生成结果回到素材库的登记链路。
面向用户自然语言目标的 workflow-run 编排。
M4 验收脚本与路线门禁。
```

---

## 5. M4 目标架构

```text
User Message
  -> Hermes workflow conversation adapter
  -> image generation intent
  -> Product Brain read
  -> M3 Task Material Pack read
  -> Image Brief Draft
  -> Image Brief Review Package
  -> Human confirm / revise
  -> Provider Payload
  -> Provider Validation
  -> Live Readiness
  -> Human confirm external call
  -> Generation Job
  -> Image Result
  -> Image QA
  -> Review / Comparison Package
  -> User selection / feedback
  -> Evolution Proposal
  -> Human apply
  -> Product Brain learning update
  -> Selected Image registered as Material Asset
```

Hermes 在这条链路中的角色：

```text
读取 Product Brain，而不是凭空创作。
读取素材卡片，而不是要求用户每次手动指定图片。
生成可审阅的 brief，而不是直接调用模型。
在安全步骤中自动推进。
在真实外部调用、Product Brain 写入、核心素材替换前停住等待确认。
```

---

## 6. M4 数据与文件结构

M4 应继续沿用现有产品目录：

```text
.hermes/product_creative/products/<product-id>/
```

M4 主要新增或强化的 artifact：

```text
artifacts/image_intents/<image-intent-id>.json
artifacts/image_intents/<image-intent-id>.md

artifacts/image_brief_reviews/<review-id>.json
artifacts/image_brief_reviews/<review-id>.md

artifacts/image_brief_patches/<patch-id>.json
artifacts/image_brief_patches/<patch-id>.md

artifacts/provider_payloads/<payload-id>.json
artifacts/provider_payloads/<payload-id>.md

artifacts/generation_jobs/<job-id>.json

artifacts/generated_images/<result-id>.json
artifacts/generated_images/<image-file>

artifacts/image_qa/<qa-id>.json
artifacts/review_packages/<review-package-id>.json
artifacts/comparison_packages/<comparison-package-id>.json
artifacts/result_feedback/<feedback-id>.json

artifacts/material_assets/<generated-material-id>.json
artifacts/material_cards/<generated-material-id>.json
```

M4 应补充或强化的结构化索引：

```text
structured/image_intent_index.jsonl
structured/image_brief_review_index.jsonl
structured/image_brief_patch_index.jsonl
structured/creative_run_index.jsonl
structured/result_feedback.jsonl
structured/material_assets_index.jsonl
structured/material_usage.jsonl
```

M4 不应创建独立于 Product Brain 的第二套长期认知系统。长期学习仍进入：

```text
Product Brain / Product State
learning.image_generation_preferences
learning.visual_identity_preferences
channel_playbooks.ecommerce
assets.materials
```

---

## 7. M4 用户体验目标

### 7.1 无需手动指定素材的常规路径

用户说：

```text
帮周十五蜂蜜露生成 3 张电商主图。
```

Hermes 应执行：

```text
1. 读取 Product Brain。
2. 读取 Material Library Map。
3. 为 image_brief / ecommerce 准备 task material pack。
4. 生成 image intent。
5. 生成 image brief draft。
6. 生成 image brief review package。
7. 停下，请用户确认或修改 brief。
```

用户确认后：

```text
8. 生成 provider payload。
9. 校验 provider payload。
10. 检查 live readiness。
11. 如果是 live，停下请求外部调用确认。
12. 生成 3 张图片。
13. 生成 QA、review package、comparison package。
14. 用户选择最佳版本并反馈原因。
15. 生成 Product Brain evolution proposal。
16. 用户确认 apply。
17. 被选图片登记为 generated_candidate；如果用户进一步确认，可升级为 current_main_image。
```

### 7.2 用户上传一张新主图后生成

用户说：

```text
用这张主图为基础，给我生成 3 张小红书封面图。
```

Hermes 应执行：

```text
1. 注册本地主图为 material asset。
2. 默认使用 mock-vision 分析；若用户确认，可用 volcengine-ark-vlm 真实分析。
3. visual-align 生成可审阅视觉对齐产物。
4. rebuild material cards。
5. 准备 image_brief task material pack。
6. 进入 M4 image brief review / confirm / generation 链路。
```

### 7.3 用户只给一个短目标

用户说：

```text
今天出一张更高级感的产品图。
```

Hermes 应执行：

```text
1. 判断这是 image generation intent。
2. 从 Product Brain 中读取品牌调性、禁用表达、已确认偏好。
3. 从素材库找当前可作为视觉参考的主图/包装图。
4. 如果素材不足，先提示缺少视觉参考；可继续做纯文生图 brief，但标记 grounding 风险。
5. 生成 image brief review package，并说明素材依据和风险。
```

---

## 8. Image Brief 确认机制

M4 必须补齐图片 brief 的确认态，但确认机制不能设计成“每张图片都让用户确认一次”。原因是：

```text
图片生成的错误成本高于普通文案。
图片 prompt 会把 Product Brain、素材理解、卖点和风格压缩成模型指令。
如果 brief 未确认就 live 生成，会把“理解偏差”放大成实际图片成本。
但后续批量生成图片 / 视频时，如果每个结果都要求人工确认 brief，会让用户工作量过大。
```

M4 推荐状态流：

```text
draft
  -> ready_for_human_review
  -> revision_requested
  -> confirmed_for_provider_payload
```

规则：

```text
dry-run / mock 可基于 draft 执行，用于开发和预览。
单次 live provider payload 默认应来自 confirmed_for_provider_payload 的 brief。
用户修改 brief 后应保留 patch artifact，而不是覆盖原始 brief。
确认后的 revised brief 应记录 source_brief_id、patch_id、confirmed_at。
```

批量生成时，M4 不采用“逐张确认 brief”，而采用“确认生成策略”的方式：

```text
用户确认一份 batch generation policy。
该 policy 约束产品、渠道、素材范围、风格边界、数量上限、provider、预算/调用上限、禁止表达。
同一批次内的多个 image brief / prompt variation 可由 Hermes 自动派生。
Hermes 必须保存每个派生 brief，但不要求用户逐个确认。
一旦派生 brief 超出 policy 边界，workflow 必须停止并请求重新确认。
```

批量确认推荐分层：

```text
低风险：同一产品、同一渠道、同一素材包、同一风格方向，只做 3-5 个 prompt variation，可用一次 batch policy 确认。
中风险：同一产品但跨渠道 / 大幅改变风格，需要确认新的 batch policy。
高风险：更改产品事实、核心包装、功效承诺、外部真实调用预算、主图身份升级，必须单独确认。
```

该策略的目标：

```text
保护 Product Brain 和外部调用成本，同时不让用户在批量生产中被确认流程淹没。
```

---

## 9. Provider 接入策略

M4 的 provider 策略：

```text
默认 mock：generic 或 mock-image。
默认 live：volcengine-ark-image。
通用扩展：generic-http-image。
```

M4 不需要新增大量 provider。更重要的是统一 provider contract：

```text
输入：confirmed image brief。
输出：provider payload。
校验：provider validation。
执行前：live readiness。
执行后：normalized image result。
```

M4 对真实调用的要求：

```text
必须显式确认。
必须记录 external_call_performed。
必须记录 provider、model、payload、result。
最多生成 5 张。
默认验证不调用 live。
live 验证只在用户确认时进行，建议每轮最多 1-2 次。
```

---

## 10. 结果反馈与 Product Brain 学习

M4 的学习目标不是简单保存“喜欢/不喜欢”，而是沉淀：

```text
什么样的图片结构更能代表当前产品。
什么样的文字覆盖适合当前渠道。
什么样的构图、色彩、场景、包装呈现更适合当前产品。
哪些视觉方向会降低产品识别度或偏离品牌。
```

反馈字段应优先使用现有维度：

```text
subject_clarity
product_recognizability
composition
style_fit
copy_fit
```

反馈进入学习的规则：

```text
只有 selected=true 且 allow_evolve=true 的结果，才有资格生成 evolution proposal。
proposal 必须人工 apply。
未确认反馈只作为本地证据，不改 Product Brain。
```

学习建议落点：

```text
learning.image_generation_preferences
learning.visual_identity_preferences
channel_playbooks.ecommerce
channel_playbooks.xiaohongshu
assets.materials[].usage_notes
```

---

## 11. 生成图回到素材库

M4 必须让优秀生成图回到 M3 素材库，否则生图结果无法参与未来迭代。

默认登记规则：

```text
被选中生成图 -> role=generated_candidate
usage=image_reference, ecommerce_reference
source_result_id=<result-id>
source_job_id=<job-id>
source_provider=<provider>
```

升级规则：

```text
generated_candidate -> current_main_image
```

必须由用户显式确认。

登记后应触发：

```text
material-card-rebuild
material-library-map
```

可选触发：

```text
image-analyze
visual-align
```

注意：生成图并不自动代表产品真实外观。除非用户确认它可以作为产品视觉参考，否则只能作为创意候选图。

---

## 12. Hermes Workflow Actions

M4 推荐新增或强化以下 workflow actions：

```text
resolve_image_intent
prepare_image_material_pack
create_image_brief
review_image_brief
revise_image_brief
build_image_provider_payload
check_image_live_readiness
submit_image_generation_job
review_image_results
record_image_result_feedback
register_selected_image_asset
```

其中可自动执行的安全步骤：

```text
resolve_image_intent
prepare_image_material_pack
create_image_brief
review_image_brief
build_image_provider_payload（仅 confirmed brief 后）
check_image_live_readiness
review_image_results
```

必须停下等待用户的步骤：

```text
revise_image_brief：单次生成需要确认 brief；批量生成需要确认 batch generation policy。
submit_image_generation_job：live 模式需要确认外部调用或已存在有效 batch execution approval。
record_image_result_feedback：需要用户选择/评分/文字反馈。
register_selected_image_asset：升级为 current_main_image 需要确认。
apply_evolution_proposal：需要确认写入 Product Brain。
```

---

## 13. M4 小版本路线

### M4.0 架构确认

目标：

```text
确认 M4 的主线、边界、数据结构、workflow 方向和验收标准。
```

产物：

```text
M4_IMAGE_GENERATION_PRODUCTIZATION_ARCHITECTURE.md
PRODUCT_MAINLINE_ROADMAP.md 更新 M4 入口说明
```

验收：

```text
用户确认 M4 方向。
确认 M4 不提前做视频执行。
确认 M4 聚焦图片生成产品化和学习闭环。
```

### M4.1 Image Intent 与用户目标解析

目标：

```text
让 Hermes 能从自然语言识别图片生成任务，而不是只靠脚本参数。
```

开发内容：

```text
新增 image intent artifact。
conversation adapter 支持“生成主图 / 封面图 / 小红书图 / 高级感产品图”等意图。
intent 中记录 channel、style_hint、count、asset_policy、risk_notes。
workflow-next 能推荐图片生成链路。
```

验收：

```text
用户说“帮这个产品生成 3 张电商主图”，系统能产出 image intent。
不调用外部模型。
不修改 Product Brain。
```

### M4.2 Image Brief Review / Patch / Confirm

目标：

```text
补齐图片 brief 的人工确认门禁。
```

开发内容：

```text
新增 image brief review package。
新增 image brief patch。
新增 image brief revise/confirm。
confirmed brief 才允许进入 live provider payload。
```

验收：

```text
能读取 image brief。
能生成可编辑 patch。
用户确认后生成 revised image brief。
live payload 对未确认 brief 阻断。
```

### M4.3 M3 Material Pack 与 Image Brief 深度衔接

目标：

```text
让图片 brief 明确说明用了哪些素材、为什么用、哪些不能当事实。
```

开发内容：

```text
image intent / image brief 自动准备或读取 task material pack。
brief 中写入 selected_material_cards。
provider prompt 中加入素材 grounding 摘要。
记录 material usage：task=image_generation 或 image_brief。
```

验收：

```text
不手动传 asset 的情况下，image brief 能引用 M3 task material pack。
material_usage 能记录本次图片生成使用过的素材。
```

### M4.4 Image Provider Payload Gate

目标：

```text
加固图片 provider payload，确保 live 生图前有可解释、可检查的请求。
```

开发内容：

```text
build_image_provider_payload workflow action。
provider validation 针对 confirmed image brief 给出清晰错误/警告。
live readiness 检查 provider key、endpoint、model、prompt、mode。
workflow-run 在 live 调用前停住。
```

验收：

```text
mock/dry-run 可默认通过。
live 无 key 或 brief 未确认时阻断。
外部调用前必须 explicit confirmation。
```

### M4.5 Multi-Variant Image Run

目标：

```text
把多版本图片生成作为稳定的产品动作。
```

开发内容：

```text
复用或增强 creative-run。
支持 count 1-5。
每张图产生 job/result/review/QA。
多张图自动产生 comparison package。
记录 run-level manifest。
```

验收：

```text
mock 模式可生成 3 个候选。
live 模式最多 5 个候选。
comparison package 列出所有候选、结果路径、provider、mode。
```

### M4.6 Image Result Feedback to Proposal

目标：

```text
让用户对图片结果的选择能转成可确认学习。
```

开发内容：

```text
强化 record_image_result_feedback workflow action。
支持 selected、rating、quality_scores、like/dislike reasons。
evolve 能从图片结果反馈生成 proposal。
proposal 指向 visual identity / image generation preferences / channel playbook。
```

验收：

```text
用户选择一张图并允许 evolve 后，系统生成 proposal。
未 apply 前 Product Brain 不变。
apply 后下一轮 brief 能读取偏好。
```

### M4.7 Selected Image Asset Registration

目标：

```text
让被选中图片进入素材库，成为后续生成可读取的素材。
```

开发内容：

```text
新增 register_selected_image_asset workflow action。
默认 role=generated_candidate。
可选择 human confirmed 后升级为 current_main_image。
登记后重建 material cards / library map。
```

验收：

```text
被选 result 能登记为 material asset。
M3 material-card-rebuild 能读取该 generated asset。
下一次 task material pack 能选择它。
```

### M4.8 M4 综合验收与 M5 入口检查

目标：

```text
确认 M4 图片生成闭环可用，且没有偏离最终主线。
```

开发内容：

```text
新增 verify_m4_image_productization_loop.ps1。
覆盖 intent -> material pack -> brief -> review -> confirm -> payload -> mock generation -> comparison -> feedback -> proposal -> selected asset registration。
可选 live 验证脚本单独存在，不默认调用。
更新 roadmap 状态。
```

验收：

```text
默认回归不调用外部模型。
Product Brain 写入仍需人工确认。
生成图片能成为素材库候选。
下一轮 image brief 能读取上轮反馈和生成素材。
```

### M4.9 Hermes 对话入口产品化

状态：已完成，并通过项目内 Hermes chat 验证。

目标：

```text
把 M4 图片生成产品化能力从脚本验证收口到 Hermes chat / Agent 对话验证。
```

开发内容：

```text
新增 product_workspace_resolve，用于按产品名/别名定位产品工作区。
product_workflow_run 支持 product_query，但优先建议 Agent 先调用 product_workspace_resolve。
workflow-next / workflow-plan / workflow-run 返回 user_next_message。
conversation adapter 能把用户自然语言反馈解析为 variant、rating、selected、allow_evolve。
新增 start_hermes_product_creative_dev.ps1，临时启用项目插件并启动 Hermes chat。
新增 Hermes Desktop 审阅说明，明确 Desktop 只作为临时 UI / 对话审阅入口。
新增 verify_m4_9_hermes_conversation_entry.ps1 默认回归。
```

验收：

```text
用户不需要记 product_id 时，Hermes 能先解析产品。
用户可以自然语言补充资料、生成内容、选择版本、评分和表达偏好。
反馈可以生成 evolution proposal。
Product Brain apply 必须停下等待明确确认。
工具输出中 user_next_message 是面向用户的下一步，command/developer_command 只是诊断信息。
```

---

## 14. M4 验证策略

### 14.1 默认验证

默认验证必须：

```text
不调用真实外部模型。
不消耗 API 费用。
不修改已确认 Product Brain，除非测试中显式 apply 到隔离测试产品。
可重复运行。
```

建议脚本：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m4_image_productization_loop.ps1
```

### 14.2 可选 live 验证

live 验证必须：

```text
开发中如确有必要，可调用真实豆包图片生成模型验证。
调用次数默认 1-2 次。
最多不超过 5 次。
记录 external_call_performed=true。
保存真实图片文件和 result artifact。
```

建议脚本：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m4_image_live.ps1
```

### 14.3 回归验证

M4 完成后至少回归：

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m3_asset_library_loop.ps1
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_run.ps1
.\.hermes\plugins\product_creative\scripts\verify_m0_6_10.ps1 -SkipLive
```

### 14.4 Hermes Desktop 临时 UI / 测试入口

M4 暂不开发新的 Web / Desktop UI。当前阶段优先验证项目内 Hermes chat / Agent 对话入口能否触发 `product_creative` workflow；Hermes Desktop 可以作为后续临时 UI / 对话测试入口，但不是进入下一阶段的前置条件。

本机 Hermes Desktop 路径：

```text
C:\Users\1\AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked
```

边界：

```text
M4 不把 UI 开发作为目标。
Hermes chat / Agent 对话触发是主验收入口。
Hermes Desktop 只作为可选 UI 入口，用于验证同一套 workflow / conversation / tool 调用体验。
脚本只作为诊断、回归和人工兜底入口。
artifact 仍是审计证据，但不能替代对话入口验收。
```

---

## 15. 进入 M5 的条件

只有满足以下条件，才进入 M5 视频生成执行：

```text
用户可以通过 Hermes chat / Agent 对话自然语言启动图片生成链路。
Hermes 对话模型能看到并调用 product_workflow_run，而不是只返回自由文本。
Hermes 能自动读取 Product Brain 和 M3 素材包。
图片 brief 有 review / patch / confirmed 状态，或批量生成时有 batch generation policy。
live 图片生成前有 readiness 和 explicit confirmation / batch execution approval。
多版本结果有 comparison package。
用户选择能形成 result feedback。
反馈能生成 proposal，且 Product Brain 写入仍需人工 apply。
被选生成图能登记回素材库。
下一轮 image brief 能读取上轮学习和生成素材。
默认验证不调用外部模型。
```

如果这些条件未满足，不进入 M5。

原因：

```text
视频生成依赖更稳定的视觉素材、图片 prompt、产品视觉偏好和素材回收机制。
M4 没收口就进入 M5，会让视频链路依赖不稳定的图片资产和不成熟的视觉学习。
```

---

## 16. 关键决策确认状态

### 16.1 M4 默认 live provider

状态：已确认。

决策：

```text
默认 live provider 使用 volcengine-ark-image。
generic-http-image 作为通用模板保留。
```

理由：

```text
当前本地已配置豆包图片生成示例，provider_registry 已有 volcengine-ark-image。
M4 的重点是产品化闭环，不是 provider 数量。
```

### 16.2 生成图默认素材角色

状态：已确认。

决策：

```text
被选生成图默认登记为 generated_candidate。
只有用户显式确认后，才能升级为 current_main_image。
```

理由：

```text
生成图可能不代表真实产品外观，直接作为主图会污染后续理解。
```

### 16.3 live 调用前 brief 确认要求

状态：已确认并落地。

原始建议：

```text
live 图片生成必须使用 confirmed image brief。
mock / dry-run 可使用 draft。
```

用户反馈：

```text
如果后续需要大批量生成图片 / 视频，逐个确认 brief 会让用户工作量过大。
确认机制需要从“逐条确认”升级为“策略确认”。
```

修订建议：

```text
单次生成：live 调用前确认 image brief。
批量生成：用户只确认 batch generation policy。
同一批次内的多个 brief / prompt variation 由 Hermes 自动派生、保存和追踪。
只要没有超出 policy 边界，不需要用户逐条确认。
一旦超出 policy 边界，必须停止并重新请求确认。
```

batch generation policy 应包含：

```text
product_id
channel / target
allowed_material_pack
style_direction
prompt_variation_rules
count_limit
provider
mode
external_call_limit
budget_note
forbidden_claims
must_keep_product_facts
expires_at / one_run_only
```

这个策略后续也适用于 M5 视频：

```text
单条高风险视频：确认 video brief。
批量视频脚本 / 图生视频：确认 batch generation policy。
Hermes 在 policy 内自动派生分镜和 prompt。
超出产品事实、素材范围、调用预算、风格边界时停止。
```

### 16.4 M4 live 验证调用次数

状态：已确认。

决策：

```text
如果开发有必要，可以调用真实豆包图片生成模型验证。
单次验证建议 1-2 张。
用户特别确认后最多 5 张。
```

理由：

```text
成本可控，也符合当前已有上限。
```

### 16.5 是否在 M4 引入 Web UI

状态：已确认。

决策：

```text
M4 不开发新的 UI 界面。
当前先以项目内 Hermes chat / Agent 对话作为主验证入口。
本机已安装 Hermes Desktop 只作为后续可选 UI / 对话测试入口。
```

理由：

```text
当前阶段核心是 Hermes 智能体闭环和数据契约。
UI 应在核心链路稳定后进入 M8。
项目内 Hermes chat 能更直接验证 tool calling、workflow-run 和 Product Brain 安全边界。
Hermes Desktop 可在对话入口跑通后，用于验证同一套能力是否能被桌面体验触发和审阅。
```

---

## 17. 主线防偏检查

M4 每个小版本完成后都必须回答：

```text
它是否增强了同一个产品的长期理解？
它是否让下一次图片 brief / prompt / 生成结果更贴合该产品？
它是否能通过 Hermes chat / Agent 对话和 workflow 被智能体稳定调用？
它是否保留了人工确认边界？
它是否复用了 Product Brain 和 M3 素材库，而不是做孤立工具？
它是否避免把脚本命令当成最终用户入口？
```

如果答案不能成立，该功能不进入 M4。
