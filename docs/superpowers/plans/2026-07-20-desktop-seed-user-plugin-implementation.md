# Desktop Seed User Plugin Implementation Plan

> **Execution mode:** Execute inline on `product-creative-rebaseline-20260716`. The user explicitly prohibited sub-agents and approved work on this branch.

**Goal:** Make a freshly installed, packaged Hermes Desktop validate, install, and enable the reviewed Product Creative distribution as a user plugin before the backend starts, without modifying the user's existing Hermes installation.

**Architecture:** Keep `.hermes/plugins/product_creative` as the only source tree. A cross-platform exporter produces a validated distribution, a generic Desktop build step stages declared seed plugins into package resources, and a generic bootstrap installer validates and atomically copies those payloads into the isolated `HERMES_HOME/plugins` directory before the existing bootstrap completion marker. The existing Hermes CLI/config and authenticated Desktop plugin registry remain the only enablement and runtime surfaces.

**Stack:** Python 3.11+, Node.js 22, Electron 40, CommonJS bootstrap modules, PowerShell installer, pytest, Node test runner, Electron Builder/NSIS.

**Global constraints:** Preserve `.t/` and `.test-tmp/`; never touch `C:\Users\1\AppData\Local\hermes`; no main merge, tag, release, provider call, XHS/Douyin access, or Product Brain write. Networked fresh-install verification must be announced first and use only the approved process-scoped `127.0.0.1:7897` proxy.

---

## Task 1: Preserve the fresh-install environment isolation fixes

**Files:**

- Modify: `scripts/install.ps1`
- Modify: `apps/desktop/scripts/test-desktop.mjs`
- Modify: `tests/test_install_repository_override.py`

1. Keep the already-written tests that require `HERMES_DESKTOP_TEST_MODE=fresh-install` to suppress user-scope environment writes and to isolate the Playwright cache.
2. Run `python -m pytest tests/test_install_repository_override.py -q` with a safe temp root and confirm all five tests pass.
3. Run PowerShell parser validation and `node --check apps/desktop/scripts/test-desktop.mjs`.
4. Commit only these three files as the environment-isolation fix.

## Task 2: Provide one cross-platform Product Creative distribution exporter

**Files:**

- Create: `.hermes/plugins/product_creative/scripts/export_distribution.py`
- Modify: `.hermes/plugins/product_creative/scripts/export_distribution.ps1`
- Create: `.hermes/plugins/product_creative/tests/test_distribution_export.py`

1. Write failing tests for an export that includes reviewed source plus generated Desktop bundles, excludes runtime/generated/secret/media content, writes `SOURCE.json`, and produces the same payload hash contract as `validate_distribution.py`.
2. Implement the Python exporter with explicit source/output root containment checks, Git tracked-plus-untracked-nonignored enumeration, version consistency, bundle build invocation, metadata generation, and final validator invocation.
3. Reduce the PowerShell exporter to a compatibility wrapper that invokes the Python implementation with the same `OutputDirectory` and `ExpectedVersion` interface.
4. Run the new exporter tests and an actual temporary Product Creative export validated against version `9.1.0-alpha.1`.
5. Commit exporter, wrapper, and tests.

## Task 3: Stage declarative seed plugins during Desktop packaging

**Files:**

- Create: `apps/desktop/seed-plugins.json`
- Create: `apps/desktop/scripts/stage-seed-plugins.cjs`
- Create: `apps/desktop/scripts/stage-seed-plugins.test.cjs`
- Modify: `apps/desktop/scripts/run-electron-builder.cjs`
- Modify: `apps/desktop/package.json`

1. Write failing Node tests for config schema, safe names and paths, exporter failure, missing/mismatched metadata, symlink rejection, and generated package-manifest contents.
2. Add a declarative config containing Product Creative's source exporter and expected version, while keeping runtime code product-agnostic.
3. Implement staging into `apps/desktop/build/seed-plugins/<name>` and generate schema-versioned `manifest.json` using only validated `SOURCE.json` metadata.
4. Invoke staging before Electron Builder and add `build/seed-plugins` to `extraResources` as `seed-plugins`.
5. Run the new tests and a real staging pass; verify manifest version, source commit, Desktop SDK version, and payload SHA-256.
6. Commit the build-time staging changes.

## Task 4: Implement the generic first-launch seed installer

**Files:**

- Create: `apps/desktop/electron/seed-plugin-installer.cjs`
- Create: `apps/desktop/electron/seed-plugin-installer.test.cjs`

1. Write failing tests for absent manifest no-op, malformed manifest, unsafe name/path, root escape, symlink, forbidden file type/content, oversized files, hash mismatch, plugin identity/version mismatch, successful atomic install, idempotent reinstall, conflicting existing plugin preservation, enable failure rollback, and receipt creation.
2. Implement schema and payload validation with no URL/network input and no product-specific branch.
3. Copy through a sibling temporary directory and atomically rename into `<HERMES_HOME>/plugins/<name>`.
4. Enable through an injected command runner in tests and the installed Hermes venv CLI in production using `plugins enable <name> --no-allow-tool-override`.
5. Write a non-secret receipt containing only name, version, hash, source commit, and timestamp.
6. Run the focused Node tests and commit the installer.

## Task 5: Insert seed installation before bootstrap completion

**Files:**

- Modify: `apps/desktop/electron/bootstrap-runner.cjs`
- Modify: `apps/desktop/electron/bootstrap-runner.test.cjs`
- Modify: `apps/desktop/electron/main.cjs`
- Modify: `apps/desktop/scripts/test-desktop.mjs`

1. Write failing tests proving the seed operation runs after `config-templates` and before `bootstrap-marker`, and that failure prevents both marker stage and Desktop completion marker.
2. Pass `process.resourcesPath/seed-plugins` from `main.cjs` to the runner only for packaged resources.
3. Inject `desktop-seed-plugins` into the runner at the required ordering boundary, using the installed active-root venv and isolated `HERMES_HOME`.
4. Extend packaged-resource validation to require and hash-check seed resources.
5. Run bootstrap runner, seed installer, build-stamp, and package-validation tests.
6. Commit the bootstrap integration.

## Task 6: Run the complete local regression and create a reachable clean build ref

**Files:** Verification only, then generated ignored `apps/desktop/build/**`, `apps/desktop/dist/**`, and `apps/desktop/release/**`.

1. Run Python distribution/API tests, Desktop bundle/routes/registry/page/plugin UI tests, typecheck, production renderer build, seed tests, bootstrap tests, and `git diff --check`.
2. Confirm `git status` contains only intended tracked changes plus preserved `.t/` and `.test-tmp/`.
3. Update any failing implementation in the owning task and rerun its RED/GREEN proof.
4. Commit remaining test/build integration changes and push only `product-creative-rebaseline-20260716` so the install stamp can pin a reachable clean commit.
5. Rebuild the Windows NSIS installer from that clean commit and confirm `install-stamp.json` has `dirty: false`, the correct repository, branch, and commit.

## Task 7: Perform the announced isolated fresh-install E2E

**Files:** Temporary sandbox under `C:\tmp`; no repository source edits.

1. Before any network call, tell the user that the process-scoped `127.0.0.1:7897` proxy will be used.
2. Snapshot user-level `PATH`, `HERMES_HOME`, and `HERMES_GIT_BASH_PATH`; record the formal Hermes path without modifying it.
3. Launch the rebuilt NSIS result with a new isolated Desktop `userData`, `HERMES_HOME`, workspace, Playwright cache, and logs.
4. Wait for asynchronous bootstrap and backend readiness; do not treat process launch as completion.
5. Prove the complete chain: exact pinned repository commit, seed receipt, user-plugin directory, enabled config, `/api/desktop/plugins` entry, verified bundle response, `/product-creative` route mount, and workspace-scoped Product Creative API response.
6. Stop only sandbox processes and compare the user environment snapshot byte-for-byte. Preserve diagnostics if verification fails.

## Task 8: Update durable project knowledge and finish the branch

**Files:**

- Modify: `AGENTS.md`
- Modify: `docs/PROJECT_STATE.md`
- Modify: `docs/AI_HANDOFF.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md`
- Create: `docs/M15_PACKAGED_SEED_PLUGIN_ACCEPTANCE_20260720.md`

1. Record architecture, security boundary, exact files, hashes, commands, test results, sandbox path, known limits, and recovery procedure.
2. Mark M15 complete only if Task 7 passes and the formal Hermes environment is unchanged; otherwise record the exact remaining gate.
3. Keep M14 live dynamic-media acceptance as a separate unresolved gate.
4. Run cross-reference checks, `git diff --check`, targeted regression tests, typecheck, and production build one final time.
5. Commit documentation, push only the approved feature branch, and report the full diff, commits, verification evidence, and remaining real acceptance items. Do not merge, tag, or release.
