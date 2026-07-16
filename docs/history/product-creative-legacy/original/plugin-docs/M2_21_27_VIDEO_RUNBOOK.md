# M2.21-M2.27 Video Script Handoff Runbook

## Direction Correction

M2 is not a post-generation video operations phase. According to `PRODUCT_AGENT_DIRECTION.md`, M2 should focus on multi-channel content, short-video scripts, storyboards, creative descriptions, channel playbooks, and reusable content patterns.

For the video route, the main M2 output is:

```text
Product Brain
  -> material-aware video intent
  -> high-quality storyboard brief
  -> provider-ready video prompt / payload
  -> optional explicit video model submission
```

The quality lever is the storyboard and provider prompt. Video task polling, result downloading, video QA, and post-generation scoring are not the M2 mainline unless explicitly confirmed later.

## Current Scope

- M2.21: registered material can carry a provider-accessible remote URL, but local material remains the canonical asset record.
- M2.22-M2.23: video provider payload and optional live submission exist as execution boundary utilities, not as the default M2 learning loop.
- M2.24-M2.25: video learning should prioritize script, storyboard, prompt, channel angle, and material usage feedback before generation.
- M2.26-M2.27: workflow tools expose video steps, with the recommended path corrected to review the video brief before provider payload creation.

## Main M2 Video Workflow

Register and understand a local product image:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 asset-register --id <product-id> --path C:\path\to\main.png --role current_main_image --description "用户上传主图" --usage video_first_frame
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 image-analyze --id <product-id> --asset <material-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 visual-align --id <product-id> --analysis <analysis-id> --note "这张主图用于图生视频首帧参考。"
```

Create the video intent and storyboard brief:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-intent --id <product-id> --message "用这张主图做一个抖音今日视频" --asset <material-id> --theme "夏日清爽开瓶"
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief --id <product-id> --intent <intent-id>
```

Review the storyboard before provider handoff:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-review --id <product-id> --brief <video-brief-id>
```

M2.28 adds an explicit edit/confirmation gate. The review package creates an editable patch under:

```text
.hermes/product_creative/products/<product-id>/artifacts/video_brief_patches/<patch-id>.json
```

Edit only the fields that need to change, then confirm the revised brief:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-revise --id <product-id> --brief <video-brief-id> --patch <patch-id> --confirmed
```

The revised brief becomes the new latest video brief with status `confirmed_for_provider_payload`.

M2.29 allows script/storyboard feedback before any real video generation:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-feedback --id <product-id> --brief <revised-video-brief-id> --selected --rating 5 --allow-evolve --note "保留这个开场钩子和产品主体回看结构。"
```

The feedback enters the normal `evolve -> apply` proposal flow. It does not mutate Product Brain until an explicit confirmed apply.

Build provider payload only after the storyboard is acceptable:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-generate --id <product-id> --brief <revised-video-brief-id> --provider volcengine-ark-video
```

If the provider requires public reference URLs, bind them before live execution:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 asset-bind-url --id <product-id> --asset <material-id> --url "https://example.com/provider-readable-image.jpg" --usage video_reference
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 live-readiness --id <product-id> --provider volcengine-ark-video --kind video --payload <provider-payload-id>
```

Submit a real provider task only as an explicit execution step:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 generation-job --id <product-id> --payload <provider-payload-id> --provider volcengine-ark-video --mode live
```

## Storyboard Quality Contract

The video brief should carry enough information to directly control video generation:

```text
shot
duration
purpose
scene
action
camera
motion
composition
product_visibility
lighting
transition
audio
caption
visual_prompt
negative_prompt
provider_prompt_segment
```

The provider prompt must make the model follow the shot order, preserve the product/reference image, avoid unverified claims, and keep captions short.

## Workflow Entry

The recommended workflow should now prefer review before provider payload:

```powershell
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-status --id <product-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-next --id <product-id>
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-plan --id <product-id> --action review_video_brief
.\.hermes\plugins\product_creative\scripts\product_creative.ps1 workflow-plan --id <product-id> --action build_video_provider_payload
```

## Not M2 Mainline

These are intentionally not exposed in the current M2 tool surface:

- provider task polling
- result URL import as a required step
- generated video binary download
- generated video multimodal QA
- post-generation scoring as the default self-iteration route

## Verification

Run sequentially, not in parallel, because the project-plugin runner temporarily adjusts Hermes plugin config:

```powershell
.\.hermes\plugins\product_creative\scripts\verify_m2_video_brief_review.ps1
.\.hermes\plugins\product_creative\scripts\verify_m2_video_provider_payload.ps1
.\.hermes\plugins\product_creative\scripts\verify_m2_workflow_execute.ps1
```
