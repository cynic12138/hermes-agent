# M13.1/M14.1 Dynamic Shot Production Implementation Plan

> Status: completed in worktree on 2026-07-17; uncommitted, unpublished, real Live acceptance pending.

> **For agentic workers:** REQUIRED SUB-SKILL: use executing-plans inline. The user forbids subagents and automatic commits; all commit steps are intentionally omitted.

**Goal:** Replace the exact-main still-image loop default with recoverable dynamic Seedance background shots, deterministic Product Plate motion, and hard motion/action QA.

**Architecture:** Extend the existing M13 shot graph and M14 QA. Video Providers generate product-free dynamic scene clips; the existing compositor trims them to the planned duration and overlays the immutable Product Plate. Motion requirements flow from Production Bible to plan, payload, compositor, and QA.

**Tech Stack:** Python 3.11+, Pydantic v2, FFmpeg/ffprobe, existing Product Creative artifact repository, pytest.

## Global Constraints

- Keep Product Creative inside `.hermes/plugins/product_creative`.
- Do not add a database or public Hermes tool.
- Do not call real external Providers in this implementation session.
- Do not make XHS/Douyin mandatory.
- Do not modify Canonical Product Brain.
- Do not commit, push, tag, release, clean, stash, or reset.
- Preserve old artifact readability through defaults.

---

### Task 1: Dynamic shot contract and video route

**Files:**
- Modify: `.hermes/plugins/product_creative/contracts/creative_artifacts.py`
- Modify: `.hermes/plugins/product_creative/runtime/media_plan.py`
- Modify: `.hermes/plugins/product_creative/runtime/creative_tasks.py`
- Modify: `.hermes/plugins/product_creative/runtime/authorization.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`
- Test: `tests/hermes_cli/test_product_creative_m10.py`

**Interfaces:**
- Produces `MediaShotPlan.motion_required`, `motion_description`, `maximum_freeze_ratio`, and `product_plate_motion`.
- `_reliable_media_provider(task)` returns the video Provider for video deliverables, including exact-main.

- [x] Add failing tests proving exact-main video uses `video_background`, product shots use `subtle_entrance`, and video authorization includes a bounded video budget.
- [x] Run the targeted tests and confirm failures are caused by missing dynamic fields/old image routing.
- [x] Add compatible fields and minimal compiler/routing changes.
- [x] Run targeted M10/M13 tests and confirm PASS.

### Task 2: Seedance duration adaptation

**Files:**
- Modify: `.hermes/plugins/product_creative/provider_registry.json`
- Modify: `.hermes/plugins/product_creative/provider_shots.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**
- Consumes Provider `limits.min_duration_seconds/max_duration_seconds`.
- Produces payload request fields `planned_duration_seconds`, `provider_duration_seconds`, and `trim_to_seconds`.

- [x] Add a failing test that a 2-second plan compiles to a 4-second Seedance body while preserving a 2-second delivery trim.
- [x] Add a failing test that the adapted prompt requires the action within the planned interval and still excludes product/text.
- [x] Implement bounded duration adaptation without changing plan duration.
- [x] Run the targeted tests and confirm PASS.

### Task 3: Deterministic Product Plate entrance

**Files:**
- Modify: `.hermes/plugins/product_creative/runtime/media_compositor.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`
- Test: `tests/hermes_cli/test_product_creative_m14_media_qa.py`

**Interfaces:**
- Consumes `MediaShotPlan.product_plate_motion`.
- Produces a shot with the Plate in its existing deterministic final geometry after 0.30 seconds.

- [x] Add a failing compositor test that command provenance records controlled translation and the rendered mid-frame preserves packaging pixels.
- [x] Implement a time-bounded overlay y-expression for `subtle_entrance`; keep `static` behavior unchanged.
- [x] Run compositor and packaging QA tests and confirm PASS.

### Task 4: Hard motion sufficiency Gate

**Files:**
- Modify: `.hermes/plugins/product_creative/runtime/media_technical_qa.py`
- Test: `tests/hermes_cli/test_product_creative_m14_media_qa.py`

**Interfaces:**
- `_freeze_check(..., motion_required, maximum_freeze_ratio)` returns FAIL/high for a motion-required frozen shot.

- [x] Add failing tests for motion-required still loops and legacy non-motion shots.
- [x] Pass the planned shot contract into freeze inspection.
- [x] Implement FAIL for required motion above its threshold; preserve WARN for legacy/static plans.
- [x] Run M14 targeted tests and confirm PASS.

### Task 5: VLM action fulfillment Gate

**Files:**
- Modify: `.hermes/plugins/product_creative/runtime/media_vlm_qa.py`
- Modify: `.hermes/plugins/product_creative/runtime/story_continuity_qa.py`
- Test: `tests/hermes_cli/test_product_creative_m14_media_qa.py`

**Interfaces:**
- Visual adapter output adds `observed_action` and `action_completed`.
- Story QA emits `action-fulfillment:<shot_id>`.

- [x] Add failing tests for PASS, FAIL, low-confidence UNKNOWN, and missing-adapter UNKNOWN.
- [x] Extend the VLM prompt and normalized observation without leaking product claims.
- [x] Add per-shot action checks; deterministic failures remain authoritative.
- [x] Run M14 targeted tests and confirm PASS.

### Task 6: Optional research-source policy

**Files:**
- Modify: `.hermes/plugins/product_creative/runtime/authorization.py`
- Modify: `.hermes/plugins/product_creative/runtime/creative_tasks.py` only if required by existing source selection
- Modify: `docs/PRODUCT_AGENT_DIRECTION.md`
- Modify: `docs/MVP_SCOPE.md`
- Test: `tests/hermes_cli/test_product_creative_m10.py`
- Test: `tests/hermes_cli/test_product_creative_live_sources.py`

**Interfaces:**
- Ordinary creative requests require no XHS/Douyin authorization.
- Platform sources are requested only by explicit platform wording or insufficient research policy.

- [x] Add failing tests that ordinary Web inspiration tasks do not request platform cookies.
- [x] Add explicit XHS/Douyin request tests that retain bounded authorization.
- [x] Make the minimum policy correction and update long-term product documents.
- [x] Run M10/live-source tests and confirm PASS.

### Task 7: Integrated offline dynamic E2E

**Files:**
- Modify: `tests/hermes_cli/test_product_creative_m13_media_production.py`
- Modify: `tests/hermes_cli/test_product_creative_m14_media_qa.py`

**Interfaces:**
- Exercises natural-language task → video plan → fake async video Provider → trim/composite → motion QA → repair.

- [x] Add an isolated fake-video fixture that returns a genuinely changing clip and an independently frozen failure clip.
- [x] Verify the good dynamic clip reaches packaging/story QA without a motion failure.
- [x] Verify the frozen clip creates a shot-scoped Repair Decision and preserves passing shots.
- [x] Verify restart resumes pending video tasks without duplicate submission.

### Task 8: Regression and knowledge closeout

**Files:**
- Create: `docs/M13_1_DYNAMIC_SHOT_PRODUCTION_IMPLEMENTATION.md`
- Modify: `AGENTS.md`
- Modify: `docs/AI_HANDOFF.md`
- Modify: `docs/PROJECT_STATE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/ARCHITECTURE_CURRENT.md`
- Modify: `docs/DECISION_LOG.md`

- [x] Run M10–M14 Python tests with Provider credentials cleared and a short repository-local basetemp (system `C:\tmp` denied access).
- [x] Run Desktop bundle/UI/typecheck/build, M9 recovery, public surface, sensitive scan, and `git diff --check`.
- [x] Record exact commands/results and the tenant-policy Live limitation.
- [x] Document recovery order, changed files, compatibility, and the next external acceptance step.

## Self-review

- Coverage: dynamic route, duration, Plate motion, deterministic motion QA, semantic action QA, optional sources, E2E and documentation are represented.
- YAGNI: no clip grouping, tracking, 3D product, new Provider, database or UI canvas.
- Compatibility: new frozen-model fields have defaults; old artifacts remain loadable.
- Security: no real external calls, no secrets, no Product Brain writeback.
