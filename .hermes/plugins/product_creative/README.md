# Hermes Product Creative

`product_creative` is a durable, AI-driven Hermes plugin for long-running product content work. It keeps Product Brain versions, workflows, events, receipts, learning rules, and writeback proposals in SQLite while media and large artifacts remain in the product workspace.

M15 extends the user-plugin-owned Hermes Desktop console into a guided internal workbench. Operators can onboard a product, start or resume a natural-language creative task, inspect three review checkpoints, and diagnose the local runtime without using CLI payloads, prompt engineering, or task IDs. Execution still enters the existing Hermes chat/Agent Runtime rather than a parallel frontend workflow.

## Install

```powershell
hermes plugins install cynic12138/hermes-product-creative --enable
```

Restart the Hermes backend or Desktop after the first install so the trusted user-plugin API can be mounted. Update with:

```powershell
hermes plugins update product_creative
```

The plugin must be installed as a **user plugin** under `~/.hermes/plugins`. Hermes intentionally refuses to import backend Python APIs from project plugins.

## Workspace model

The M9 console uses the active Hermes Desktop workspace. Runtime data belongs to that workspace:

```text
<workspace>/.hermes/product_creative/runtime.sqlite3
<workspace>/.hermes/product_creative/products/<product-id>/
```

The user installation under `~/.hermes/plugins/product_creative` contains code only. It does not own product data. Every API request carries the current workspace root, which is canonicalized and scoped with `ContextVar`; the plugin never changes the process-wide working directory.

## M15 guided Desktop workbench

Open **Product Creative** from the Desktop sidebar or command palette.

- A workspace with no product shows safe onboarding. Optional descriptions enter Evidence/Draft and never become confirmed Product Brain facts automatically.
- **Overview** shows Product Brain/readiness, three operator checkpoints, and a natural-language creative task composer.
- **Tasks** shows durable workflows, steps, events, provider tasks, and one-click natural-language resume without exposing task IDs to operators.
- **Review queue** separates product truth, creative direction, and final media quality before accepting or rejecting controlled proposals.
- **Assets** lists registered materials and generated artifacts.
- **Learning** shows rules and Product Brain history, including controlled revoke and rollback.
- **Settings** reports credential presence, real-provider readiness, ffmpeg/ffprobe, and optional XHS/Douyin sidecar health without returning secret values.

XHS and Douyin are optional inspiration sources. Their absence does not block normal creation from Product Brain, local/history materials, and Web research. Product images and packaging materials are added through the existing Hermes chat attachment path.

Proposal decisions, Product Brain rollback, rule revoke, workflow retry/cancel, and provider-task refresh all pass through typed commands, policy checks, explicit confirmation, optimistic version checks, receipts, and audit events. Rollback creates a new immutable Brain version; it never rewrites history.

## Hermes LLM and providers

Set `PRODUCT_CREATIVE_ENABLE_LLM=1` to enable Hermes LLM planning where configured. Real provider execution remains separately gated by `PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1`, provider credentials, and explicit user confirmation. Never commit provider keys or Hermes configuration into this repository.

M9 provider refresh only refreshes an existing durable task projection. It does not start a new generation job.

## Backup and recovery

Before migrating an existing workspace, back up `.hermes/product_creative`. SQLite uses WAL, full synchronous writes, foreign keys, leases, idempotency receipts, and an outbox. Product Brain rollback and workflow recovery are additive, audited operations.

For diagnostics, inspect the console workflow/event timeline and runtime error artifacts first. Do not edit `runtime.sqlite3` directly while Hermes is running.

## Architecture

```text
Hermes Tool / CLI / Desktop
  -> Typed Command Bus / Query Services
  -> AI Controller + Policy + Confirmation
  -> Durable Workflow + Capability Registry
  -> Repository Ports
  -> SQLite + Artifact Filesystem + Provider Gateway
```

Capability descriptors own tool schema, action metadata, policy requirements, executors, workflow fragments, and events. Application and domain modules do not import SQLite or provider SDKs.

## Development

Run the focused M9 checks from the Hermes Agent repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .hermes/plugins/product_creative/scripts/verify_m9_review_recovery.ps1
powershell -ExecutionPolicy Bypass -File .hermes/plugins/product_creative/scripts/verify_public_surface_golden.ps1
```

The distribution repository is generated from `.hermes/plugins/product_creative`; do not maintain business code directly in the distribution repository. Every release records its source commit and publishes a SHA-256 checksum.

## Compatibility

M9.1 preserves all 78 M8 Hermes tools and CLI commands and adds six controlled recovery commands, for 84 total. Version `9.1.0-alpha.1` requires a Hermes Desktop build with Desktop Plugin SDK v1. The `/product-creative` page, translations, and UI bundle are delivered by this plugin; Hermes Desktop contains no Product Creative-specific route or component.

## Security and privacy

- The backend API is mounted only for explicitly enabled user plugins.
- Workspace and media paths are canonicalized and cannot escape the active workspace.
- Media is addressed by database record ID rather than arbitrary path input.
- Product data, prompts, artifacts, credentials, and runtime databases are excluded from distribution.
- External publication, billable provider calls, canonical material changes, and Product Brain mutation remain confirmation-gated.

## License and attribution

MIT. Product Creative is derived from and designed for [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent), which is also MIT licensed. See `LICENSE` in the distribution repository.
