# M15 打包种子插件与 Fresh-install 验收记录

## 1. 结论

- 日期：2026-07-20（Asia/Shanghai）
- 分支：`product-creative-rebaseline-20260716`
- 被验收源码提交：`a0081ddfbe966473b996f8f6e3a879ab6720888f`
- 插件版本：`9.1.0-alpha.1`
- 状态：`PACKAGED_FRESH_INSTALL_AND_PLUGIN_UI_ACCEPTED / UNPUBLISHED / INTERNAL_OPERATOR_FULL_FLOW_PENDING`
- 发布状态：未合并 `main`、未 tag、未 release；独立分发仓库未更新。

M15 的打包安装门禁已经关闭：新的 Windows NSIS 安装形态能在全新隔离环境中从固定 Git 提交安装 Hermes runtime，将 Product Creative 作为 enabled user plugin 安装，启动认证 backend，并在真实 Electron 中打开插件路由和五个核心视图。

M15 仍不能标记为最终产品验收完成。剩余门禁是由内部运营人员在已配置真实文本模型的安装形态中，亲自完成一次 onboarding → 自然语言任务 → 三节点审阅 → 中断恢复 → 反馈/学习全链。M14 真实动态视频与媒体 QA 是另一条独立质量门禁。

## 2. 打包身份

- 安装器：`apps/desktop/release/Hermes-0.17.0-win-x64.exe`（生成物，不提交 Git）
- 大小：`118184438` bytes
- SHA-256：`90BCE51012171CDD151FFFB2E782F351E89B86035A76627B04FEF79870EF7175`
- install stamp：repository `cynic12138/hermes-agent`、branch `product-creative-rebaseline-20260716`、commit `a0081ddfbe966473b996f8f6e3a879ab6720888f`、`dirty=false`
- seed payload SHA-256：`e75aeb88253b1ec55ea961345961ac7287d981ee2e1cff135a14211586657ad2`
- Desktop bundle SHA-256：`8291e28588ca06d5a1613c05f30699032540ff42c33b5dfce2694ed60adf9937`
- bundle 大小：`48352` bytes

源码 bundle、安装后 bundle、`SOURCE.json` 声明和认证 bundle API 返回的 SHA-256 一致。API 响应本身是包含源码和身份字段的 JSON，因此整个 HTTP body 的哈希不等于 bundle 源码哈希；验收比较的是响应中的 `source`/`sha256` 与落盘文件。

## 3. Fresh-install 环境与过程

- 沙箱：`C:\tmp\hermes-desktop-fresh-install-PFu67p`
- 隔离 Hermes home：`C:\tmp\hermes-desktop-fresh-install-PFu67p\hermes-home`
- 隔离 runtime checkout：`...\hermes-home\hermes-agent`
- 隔离插件目录：`...\hermes-home\plugins\product_creative`
- 代理：仅本次 fresh-install 进程使用 `127.0.0.1:7897`；没有写入用户级代理、PATH 或 Hermes 环境变量。

实际 bootstrap 结果：

1. 从 `cynic12138/hermes-agent` 获取固定提交 `a0081dd`。
2. 建立 Python 3.11 venv，安装 runtime 依赖、Node 依赖和 Playwright Chromium。
3. 验证 seed manifest、插件身份、路径、payload hash 和敏感内容。
4. 原子安装并启用 `product_creative@9.1.0-alpha.1`。
5. 写入不含密钥的安装回执。
6. backend 在隔离环境启动，实际端口为 `62526`。
7. 启动真实 Electron renderer，不使用浏览器替代桌面壳。

安装回执确认：

```text
name: product_creative
version: 9.1.0-alpha.1
payloadSha256: e75aeb88253b1ec55ea961345961ac7287d981ee2e1cff135a14211586657ad2
sourceCommit: a0081ddfbe966473b996f8f6e3a879ab6720888f
```

## 4. 真实运行时缺陷与修复

第一次真实 Electron 点击 Product Creative 后仍显示聊天页。根因不是插件安装失败，而是宿主的 `:sessionId` 动态路由先匹配了 `/product-creative`，把插件深链误判成聊天 session。

修复采用宿主通用路由判定，不添加 Product Creative 专属 core route：

- `apps/desktop/src/app/routes.ts` 统一判定当前路径属于内置路由、插件路由、加载态、错误态还是聊天 session。
- `apps/desktop/src/app/desktop-controller.tsx` 让 `:sessionId` 在渲染聊天前尊重插件 route surface。
- `apps/desktop/src/app/routes.test.ts` 增加动态插件路由回归。
- 修复提交：`a0081dd fix(desktop): render plugin routes before chat sessions`。

重新构建安装器并 fresh-install 后，Product Creative 能从侧栏和直接路径进入，不再被聊天路由吞掉。

## 5. 认证 API 验收

使用从本次 backend 首页注入的临时 session token 调用同源 API；token 未输出、未写入文档。

- `GET /api/desktop/plugins`：返回 `product_creative`、source `user`、version `9.1.0-alpha.1`、API v1、path `/product-creative`、entry `dist/desktop.js`。
- `GET /api/desktop/plugins/product_creative/bundle`：返回正确 name/version/API/entry、48352-byte source 和声明 SHA-256。
- `GET /api/plugins/product_creative/v1/diagnostics`：接受 `X-Hermes-Workspace-Root`，返回 `product_creative.desktop_diagnostics.v1`。

诊断结果：

- Product Creative runtime：`READY`。
- `DOUBAO_API_KEY`、`DEEPSEEK_API_KEY`、`SILICONFLOW_API_KEY`：只返回“已配置”，不返回值。
- ffmpeg/ffprobe：`READY`。
- real-provider：`ACTION_REQUIRED`，保持显式关闭。
- XHS/Douyin：`OPTIONAL_OFFLINE`，不阻断普通创作。
- safety：`external_provider_called=false`、`secret_values_returned=false`、`sidecars_are_optional=true`。

本次安装与 UI 验收没有调用真实 Provider、外部抓取或付费能力。

## 6. 真实 Electron 页面验收

在隔离 runtime workspace 中通过桌面 UI 创建项目 `M15 Packaged Acceptance`，再创建仅用于沙箱验收的产品 `M15 Acceptance Product`。该产品只存在于临时 workspace，不进入源码仓库或正式 Product Brain。

已实际打开并核对：

- Overview：显示 Product Brain V1、readiness/production 空态和自然语言任务入口。
- Tasks：显示 Creative Tasks 与 Durable Workflows 空态。
- Review：显示 Product Truth、Creative Direction、Final Quality 三节点及 proposal/result 空态。
- Assets：显示 Task-selected Inputs、Production Bible、Product Plate、Shot Outputs、Final Composite、Artifacts、Materials 空态。
- Learning：显示 Task Feedback Impact、Brain Versions（Version 1 / INITIAL）和 Rules 空态。

这证明 bundle → registry → route → mount → authenticated API → workspace-scoped read model 的实际桌面链路可用。没有用单元测试或直接 Python 函数替代该验收。

## 7. 隔离结论与后续修复

已确认：

- backend 日志、runtime、插件、workspace、Product Brain 和安装回执均位于 `C:\tmp` 沙箱。
- 隔离进程关闭后，属于该打包壳和沙箱 venv 的 Hermes/Python 进程数量为 0。
- 用户级 `HERMES_HOME`、`HERMES_GIT_BASH_PATH` 仍为空；用户 PATH 仍为 `C:\Users\1\AppData\Local\Microsoft\WindowsApps;`。
- 隔离日志中没有正式 Hermes 路径引用；正式数据库二进制中未检索到本次产品名或沙箱路径。

原未知风险已于同日后续修复关闭：

- fresh-install 现在必须提供位于系统临时目录内的 sandbox root、Electron `userData` 和 `HERMES_HOME`，缺少或越界即 fail closed。
- harness 同时传入 Chromium `--user-data-dir`，不再只依赖可选环境变量覆盖。
- 新打包壳正向实测中临时沙箱有 6 个运行写入，受保护的 37 个正式状态文件前后差异为 0，残留测试进程为 0。
- 历史时间戳变化的具体来源仍不可追溯；没有删除、回滚或覆盖正式目录。完整证据见 `docs/M15_FRESH_INSTALL_USER_DATA_ISOLATION_20260720.md`。
- 新建项目对话框在长目录路径下出现横向溢出，Create 按钮需要水平滚动才能看到。它不阻断插件链路，但属于内部运营 UX 缺陷。

## 8. 最终回归

在真实 fresh-install 完成后执行：

- Node bootstrap/seed/staging/stamp：`29 passed`。
- Desktop routes/registry/page/Product Creative/distribution：`25 passed`（5 files）。
- Python install repository/Desktop API/distribution/M15 backend：`32 passed`（4 files）。
- M9 review/recovery：`25/25`。
- public surface：`84 tools / 84 CLI`，golden hash 一致。
- TypeScript typecheck：通过。
- production build/NSIS：通过；安装器身份见第 2 节。

Python 回归的前两次尝试分别被系统临时目录权限和“测试输出位于源码仓库内”的安全门禁阻断；没有业务断言失败被掩盖。改用仓库外的全新短临时目录后，同一组测试 32/32 通过。测试期间真实凭据变量和 real-provider 开关均清空。

本机 Node 为 24.x；发布权威环境仍是 Node 22。Node 22 CI 尚需作为正式发布门禁运行，本机结果只能作为补充。

## 9. 剩余真实验收

1. 内部运营人员在安装版 Desktop 中配置真实文本模型，从自然语言建立/选择产品并启动一次 Creative Task。
2. 完成产品事实、创意方向、成片质量三节点审阅；验证中断后自然语言/按钮恢复不重复付费步骤。
3. 提交一次反馈和长期学习 proposal，确认未批准时 Canonical Brain 不变，批准后才产生新版本、receipt 和 event。
4. 在真实运营流程中验证主图附件、最终媒体预览和第二 workspace 隔离。
5. 独立完成 M14 动态 Seedance 样片、真实 VLM/OCR QA、返修和用户质量接受。
6. 在 Node 22 CI 运行 release workflow；之后仍需单独授权才能 tag/release 或更新独立分发仓库。

## 10. 恢复顺序

1. 读取 `AGENTS.md`、`docs/AI_HANDOFF.md`、`docs/PROJECT_STATE.md`、`docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md` 和本文。
2. 运行 `git rev-parse HEAD`；不要把本文记录的验收提交误当作永远最新 HEAD。
3. 核对 `apps/desktop/build/install-stamp.json`、`apps/desktop/build/seed-plugins/manifest.json`、插件 `SOURCE.json` 和 bundle hash。
4. 先运行 Node seed/bootstrap、Desktop 五文件、Python 四文件、M9 recovery、public surface 和 typecheck。
5. 重新构建 NSIS；记录安装器 hash，使用全新隔离 home/workspace/user-data 运行 fresh-install。
6. 在真实 Electron 中复验插件深链与五视图；不要只调用 backend。
7. 检查正式 Hermes 目录在验收前后的文件级变化；必须保持零差异。隔离修复与基准证据见 `docs/M15_FRESH_INSTALL_USER_DATA_ISOLATION_20260720.md`。
