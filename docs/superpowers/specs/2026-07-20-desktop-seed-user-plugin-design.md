# Desktop Seed User Plugin Design

Date: 2026-07-20

Branch: `product-creative-rebaseline-20260716`

Status: approved direction; implementation pending

## Context

The M15 Windows fresh-install test proved that the packaged Desktop shell can bootstrap the repository pinned by `install-stamp.json`, install dependencies, write the completion marker, and start the Hermes backend. The clean runtime still returns zero entries from `GET /api/desktop/plugins` because Product Creative exists only as repository source under `.hermes/plugins/product_creative`. Desktop correctly refuses executable project plugins and only loads enabled bundled or user plugins.

The installer must therefore turn a reviewed Product Creative distribution into an enabled user plugin before the backend starts. It must not add Product Creative routes or business APIs to Hermes core, fetch a second repository during first launch, or create another maintained source tree.

## Scope decision

`IN_SCOPE`: M15 is not complete until a clean Desktop install exposes the Product Creative page and backend API. The change is limited to generic Desktop distribution/bootstrap infrastructure plus Product Creative packaging metadata.

Out of scope:

- changing Product Creative business behavior, Product Brain, database schemas, providers, or media generation;
- treating project plugins as trusted Desktop executable plugins;
- merging main, tagging, releasing, or updating the independent distribution repository;
- changing the user's installed Hermes, global Git configuration, system proxy, hosts, or DNS.

## Redundancy decision

`EXTEND` existing mechanisms:

- tracked-only Product Creative distribution export;
- `SOURCE.json`, payload SHA-256, Desktop bundle SHA-256, version checks, and sensitive-data validation;
- Desktop bootstrap stage protocol and completion marker;
- Hermes user-plugin directory and `plugins.enabled` configuration;
- authenticated Desktop plugin discovery and bundle APIs.

No second plugin registry, updater, enable list, or Product Creative-specific host route will be created.

## Selected architecture

### 1. Declarative build input

Desktop owns a small seed manifest that names each plugin to ship and points to its existing exporter. Product Creative is the first entry. Runtime code consumes only the generated package manifest and has no Product Creative name or path hardcoded in its control flow.

The source of truth remains:

```text
.hermes/plugins/product_creative
```

The independent `hermes-product-creative` repository remains a generated publication target and is not contacted by first launch.

### 2. Build-time staging

A generic staging script exports configured plugins into:

```text
apps/desktop/build/seed-plugins/<plugin-name>/
```

Product Creative reuses its existing export and validation rules. The PowerShell exporter becomes a compatibility wrapper around a cross-platform Python exporter so CI and local release builds use one implementation.

After export, the staging script writes:

```text
apps/desktop/build/seed-plugins/manifest.json
```

Each entry contains only validated metadata:

- plugin name and version;
- relative payload path;
- payload SHA-256;
- Desktop SDK version;
- source repository and source commit.

Electron Builder copies the entire staged directory to `resources/seed-plugins`. Missing, invalid, dirty-version, unsafe-path, symlinked, oversized, or hash-mismatched seed payloads fail the build.

### 3. Generic first-launch installer

The Desktop bootstrap runner checks for `resources/seed-plugins/manifest.json`. When present, it inserts a generic `desktop-seed-plugins` operation after configuration templates exist and before `bootstrap-marker` runs.

For each entry it:

1. validates schema version, name, version, relative path, root containment, file types, size, and payload hash;
2. validates `plugin.yaml` identity and version against the package manifest;
3. refuses symlinks and refuses to overwrite a different existing user plugin;
4. copies into a sibling temporary directory under `HERMES_HOME/plugins`;
5. atomically renames it to `HERMES_HOME/plugins/<name>`;
6. enables it through the existing Hermes plugin configuration command;
7. writes a non-secret installation receipt under `HERMES_HOME` containing name, version, hash, and install time.

If the exact same payload already exists, installation is idempotent and only verifies that it is enabled. If any seed fails, bootstrap fails closed before the completion marker. A retry may safely continue; it must not delete or overwrite a user-modified plugin.

### 4. Trust boundary

Seed plugins are trusted executable code shipped inside the signed/stamped Desktop package. They become normal enabled user plugins and continue through the existing backend/API discovery gates. Project plugins remain excluded from executable Desktop and backend loading.

The package manifest is not an online catalog and cannot install arbitrary URLs. First launch performs no additional plugin network fetch.

### 5. Isolation

`HERMES_DESKTOP_TEST_MODE=fresh-install` must never persist user-level `PATH`, `HERMES_HOME`, `HERMES_GIT_BASH_PATH`, or portable Node/Git paths. Playwright browsers are stored under the test sandbox. The fresh-install harness records and compares user environment values before and after the run.

The acceptance sandbox uses a new `C:\tmp\...` root with isolated Electron user data, `HERMES_HOME`, workspace, configuration, user plugins, and logs. It never reads credentials or the installed Hermes at `C:\Users\1\AppData\Local\hermes`.

## Error behavior

- Missing seed manifest: normal upstream Hermes behavior; no plugins are seeded.
- Invalid manifest or unsafe path: stop bootstrap with a diagnostic error.
- Hash or identity mismatch: stop before copying and before the marker.
- Existing different plugin: stop and preserve it unchanged.
- Copy failure: remove only the newly created temporary directory.
- Enable failure after a new copy: remove only that new copy and report failure.
- Retry after interruption: accept an exact verified payload, repair enable state, and continue.
- Network failure while cloning the pinned Hermes repository: report the failing stage; do not fall back to another repository or commit.

## Verification

Automated verification must cover:

- build manifest schema, unsafe paths, name/version/hash mismatch, forbidden content, and symlinks;
- generic seed installer success, idempotency, collision refusal, rollback, and marker ordering;
- fresh-install environment isolation and Playwright cache isolation;
- packaged resource presence and hash consistency;
- existing Desktop bootstrap, bundle, registry, route, Product Creative UI/API, typecheck, and production build regressions.

The final clean-machine-style test must prove this chain from a new sandbox:

```text
packaged Desktop
→ bundled install.ps1
→ pinned cynic12138/hermes-agent commit
→ isolated runtime
→ packaged seed validation
→ enabled user plugin
→ backend ready
→ /api/desktop/plugins lists product_creative
→ bundle loads
→ /product-creative route mounts
→ workspace-scoped Product Creative API responds
```

No provider credentials, real media generation, XHS/Douyin access, production API, or Product Brain write is part of this acceptance test.

## Completion state

This work is complete only after the rebuilt NSIS package passes the full isolated chain and the user's formal Hermes environment is unchanged. The result remains unmerged, untagged, and unreleased. Commit and push are limited to `origin/product-creative-rebaseline-20260716` under the user's existing authorization.
