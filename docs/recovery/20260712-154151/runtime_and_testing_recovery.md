# Runtime and Testing Recovery

## 工具链

- Python `>=3.11,<3.14`；当前 `3.13.9`。
- Node 当前 `24.15.0`；CI 使用 Node 22，存在环境差异。
- npm `11.13.0`；PowerShell 5.1。
- `.venv` 存在；`uv` 未发现。

## 正确入口

- 用户插件安装：`hermes plugins install cynic12138/hermes-product-creative --enable`。
- 开发 chat：`powershell -ExecutionPolicy Bypass -File .hermes/plugins/product_creative/scripts/start_hermes_product_creative_dev.ps1`（会临时修改并恢复 config，不属于纯只读）。
- Desktop dev/build：`npm.cmd --prefix apps/desktop run dev|build`。
- M9 验证：`verify_m9_review_recovery.ps1`、`verify_public_surface_golden.ps1`。
- 上游 Hermes 规则要求 Python 测试优先使用 `scripts/run_tests.sh`；Windows 需在可用 Bash 环境执行。

## 已有覆盖

- 64 个 Product Creative PowerShell 验证脚本，覆盖 M0–M9、provider、安全、schema、tool、runtime、artifact 边界。
- M9 API 用 FastAPI TestClient + TemporaryDirectory。
- M9.1 工作区新增 Node bundle test、registry Vitest、FastAPI desktop plugin page test。
- 无统一 coverage 报告；不能证明 80% 行覆盖。

## 恢复阶段安全验证

- PASS：`node --test apps/desktop/electron/desktop-plugin-bundle.test.cjs`（2 tests）。
- PASS：两个 JS 文件 `node --check`。
- PASS：3 个 Python 文件 AST parse。
- PASS：`git diff --check`（仅 CRLF 提示）。

未执行 Desktop 完整 build/typecheck、M9 DB 测试、bundle/export、启动或 provider 调用，因为会写产物/配置、依赖未对齐或可能触发外部副作用。

## 可交付状态

- M9 backend/runtime：可开发、可测试，具备演示基础。
- M9 固定 Desktop 页面：已提交但正被替换（DEPRECATED direction）。
- M9.1：PARTIAL，尚未完整 build/E2E/提交。
- production provider：PARTIAL/BLOCKED，依赖外部条件。

最小后续验证：对齐 Node 22 → Python/Node focused tests → Desktop typecheck/build → user-plugin 安装的隔离 workspace E2E；真实 provider 单独 opt-in。
