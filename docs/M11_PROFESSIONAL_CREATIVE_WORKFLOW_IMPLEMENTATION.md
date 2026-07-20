# M11 Professional Creative Workflow Implementation

- Date: 2026-07-16
- Branch: `product-creative-rebaseline-20260716`
- Current HEAD before M11 commit: `0aa95637213f02eca2ef8f619daaf771150a7e11`
- Source strategy: scheme 1; `.hermes/plugins/product_creative` remains the only business source of truth until the product is stable
- State: `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED`
- Git state: uncommitted, unpushed, untagged, unreleased

## 1. Why M11 exists

M10 proved that Hermes can accept natural language, inspect Product Brain, select materials, call Web/XHS/Douyin and submit real image/video providers. It did not prove that the creative result was useful. The reviewed samples exposed two product failures:

- a fixed product image plus generic captions was incorrectly treated as a story video;
- a generative video provider redrew Chinese packaging text and produced illegible characters.

M11 moves the completion boundary from “a provider returned a playable file” to “a complete, traceable and executable professional creative package passed a pre-generation gate.”

## 2. Scope and non-scope

M11 implements the professional pre-generation layer:

```text
Natural-language goal
→ Creative Task Brief
→ Product Grounding Pack
→ Research Insight Pack
→ Stable / Variation / Exploration candidates
→ Creative Decision
→ Story Package
→ Production Bible
→ Preflight QA
→ existing generation capability
```

It does not add providers, perform live platform crawling in normal tests, implement automatic media QA/repair, create a free-form multi-agent group, split the source repository, or change Product Brain/database schemas.

## 3. Reuse decision

The implementation extends the existing M10 path:

- public entry remains `product_workflow_run`;
- `CreativeTaskRecord`, Goal Planner, Command Bus and capability registry remain the orchestration foundation;
- Product Brain, readiness, materials, external source snapshots, provider tasks, receipts/events and recovery remain authoritative;
- the existing artifact repository and workspace filesystem store the new versioned artifacts;
- Desktop keeps the existing Overview, Tasks, Review, Assets and Learning views.

No parallel task database, second chat entry, second provider registry, second material library or second Product Brain was created.

## 4. Versioned professional artifacts

The following sealed Pydantic contracts live in `contracts/creative_artifacts.py`. Each artifact contains schema identity, task/product identity, timestamps, source references, status and a SHA-256 content hash. Extra fields are rejected and modified persisted content fails validation.

1. `product_creative.creative_task_brief.v1`
2. `product_creative.product_grounding_pack.v1`
3. `product_creative.research_insight_pack.v1`
4. `product_creative.creative_candidate.v1`
5. `product_creative.creative_decision.v1`
6. `product_creative.story_package.v1`
7. `product_creative.production_bible.v1`
8. `product_creative.qa_report.v1`

Existing tasks without these fields load as `legacy_incomplete`; old workspace data is not batch migrated.

## 5. Runtime flow

### 5.1 Brief and grounding

`professional_artifacts.py` creates the task brief and grounding pack before creative work. Grounding reads only the current confirmed Product Brain and the current active packaging material. External search results and model interpretations do not become confirmed claims.

The grounding pack records:

- Brain version and fingerprint;
- SKU readiness;
- current packaging material ID and hash;
- allowed and forbidden claims;
- selected input materials and evidence references;
- blockers for the current deliverable.

### 5.2 Research

Task-scoped external snapshots are converted into source-specific insight:

- Web: event, date and factual background;
- XHS: consumer language and usage scenes;
- Douyin: first-five-second hook and spoken-copy structure.

Every research pack is `not_product_fact=true`. If no task-scoped source exists, it records an explicit offline degradation warning instead of pretending that real-time research occurred.

### 5.3 Candidates and decision

`creative_direction.py` currently produces three bounded directions:

- Stable: highest execution and compliance confidence;
- Variation: a materially different but still practical treatment;
- Exploration: a higher-novelty narrative with higher execution risk.

Each candidate contains a hook, conflict, progression, ending, product role, required material, production route, risks and feasibility. The decision scores product fit, channel fit, freshness, feasibility, packaging safety and compliance safety, then preserves the selected and rejected reasons.

This deterministic director is an M11 contract and gate implementation. It is not the final professional creative intelligence; M12 will move domain methods and examples into tested business Skills.

### 5.4 Story and Production Bible

The selected candidate becomes a Story Package with a concrete premise, character, setting, world rules, visual/audio hook, incident, conflict, escalation, turn, product intervention, ending and prohibited content.

The Production Bible converts that story into five shot-level instructions:

- duration and composition;
- action, characters and scene;
- input material IDs;
- deterministic captions;
- narrative function;
- continuity and retry rules;
- provider/compositor responsibility.

Video provider prompts are compiled from the Production Bible. The raw user message is not passed through as the final provider prompt.

### 5.5 Packaging trust boundary

Natural-language requirements such as “包装外观和文字不得变化”, “产品包装文字必须保持不变” and “主图原样保留，不允许改动” now route to `exact-main-composite`.

The selected product material becomes `immutable_product_plate`; backgrounds, characters and motion may be generated, while packaging pixels and deterministic subtitles belong to the compositor. Preflight QA independently re-checks the raw message so a lost Boolean flag cannot silently permit a reference-guided generative route.

This fix was discovered by the real Zhou Shiwu review fixture. The first attempt incorrectly selected `reference-guided-generation`; failing tests were added before the parser and QA defenses were changed.

## 6. Provider and recovery boundary

For generative video, the runtime refuses dispatch unless the current task has:

- a valid Creative Decision;
- a valid Story Package;
- a valid Production Bible;
- a `PASS` QA report;
- a complete professional artifact status.

The compiler records the source Bible ID/hash in the provider payload. Task revisions create `-rN` artifact IDs, preserve the original goal and old artifacts, and require a new authorization before another provider submission. Revision messages can also contribute structured production constraints: for example, “产品在第 4 秒左右出现” is parsed into `requested_product_reveal_seconds`, changes the shot order, and is verified against the first shot that actually references the product material. Existing provider-task idempotency and receipt/event recovery remain unchanged.

The legacy direct exact-main public tool remains available for compatibility. The official M11 `product_workflow_run` path supplies Story/Bible IDs and must not use the generic fallback story.

## 7. Desktop changes

- Overview shows Product Grounding and Preflight QA.
- Tasks shows the eight artifact gates, status and current artifact IDs.
- Review shows all three candidates, Creative Decision, Story Package and QA.
- Assets shows selected inputs and the Production Bible.
- Workspace and locale remount behavior remains unchanged.

No Product Creative-specific route was added back to Hermes core.

## 8. Files changed by responsibility

### Contracts and persistence

- `.hermes/plugins/product_creative/contracts/creative_artifacts.py`
- `.hermes/plugins/product_creative/contracts/models.py`
- `.hermes/plugins/product_creative/contracts/__init__.py`
- `.hermes/plugins/product_creative/runtime/professional_artifacts.py`

### Creative direction and orchestration

- `.hermes/plugins/product_creative/runtime/creative_direction.py`
- `.hermes/plugins/product_creative/runtime/creative_tasks.py`
- `.hermes/plugins/product_creative/runtime/agent.py`
- `.hermes/plugins/product_creative/application/planner.py`

### Provider and exact-main compilation

- `.hermes/plugins/product_creative/provider_payloads.py`
- `.hermes/plugins/product_creative/provider_ports.py`
- `.hermes/plugins/product_creative/provider_gateway.py`
- `.hermes/plugins/product_creative/capabilities/video/executor.py`
- `.hermes/plugins/product_creative/capabilities/video/exact_video_service.py`

### Desktop and tests

- `.hermes/plugins/product_creative/application/console_queries.py`
- `.hermes/plugins/product_creative/desktop_ui/index.js`
- `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`
- `tests/hermes_cli/test_product_creative_m11_artifacts.py`

## 9. Verification evidence

Environment used for the final local verification:

- Python `3.13.9`
- Node `v24.15.0`
- npm `11.13.0`
- credentials and `PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER` removed from test processes
- isolated `HERMES_HOME`, `TMP` and `TEMP`

Passed:

- M11 professional artifacts and Hermes natural-language E2E: 31 tests;
- M10 regression: 35 tests;
- Live source adapter regression with isolated fixtures: 10 tests;
- distribution contracts: 3 tests;
- Desktop backend/page API: 12 tests;
- Desktop plugin Registry/UI: 9 tests;
- TypeScript typecheck and Desktop production build;
- plugin desktop bundle build, SHA-256 `c32a6eb0483a1d25b968938b87bf3ce9cecce052c2ae9a51351416f428ecdce6`;
- M9 review/recovery: 25/25;
- public surface golden: 84 tools / 84 CLI, unchanged hash;
- contract invariants: 51 workflow actions, 84 tools and 84 CLI, zero failures.

The production build retained existing dirty-stamp, CSS token and large-chunk warnings; it completed successfully. Final `git diff --check` passed with line-ending conversion warnings only.

These results do not claim that this M11 run performed real Web/XHS/Douyin crawling or paid provider generation. Live calls remain user-authorized acceptance work.

## 10. User review fixture

The real-material review fixture is isolated at:

`C:\data\work file\hermers-agent for me\.m11-review-20260716-4`

It uses `周十五产品垫图\1.png`, SHA-256:

`fd6735a1595eea489af7127f4a6adc408ef9bb831851376b0488c392405a8801`

The authoritative public-entry review task is `task-2e495b5048ed4f45a62be4e05f59b6ad`. It entered `preview_first` from natural language, returned only three candidates and a Decision, then accepted “选择 B 方向，产品在第 4 秒左右出现” through the same `product_workflow_run` task. Revision `r1` selects the bag-object Variation, places the first immutable product plate at exactly 4.0 seconds, limits product copy to “外观可爱/方便随身携带”, uses `exact-main-composite`, and passes all eight preflight checks. The task is deliberately left at `NEEDS_INPUT`; no final video, external call, provider authorization or Product Brain writeback occurred. The human-readable package is `docs/reviews/M11_ZHOU_SHIWU_CREATIVE_PACK_REVIEW.md`.

Earlier fixture directories are retained as failure evidence:

- `.m11-review-20260716-1`: PowerShell stdin encoding replaced Chinese text with `?`;
- `.m11-review-20260716-2`: exposed the missing packaging-preservation phrase handling.
- `.m11-review-20260716-3`: exposed packaging text being misclassified as a separate text deliverable.

Inside `.m11-review-20260716-4`, the earlier engineering task and its original/`r1`–`r6` artifacts remain immutable as diagnostic history. `r1` exposed unconfirmed suggestive copy, `r2` exposed that timing feedback had not changed the shot structure, `r3` preserved another PowerShell stdin encoding failure, `r4` verified the 4-second constraint, `r5` confirmed that `preview_first` stops at candidates/Decision, and `r6` proved the full pack internally before the public continuation path was implemented. The newer public-entry task above is the current review source of truth.

## 11. Requirement-by-requirement completion audit

| M11 completion requirement | Status | Direct evidence |
|---|---|---|
| User does not need product ID, CLI, JSON or prompt engineering | CONFIRMED for Hermes chat | Real `AIAgent` natural-language E2E selects `product_workflow_run`; the public tool remains the only Product Creative task entry |
| Provider-ready video tasks contain Brief, Grounding, Decision, Story and Production Bible | CONFIRMED | Artifact contracts, provider gate and missing-artifact zero-dispatch tests |
| Three candidates are materially different and the decision is explainable | CONFIRMED structurally | Stable/Variation/Exploration tests, score/rejection coverage and public review task |
| Platform inspiration traces to creative artifacts without Product Brain pollution | CONFIRMED with isolated fixtures | Snapshot refs enter Research/Candidates; `not_product_fact=true`; Brain hash remains unchanged |
| Missing QA/Story/Bible causes zero Provider calls | CONFIRMED | Fail-if-called Command Bus regression |
| Exact packaging language selects a safe route | CONFIRMED | Natural-language phrase matrix, independent QA recheck and `exact-main-composite` review task |
| Generic caption templates cannot qualify as story delivery | CONFIRMED at preflight | `story_specific` check and `NEEDS_REVISION` regression |
| Interrupted/revised tasks continue through natural language without overwriting old artifacts | CONFIRMED | M10 durable resume plus M11 immutable `-rN` revision tests |
| Desktop exposes the key artifacts and blockers | CONFIRMED by targeted tests | backend/page projections and Product Creative bundle tests |
| User personally accepts or revises one complete creative package | CONFIRMED | User response on 2026-07-16: “全部接受，允许进入下一步” |

Therefore M11 is `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED`. This does not authorize commit, push, release or live provider execution.

## 12. Known limitations

- Candidate generation is still deterministic scaffolding and covers one short product-story family; it does not yet prove broad creative quality.
- The current Zhou Shiwu review pack did not use real-time Web/XHS/Douyin evidence.
- M14 automatic media QA and repair are not implemented.
- M13 mixed shot-level production and plugin-managed ffmpeg diagnosis are not implemented.
- A `PASS` preflight report means the package is structurally executable and respects known boundaries; it is not a substitute for human creative approval.
- The tracked-only release export intentionally excludes uncommitted files. A real M11 distribution export/install can only be authoritative after the M11 source is committed.

## 13. Recovery order

After local Codex state loss:

1. read `AGENTS.md`;
2. read `docs/PRODUCT_AGENT_DIRECTION.md`;
3. read `docs/AI_HANDOFF.md` and `docs/PROJECT_STATE.md`;
4. read this document and the M11 plan;
5. inspect `creative_artifacts.py`, `professional_artifacts.py`, `creative_direction.py` and `creative_tasks.py`;
6. run the M11, M10, contract, public-surface and Desktop gates;
7. inspect the review fixture and review Markdown;
8. do not mark M11 complete until the user accepts or revises the creative package.

## 14. Stable-then-split threshold

Scheme 1 remains active. Splitting the plugin into an independently developed source repository should be reconsidered only when:

- public plugin contracts remain unchanged across at least two consecutive product milestones;
- the plugin installs and runs without in-tree import assumptions;
- standalone unit/integration/Desktop tests pass from an exported user-plugin installation;
- release and compatibility matrices no longer require coordinated core edits;
- product workflows and artifact schemas are stable enough to version independently;
- the team accepts the added dual-repository debugging and release cost.
