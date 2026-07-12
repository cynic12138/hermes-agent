# AI-Driven Product Creative Runtime Architecture

Status: implemented runtime refactor baseline after M8 closeout

## 1. Runtime Goal

The runtime owns one long-lived product workspace. A user provides a product, material, goal, result, channel performance, or feedback. The runtime then:

1. resolves the product workspace;
2. uses an LLM-backed structured decision with deterministic fallback;
3. selects a text, image, video, exact-main-video, review, feedback, inspiration, material, or learning action;
4. executes a declarative workflow through guarded action contracts;
5. persists artifacts, workflow state, events, evidence, and diagnostics;
6. evaluates generated results and user/channel feedback;
7. aggregates successful and failed patterns into evidence-backed rule candidates;
8. creates a reviewable writeback proposal;
9. updates Product State, Product Brain pages, channel playbooks, and material/generation preferences only after the required confirmation;
10. rebuilds generation-safe context so the next generation consumes the confirmed learning.

The closed loop is:

```text
User input
  -> IntentDecision
  -> WorkflowDefinition
  -> ActionCommand
  -> Guard + missing-input policy
  -> Domain action executor
  -> Provider/Material/Artifact/Product Brain port
  -> ActionResult + evidence
  -> EvaluationReport
  -> RuleCandidate aggregation/conflict detection
  -> WritebackProposal
  -> explicit confirmation when required
  -> Product Brain projections
  -> generation-safe context for the next turn
```

## 2. Dependency Direction

Dependencies point inward toward contracts and application/runtime services.

```text
Hermes tools / CLI
        |
        v
runtime agent + decision + workflow state machine
        |
        v
action/workflow registries + DTO contracts
        |
        v
domain services (brain, material, image, video, review, inspiration)
        |
        v
ports (repositories, provider gateway)
        |
        v
filesystem / provider adapters / HTTP and media implementations
```

Rules:

- CLI does not call domain functions directly. It invokes the same named tool adapter as Hermes.
- Workflow execution does not dispatch through a central action `if/elif` executor. It uses the action registry.
- Image/video workflow actions call `GenerationProviderGateway`, not low-level HTTP/provider modules.
- Workflow and rule state use strict, atomic repositories.
- Product Brain canonical learning is not mutated by status, planning, review, feedback, evaluation, or proposal creation.
- Compatibility files (`workflow.py`, `store.py`, `providers.py`, `schemas.py`, `tools.py`) are stable facades only.

## 3. Contracts

`contracts/actions.py` is the single action catalog. It defines action name, tool, domain, input/confirmation requirements, workspace writes, and Product Brain mutation policy.

`contracts/models.py` owns strict Pydantic boundary DTOs:

- `IntentDecision`
- `ActionCommand`
- `ActionResult`
- `WorkflowStep`
- `WorkflowInstance`
- `EvaluationReport`
- `EvidenceRef`
- `RuleCandidate`
- `WritebackProposal`

`schema_runtime.py` derives the workflow action enum from `ACTION_NAMES`. Action names are not copied into a parallel schema list.

## 4. AI Decision Layer

`runtime/decision_service.py` owns intent decisions.

- Explicit actions are validated against the action contract.
- Hermes LLM receives a compact Product State/workflow/evidence snapshot and the allowed action catalog.
- The LLM must return `IntentDecision` JSON and cannot assert confirmation.
- Unknown or invalid LLM actions are rejected and fall back to deterministic routing.
- `PRODUCT_CREATIVE_DISABLE_LLM=1`, missing LLM configuration, empty input, timeout, or parse failure uses deterministic fallback.
- Safety gates remain in guard/action policy code; they are never delegated to model judgment.

## 5. Action Runtime

`runtime/action_registry.py` dynamically discovers `runtime/actions/*.py`. All 45 contracted actions must have exactly one runtime definition.

Each `ActionRuntimeDefinition` can supply:

- executor;
- automatic advancement policy;
- idempotency fields;
- plan policy;
- guard policy;
- missing-input policy;
- execution argument binder;
- conversation argument binder.

M9/M10 extension rule: add an action contract and a domain action module. New behavior can own its policies in that module; it does not require another central execution branch.

Dangerous or externally submitted actions use action receipts. Receipt keys are hashes of declared idempotency fields. Already applied Product Brain proposals are valid idempotent replays after confirmation.

## 6. Workflow State Machine

`runtime/workflow_catalog.py` dynamically discovers `runtime/workflows/*.py`. Current definitions are grouped by product/material, content/inspiration, image, and video domains.

`WorkflowInstance` persists under `structured/workflows/` and contains:

- workflow and definition version;
- product and trace identity;
- structured intent;
- ordered steps and step state;
- current step;
- attempts, output references, pause reason, and error fields.

Step states are pending, ready, running, waiting for input, waiting for confirmation, waiting for provider, succeeded, failed, or cancelled.

Resume is allowed only when the persisted current step equals the requested action. This prevents shared learning actions such as `create_evolution_proposal` from attaching to an unrelated image/channel/video workflow.

Workflow events append to `structured/workflow_events.jsonl`. A workflow run carries a trace ID into every action execution and structured error record.

## 7. Storage Layers

### Product Brain Repository

Owns canonical `structured/product_state.json` and Product Wiki page boundaries. Canonical learning writeback is confirmation-gated. Generation-safe projections strip source IDs, timestamps, and operational metadata before model use.

### Structured Store

Owns machine state and event streams such as workflows, rule candidates, proposals, receipts, feedback indexes, and runtime errors. JSON reads are strict; corrupt structured state raises a diagnostic error instead of silently returning an empty object.

### Artifact Store

Owns generated/reviewable JSON artifacts grouped by artifact type. It cannot resolve paths outside the product workspace.

### Material Store

Owns material asset records and the material library projection. Binary files stay under `assets/`; structured material metadata stays behind the Material Repository. Material feedback affects selection scoring but does not directly mutate canonical Product Brain learning.

Filesystem writes use a short same-directory temporary file, flush, `fsync`, and atomic replace. The short temporary name avoids Windows path-length failures for long product/action IDs.

## 8. Provider Layer

`provider_ports.py` defines `GenerationProviderGateway`. `provider_gateway.py` supplies the default adapter and supports dependency injection for verification and future providers.

Provider responsibilities are isolated:

- payload adaptation;
- capability/registry lookup;
- readiness and validation;
- HTTP submission;
- asynchronous task status;
- response normalization and result import.

Workflow actions do not own credentials, HTTP, downloads, or provider response parsing. Live image/video execution remains confirmation-gated; tests use mock providers.

## 9. Artifact and Review Layer

Generated content, briefs, provider payloads, jobs/results, review packages, evaluations, feedback, task overviews, and workflow runs are immutable or append-oriented artifacts. Manifests provide discoverability without becoming canonical Product Brain state.

Review and feedback are separate from learning apply:

- review packages are read-only presentations;
- feedback records user judgment and optional channel metrics;
- evaluation creates proposed updates and rule candidates;
- proposal creation is reviewable and does not mutate canonical learning;
- proposal apply requires the action contract's confirmation policy.

## 10. Rule and Writeback Lifecycle

Rule candidates carry scope, target path, type, value, conditions, evidence, sample size, confidence, direction, risk, conflict key, and lifecycle status.

Scopes:

- Product State/Product Brain;
- channel playbook;
- material preference;
- image/video generation policy.

Risk levels:

- level 1: recorded as a candidate; still not silently applied to canonical Product Brain;
- level 2: requires review;
- level 3: requires explicit confirmation.

Repeated identical rules aggregate subject evidence, sample size, and confidence. Different values under the same conflict key are marked `review_required` with conflict references. Applied proposals mark linked rule candidates applied.

Channel feedback accepts optional impressions, views, clicks, likes, saves, shares, comments, conversions, spend, and revenue. The writer derives engagement, click-through, conversion, and return-on-ad-spend rates. Sufficient-sample high/low performance becomes channel playbook and successful/failed pattern updates in the next proposal.

## 11. Error and Logging Strategy

Errors have:

- stable error ID and code;
- exception type and redacted message;
- product, action, stage, trace, and retryability;
- a persisted JSONL diagnostic path.

Classification distinguishes store corruption, not found, validation, timeout, IO, and internal failures. CLI, tools, and workflow execution use the same classifier. Workflow instance, run artifact, event stream, receipt, and runtime error can be correlated by workflow/run/action IDs and trace.

## 12. Entry Points

`tool_catalog.py` declares 78 tool names, schemas, and handler names.

`tool_handlers.py` owns thin Hermes adapter functions and uniform error serialization. `tools.py` is a stable facade.

`cli.py` owns parser definitions and a declarative command list. It maps commands to the same tool names and calls `invoke_product_tool`; it does not maintain a second business dispatch table.

## 13. Migration and Acceptance

Implemented migration stages:

1. single action/schema contract and strict DTOs;
2. discoverable domain action registry;
3. discoverable workflow catalog and persistent workflow instances;
4. idempotent receipts and atomic structured storage;
5. Product Brain/Structured/Artifact/Material repository ports;
6. injectable provider gateway;
7. structured LLM intent decision with fallback;
8. review/evaluation/rule/writeback lifecycle;
9. unified Hermes tool and CLI adapter path;
10. structured errors, traces, and updated boundary verification.

Acceptance commands:

```powershell
python -m compileall -q .hermes/plugins/product_creative
./.hermes/plugins/product_creative/scripts/verify_ai_runtime_architecture.ps1
./.hermes/plugins/product_creative/scripts/verify_product_creative_contracts.ps1
./.hermes/plugins/product_creative/scripts/verify_runtime_boundaries.ps1
./.hermes/plugins/product_creative/scripts/verify_provider_boundaries.ps1
./.hermes/plugins/product_creative/scripts/verify_product_brain_boundaries.ps1
./.hermes/plugins/product_creative/scripts/verify_artifact_boundaries.ps1
./.hermes/plugins/product_creative/scripts/verify_schema_boundaries.ps1
./.hermes/plugins/product_creative/scripts/verify_tool_boundaries.ps1
./.hermes/plugins/product_creative/scripts/verify_cli_boundaries.ps1
./.hermes/plugins/product_creative/scripts/verify_agent_runtime_loop.ps1
./.hermes/plugins/product_creative/scripts/verify_m4_image_productization_loop.ps1
./.hermes/plugins/product_creative/scripts/verify_m5_video_generation_execution.ps1
./.hermes/plugins/product_creative/scripts/verify_m7_9_full_validation.ps1
./.hermes/plugins/product_creative/scripts/verify_m8_closeout.ps1
```

Live provider and sidecar tests are separate opt-in suites because they require credentials, logged-in browser state, network access, and possible external cost.
