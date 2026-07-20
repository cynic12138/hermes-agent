# M13.1 / M14.1 Dynamic Shot Production Implementation

## Recovery identity

- Date: 2026-07-17
- Branch: `product-creative-rebaseline-20260716`
- HEAD at implementation time: `0aa95637213f02eca2ef8f619daaf771150a7e11`
- State: `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED_LIVE_ACCEPTANCE_PENDING`
- Source of truth: `.hermes/plugins/product_creative`
- Design: `docs/plans/2026-07-17-m13-1-dynamic-shot-production-design.md`
- Step plan: `docs/plans/2026-07-17-m13-1-dynamic-shot-production-plan.md`

This increment fixes the structural reason the first exact-main sample looked like a
slideshow: M13 selected an image Provider whenever packaging had to remain exact, then
FFmpeg looped each image for the planned shot duration. M13.1 keeps packaging exact by
local deterministic composition while assigning scene, person and action motion to the
video Provider.

No real Provider, Web, XHS, Douyin or DeepSeek call was made in this implementation
session. Provider credentials were cleared from every Python regression command.

## Resulting production chain

```text
Natural-language video goal
→ Product Grounding / Creative Decision / Story / Production Bible
→ Media Execution Plan with per-shot motion contract
→ Seedance product-free scene/person/action clip (4–15 seconds)
→ local trim to the planned story interval
→ immutable Product Plate deterministic entrance/composite
→ deterministic ASS subtitle
→ H.264/AAC final composition
→ technical freeze/motion gate
→ VLM action-fulfillment/continuity gate
→ PASS, shot-scoped REPAIR, HUMAN_REVIEW or REJECT
```

The Product Plate never enters the generation Provider. It may translate vertically for
the first 0.30 seconds, then stays at the existing deterministic final geometry. The first
version does not rotate, perspective-transform, deform, track hands or allow occlusion of
the package.

## Contract and routing changes

`MediaShotPlan` remains backward-readable through defaults and now carries:

- `motion_required`
- `motion_description`
- `maximum_freeze_ratio`
- `product_plate_motion`: `none`, `static` or `subtle_entrance`

For a video deliverable, `_reliable_media_provider` now chooses the video Provider even
when the request requires exact packaging or the Production Bible uses
`exact-main-composite`. Old recoverable task records without `request.deliverables` are
recognized from their video workflow actions and pending media shots.

Task authorization still keeps image and video budgets explicit and bounded at five. An
exact-main video no longer removes the video budget because the local compositor protects
the package; it does not create scene motion.

## Seedance duration adaptation

The Volcengine video Provider registry records `min_duration_seconds=4` and
`max_duration_seconds=15`. `MediaShotPlan.duration_seconds` remains the final delivery
duration. A Provider payload separately records:

- `planned_duration_seconds`
- `provider_duration_seconds`
- `trim_to_seconds`

A two-second story shot requests four seconds from Seedance. The adapted prompt requires
the core action to finish within the first two seconds and retain natural movement after
that point. The compositor trims the downloaded source back to two seconds. A planned
shot above the Provider maximum fails with an instruction to split the shot instead of
silently looping it.

## Motion and action quality gates

The technical freeze check uses the shot-specific threshold. A motion-required shot at or
above its threshold is `FAIL/high` and repairable; legacy non-motion artifacts retain the
old warning behavior.

One important defect was found during the integrated regression: FFmpeg may emit only
`freeze_start` when a freeze continues through end-of-file. The old parser summed only
`freeze_duration`, so a fully static clip could appear to have zero frozen seconds. The
parser now closes the final open freeze interval at the probed shot duration.

The Doubao VLM observation adds `observed_action` and `action_completed`. Story QA emits
`action-fulfillment:<shot_id>` for every motion-required shot:

- high-confidence completed action: `PASS`
- high-confidence missing/incomplete action: `FAIL/high`, shot-scoped repair
- low confidence or missing adapter: `UNKNOWN/high`, human review

Deterministic failures remain authoritative over a semantic PASS.

## Inspiration-source policy

Web is the default fresh-information source. Product Brain, local materials, historical
inspiration and normal Web research are sufficient for ordinary creative tasks. XHS and
Douyin are optional specialist sources, used only when the user explicitly requests
platform research or a future research-sufficiency decision proves ordinary sources are
insufficient. A channel name such as “今天能发的抖音视频” does not request platform
Cookie access; “搜索抖音最新爆款灵感” does.

Any external result remains `not_product_fact` evidence/inspiration and cannot update the
Canonical Product Brain without its separate proposal and confirmation.

## Additional reliability fixes found by the Gate

- Provider payload persistence now creates its own collection directory, removing an
  isolated-test ordering dependency.
- New Media QA artifact IDs use a stable 20-character SHA-256 identity token. The report
  still stores full task, plan, manifest and source references, while avoiding Windows
  `MAX_PATH` failures during atomic persistence.
- The integrated fake async video Provider now returns a genuinely changing MP4 instead
  of a PNG disguised as a video result. Restart polling submits each shot once and does
  not consume duplicate authorization calls.

## Files changed by this increment

Runtime and contracts:

- `.hermes/plugins/product_creative/contracts/creative_artifacts.py`
- `.hermes/plugins/product_creative/provider_registry.json`
- `.hermes/plugins/product_creative/provider_shots.py`
- `.hermes/plugins/product_creative/runtime/authorization.py`
- `.hermes/plugins/product_creative/runtime/creative_tasks.py`
- `.hermes/plugins/product_creative/runtime/media_plan.py`
- `.hermes/plugins/product_creative/runtime/media_compositor.py`
- `.hermes/plugins/product_creative/runtime/media_technical_qa.py`
- `.hermes/plugins/product_creative/runtime/media_vlm_qa.py`
- `.hermes/plugins/product_creative/runtime/story_continuity_qa.py`
- `.hermes/plugins/product_creative/runtime/media_qa.py`

Tests:

- `tests/hermes_cli/test_product_creative_m10.py`
- `tests/hermes_cli/test_product_creative_m13_media_production.py`
- `tests/hermes_cli/test_product_creative_m14_media_qa.py`

Knowledge:

- this document
- the M13.1 design and implementation plan
- `AGENTS.md`, `docs/AI_HANDOFF.md`, `docs/PROJECT_STATE.md`,
  `docs/ROADMAP.md`, `docs/ARCHITECTURE_CURRENT.md`, `docs/DECISION_LOG.md`,
  `docs/MVP_SCOPE.md` and `docs/PRODUCT_AGENT_DIRECTION.md`

## Verification evidence

All Python commands cleared `DOUBAO_API_KEY`, `ARK_API_KEY`,
`PRODUCT_CREATIVE_ARK_API_KEY`, `DEEPSEEK_API_KEY` and `SILICONFLOW_API_KEY`.

| Gate | Result |
|---|---|
| M10 natural-language task regression | 40 passed |
| M13 media production regression | 41 passed |
| M14 QA/repair regression | 35 passed |
| M11/M12/live-source/distribution regression | 85 passed |
| Desktop plugin backend API | 12 passed |
| Desktop bundle safety | 2 passed |
| Desktop routes/registry/page/plugin UI | 16 passed |
| TypeScript typecheck | PASS |
| Desktop production build | PASS on local Node 24.15.0 |
| M9 review/recovery | 25/25 passed |
| Public surface golden | 84 tools / 84 CLI, hash matched |
| Distribution validation and sensitive scan | PASS |
| Offline enabled user-plugin install | PASS |
| Exported bundle registry | 1 passed |
| `git diff --check` | PASS; line-ending warnings only |

The release-authoritative Node environment remains Node 22. The local Node 24 build is a
supplementary result, not a replacement for CI.

The isolated distribution was exported outside the repository to
`C:\data\work file\hermers-agent for me\m131-dist-20260717`. It was not published.

## Known limits and next acceptance gate

- Codex tenant policy still blocks sending workspace product media/prompts to external
  Providers, despite the user's explicit task authorization. This increment made zero
  real calls and did not attempt a workaround.
- The prior five-image/exact-main sample remains a valid `REPAIR` artifact but is not
  evidence of dynamic production quality.
- Real Seedance motion, real VLM action judgment and a repaired real shot have not yet
  passed the combined Live Gate.
- Provider audio is not yet preserved by the deterministic compositor; its silent AAC
  track can produce a non-blocking silence warning.
- Complex product interaction, hand-held rotation, perspective, occlusion and tracking
  are not promised by this version.

The next acceptance action is one externally executed, sanitized Seedance shot set using
the new product-free dynamic prompts. Import it into the existing task, then run local
trim/composition, M14 QA, one bounded shot repair if needed, and user review. M15 Desktop
internal trial work starts only after that Live Gate and user acceptance.

## Recovery checklist

1. Read `AGENTS.md`, `docs/AI_HANDOFF.md`, `docs/PROJECT_STATE.md` and this document.
2. Confirm branch, HEAD and dirty worktree; do not clean or reset.
3. Confirm `MediaShotPlan` contains the four dynamic fields with defaults.
4. Confirm exact-main video authorization and provider routing both include video.
5. Confirm Seedance registry limits are 4–15 seconds and payloads keep planned/provider/
   trim durations separately.
6. Run the M13 dynamic async fixture and M14 frozen-shot repair tests with credentials
   cleared.
7. Run M9/public-surface and distribution validation before any release proposal.
8. Do not commit, push, tag or publish until the user separately authorizes it.
