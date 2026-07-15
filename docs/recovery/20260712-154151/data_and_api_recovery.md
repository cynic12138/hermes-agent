# Data and API Recovery

## 数据模型

SQLite：`<workspace>/.hermes/product_creative/runtime.sqlite3`；启用 foreign keys、WAL、FULL synchronous、30s busy timeout（`database.py:19-37`）。

主要表：

- 产品/认知：`products`、`product_brain_versions`、`generation_snapshots`。
- 工作流：`workflow_instances`、`workflow_steps`、`workflow_events`、`product_leases`。
- 幂等/异步：`command_receipts`、`outbox_events`、`provider_tasks`、`mock_provider_effects`。
- 学习：`rule_candidates/evidence/conflicts`、`writeback_proposals`、`proposal_updates`。
- 产物：`artifact_records`、`material_records`。
- 迁移/恢复：`migration_backups`、`legacy_imports`、`confirmations`、`recovery_events`。

证据：`.hermes/plugins/product_creative/infrastructure/sqlite/migrations.py:17-470`。

## API

基础前缀：`/api/plugins/product_creative/v1`。

- 查询：health、products、snapshot、review queue、workflows/detail、assets、learning、media。
- 命令：proposal decision、Brain rollback、workflow retry/cancel、provider refresh、rule revoke。
- 工作区新增：media descriptor/thumbnail。
- M9.1 宿主新增：`/api/desktop/plugins` 与 `/{name}/bundle`（未提交）。

全部 Product Creative API 要求 `X-Hermes-Workspace-Root`；命令支持确认、trace、optimistic version 和 HTTP 409/428（`dashboard/plugin_api.py:31-170`）。

## 外部依赖与门禁

环境变量仅列名称：

- `HERMES_HOME`
- `PRODUCT_CREATIVE_ENABLE_LLM`
- `PRODUCT_CREATIVE_DISABLE_LLM`
- `PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER`
- `PRODUCT_CREATIVE_ENABLE_EXTERNAL_PROVIDER`
- `PRODUCT_CREATIVE_MAX_DATA_URL_BYTES`
- `PRODUCT_CREATIVE_ARK_API_KEY`
- `PRODUCT_CREATIVE_GENERIC_IMAGE_ENDPOINT`
- `PRODUCT_CREATIVE_GENERIC_IMAGE_API_KEY`
- `PRODUCT_CREATIVE_GENERIC_IMAGE_MODEL`

真实 provider 还需要 endpoint/model/credential/readiness/显式确认。可选依赖包括 FastAPI web extra、Pillow、ffmpeg、XHS/Douyin sidecar。无 Product Creative 专属 MCP、向量库、外部消息队列或 cron。

## Mock/真实边界

- 默认 durable outbox worker 使用 `MockProviderGateway`。
- generic HTTP image、Ark image/VLM/async video 有 live 登记；其他多个 provider 是 `mock_only`。
- sidecar 服务不在仓库，登录态/风控状态 UNKNOWN。

## 风险

- `X-Hermes-Workspace-Root` 未证明绑定到 Desktop 当前 workspace 白名单。
- media descriptor 向 renderer 暴露绝对路径。
- thumbnail 将最多 8MiB 文件整体读入并 base64。
- 历史 workspace 是否全部迁移到 SQLite UNKNOWN。
- 未发现/未输出实际密钥；仓库防护要求 `.env`、DB、产品数据和 artifacts 不进入分发。
