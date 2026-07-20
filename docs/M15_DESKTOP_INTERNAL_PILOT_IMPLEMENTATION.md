# M15 Desktop 内部试用版实施与恢复记录

## 1. 身份与状态

- 初始实施：2026-07-17；方案 A 收口：2026-07-20（Asia/Shanghai）
- 分支：`product-creative-rebaseline-20260716`
- M11–M15 实现与测试提交：`25e26df`；首次安装修复：`4f74ef3`
- 插件版本：`9.1.0-alpha.1`
- 状态：`PILOT_REF_AVAILABLE / INSTALLER_REBUILT / FRESH_INSTALL_NETWORK_BLOCKED / UNPUBLISHED / INTERNAL_OPERATOR_ACCEPTANCE_PENDING`
- 源码真源：`.hermes/plugins/product_creative/`
- 外部分发仓库仍是生成目标，不是业务源码真源。

M15 的目标是让不熟悉 Prompt、CLI 和 task ID 的内部运营人员，从 Hermes Desktop 完成产品建立、环境检查、自然语言创作入口、任务恢复、三次关键审阅和反馈。M15 不替代 M14 的真实动态样片 Gate；M14 Live Gate 仍因 Codex 租户级外部披露策略而独立保持 pending。

## 2. 范围与复用结论

- Scope Gate：`IN_SCOPE`。M15 是当前路线图中的内部试用阶段。
- Redundancy Review：`EXTEND/REFACTOR_EXISTING`。
- 复用既有 Desktop Plugin SDK、plugin-owned 页面、dashboard API、Command Bus、Creative Task、Review/Recovery、workspace header 和确认审计。
- 没有新增第二套 Agent loop、任务数据库、Provider、Product Brain schema、宿主专属 Product Creative 路由或大型创作画布。
- Hermes chat 仍是执行入口；Desktop 是引导、状态、审阅和恢复工作台。

## 3. 迁移前后用户流程

### 迁移前

```text
先在 Hermes 对话中知道产品 ID/任务意图
→ Product Creative Desktop 主要查看五个视图
→ 恢复任务时需要理解内部 task ID
→ 环境问题需人工检查变量、Sidecar 和媒体工具
```

### M15 后

```text
打开 Product Creative
→ 没有产品时填写产品名称和可选描述
→ 描述进入 Evidence/Draft，不自动污染 Canonical Brain
→ Overview 输入自然语言目标或选择预设
→ Hermes chat 带入当前产品上下文并执行既有 Agent Runtime
→ Tasks 一键继续中断任务，无需复制 task ID
→ Review 按产品事实/创意方向/成片质量审阅
→ Settings 查看安全诊断和可选来源状态
```

主图和材料仍通过 Hermes chat 的现有附件能力进入，不在 M15 新增可读取任意本地路径的插件文件选择器。

## 4. 后端契约

### `POST /api/plugins/product_creative/v1/products`

- 输入：`name`、可选 `product_id`、可选 `description`。
- 复用 `product_workspace_resolve(create_if_missing=True)` 创建当前 workspace 产品。
- 可选描述经 `product_ingest` 进入 Evidence/Draft。
- 返回 `canonical_brain_changed: false`；不会自动确认 Product Brain 字段。
- 空名称/过长字段返回 422；当前 workspace 精确重名返回 409，且不摄入新描述。
- 不调用网络、LLM 或 Provider。

### `GET /api/plugins/product_creative/v1/diagnostics`

- 只读检查插件 runtime、豆包凭据存在性、可选 DeepSeek/SiliconFlow 凭据、real-provider gate、ffmpeg/ffprobe 和固定 loopback Sidecar 健康。
- `DOUBAO_API_KEY` 是豆包图片、VLM 和视频能力的最高优先凭据。
- XHS `127.0.0.1:8787`、Douyin `127.0.0.1:8000` 仅作短超时本机健康检查，不能传入任意 URL。
- XHS/Douyin 离线返回 `OPTIONAL_OFFLINE`，不会阻断普通创作。
- API 仅返回是否配置/是否可用，不返回凭据值，也不调用真实 Provider。

## 5. Desktop 工作台

### Onboarding

- 无产品 workspace 显示产品名称、可选产品 ID、可选描述表单。
- 说明描述只进入 Evidence/Draft。
- 可直接进入聊天补充当前包装、主图和产品资料。
- 创建后自动选择新产品并重新读取当前 workspace。

### 自然语言任务与恢复

- Overview 支持自由目标和“今日产品视频/产品图片/继续了解产品”预设。
- Desktop 把原始用户目标、当前产品名称和内部 product ID 交给 Hermes chat。
- Tasks 的“继续任务”在内部携带 task ID 和幂等恢复要求，用户不需要复制或理解 ID。

### 三个运营审阅节点

1. 产品事实：Readiness、关键问题和阻塞原因。
2. 创意方向：候选、选择理由、Story/Production Bible 和 Preflight QA。
3. 成片质量：Media QA、失败证据、Repair/Human Override。

三个节点是现有 durable artifact 的投影，不增加平行持久状态。所有 Product Brain proposal、rollback、rule revoke、workflow retry/cancel 和媒体质量决定继续走既有 reason、confirmation ID、receipt 和 event 门禁。

### Settings

- Provider/model credentials：只显示配置状态。
- Media runtime：显示 ffmpeg/ffprobe 可用性。
- Optional inspiration sources：XHS/Douyin 明确标为可选。
- 可刷新诊断或进入 Hermes 通用 Settings；本页不写系统环境变量。

### 隔离、语言与 cleanup

- 产品选择按 `workspaceRoot` 保存，重挂载其他 workspace 时重新读取产品、任务和诊断。
- `zh-CN` 归一化为简体中文；缺少的本地化字段回退英文。
- mount cleanup 终止轮询、清空 DOM，并使残留旧事件处理器 fail closed。

## 6. 调用链与信任边界

```text
Desktop plugin-owned bundle
→ authenticated same-origin plugin API
→ workspace ContextVar/header
→ Product Creative Command Bus / Query Services
→ SQLite durable state + workspace artifacts

Desktop task composer
→ host.continueInChat(...)
→ Hermes chat / Agent Runtime
→ existing Product Creative tools and durable workflows
```

- enabled bundled/user plugin 是 Desktop SDK v1 的受信任同源代码；project plugin 仍不能注入 executable page/backend API。
- workspace 数据不进入插件安装目录；分发包不包含 SQLite、产品素材、Prompt、Cookie、Token 或个人数据。
- Settings 诊断不能扩大外部授权；付费调用、Cookie、Product Brain 写回继续遵守既有门禁。

## 7. 源码、生成物与分发证据

- UI 源码：`.hermes/plugins/product_creative/desktop_ui/index.js`
- 生成 bundle：`.hermes/plugins/product_creative/dashboard/dist/desktop.js`
- bundle SHA-256：`8291e28588ca06d5a1613c05f30699032540ff42c33b5dfce2694ed60adf9937`
- 最终临时分发目录：`C:\data\work file\hermers-agent for me\m15-dist-20260717-1658`
- 分发 payload SHA-256：`155dbe5021b7af2f89edcf3349444528c690f9dbcf42f5df291c9d66af0eba9d`
- 分发 source commit：`0aa95637213f02eca2ef8f619daaf771150a7e11`（dirty worktree，不能用于正式发布）
- Windows Desktop 壳构建产物：`apps/desktop/release/Hermes-0.17.0-win-x64.exe`
- 首次安装修复后的安装器大小：117,691,265 bytes
- 首次安装修复后的安装器 SHA-256：`283733CDCE6EA31EB87AADD8CD3C7C6CD81715241A1E7AC70ACF5BA79B1AC381`
- install stamp commit：`4f74ef396fc75600e049f82bfe778d67bc15633a`
- install stamp：repository `cynic12138/hermes-agent`、branch
  `product-creative-rebaseline-20260716`、`dirty=false`、source `local`

该文件复用现有 Hermes Desktop Electron/NSIS 薄安装管线。第一次受限构建因不能创建 `%LOCALAPPDATA%\electron-builder` 缓存而失败；取得本机缓存写权限后成功。cleanup 修复后又重新构建并重新计算上述哈希，避免交付旧 renderer。

重要边界：NSIS 仍是薄 Desktop 壳，但 `4f74ef3` 将受校验的 `install.ps1/install.sh` 作为
`extraResources/bootstrap` 随包分发，并在 stamp 中加入 GitHub `owner/repository`。bootstrap 优先使用
包内脚本，再按 `cynic12138/hermes-agent@commit` 克隆 runtime；GitHub Raw 仅保留给旧包的兼容回退。
fresh-install 仍必须完成固定 runtime、enabled Product Creative user plugin 和 backend 启动，不能仅凭
干净 stamp、包内脚本和安装器文件关闭门禁。

## 8. 实际验证

- M15 backend：`6 passed`。
- Product Creative Desktop bundle：Task 7 RED 证明 cleanup 后旧事件仍可执行；修复后 `11 passed`。
- Desktop routes/registry/page/Product Creative：2026-07-20 定向复验 `25 passed`（5 files）。
- 分发 bundle：`1 passed`（从新导出目录加载）。
- Desktop bundle security：`2 passed`。
- M10–M15、来源、分发和 Desktop backend：2026-07-20 使用项目 `.venv`、清空真实凭据/
  Provider 开关并以短路径 `C:\tmp\m15-precommit-venv-20260720` 复验，`207 passed / 0 failed`
 （8 files，94.9 秒）。Windows 没有可用 WSL，故直接使用 canonical runner
  `scripts/run_tests_parallel.py`；未调用外部 API。
- M9 review/recovery：`25/25`。
- public surface：`84 tools / 84 CLI`，golden hash 一致。
- TypeScript typecheck：通过。
- Desktop production build：通过。
- 首次安装仓库/包内脚本 TDD：RED 分别证明 stamp repository 被忽略、非法 repository 未拒绝、
  包内脚本未使用；修复后 bootstrap/build-stamp `11 passed`，Windows/POSIX installer repository
  contract `2 passed`，PowerShell `-Manifest -Repository cynic12138/hermes-agent` 实际返回成功。
- Desktop platforms：`286 passed / 3 failed / 2 skipped`；3 项为既有 Windows 环境差异（Linux
  unpacked 路径期望和本机 Bash launcher 不可用），本次 bootstrap 测试全部通过，未顺带修改。
- 分发版本、哈希和敏感扫描：通过。
- enabled user-plugin 离线安装：新导出目录
  `C:\data\work file\hermers-agent for me\m15-precommit-dist-20260720-1005` 验证通过。
- Windows NSIS Desktop 壳构建：通过，并生成 blockmap。
- Packaged payload smoke validation：通过；确认 `install-stamp` 指向
  `cynic12138/hermes-agent@4f74ef396fc7`、`dirty=false`，包内 `bootstrap/install.ps1` 和
  `bootstrap/install.sh`、renderer，以及 Windows `conpty.node`、`conpty_console_list.node`、
  `pty.node` 均已打包。

### 本地打包形态隔离试运行

- 首次隔离目录 `C:\data\work file\hermers-agent for me\m15-pilot-20260717-1710` 因 sandbox 创建的插件目录无法被本机 Desktop 进程读取而失败，错误为 `WinError 5`；没有发生 bootstrap、联网或 Provider 调用。
- 使用本机权限重建隔离环境 `C:\data\work file\hermers-agent for me\m15-pilot-native-20260717-1720`，把临时分发安装为 enabled user plugin，并以打包 Desktop 壳显式指向当前 worktree runtime 后成功启动 backend。
- 认证 API 发现 `product_creative`；bundle 返回版本 `9.1.0-alpha.1`、API v1 和声明 SHA `8291e28588ca06d5a1613c05f30699032540ff42c33b5dfce2694ed60adf9937`。
- diagnostics 正确返回 `ACTION_REQUIRED`：隔离环境未配置凭据/Provider，XHS/Douyin 两项均为可选离线；没有泄露密钥。
- 在打包 backend 中创建隔离产品 `m15-pilot-product` 成功：产品数变为 1、Brain version 为 1、描述进入 Evidence，Canonical Product Brain 未改变且未泄漏描述。
- 该证据证明“打包 Desktop 壳 + 当前 worktree runtime + 已安装分发插件”的本地组合可运行；不证明薄安装器能在另一台干净机器自动取得未提交 runtime。
- Windows UI 自动操作权限请求超时，未形成运营人员可见页面的人工点击证据，也未盲目点击。

已知 warning：既有 CSS `text-*` 注释解析 warning、约 27 MB 主 chunk 体积 warning。最终安装器
stamp 为 clean；未顺带修复两个非 M15 build warning。

环境说明：离线安装探针首次误用全局 Anaconda Python，因其缺少项目已声明依赖
`python-multipart` 而在导入宿主 FastAPI 时失败；改用仓库现有 `.venv` 后原命令通过。
没有联网安装或升级依赖，该次环境失败不计为插件失败。

## 9. M15 修改文件（按职责）

### 诊断与 API

- `.hermes/plugins/product_creative/runtime/desktop_diagnostics.py`
- `.hermes/plugins/product_creative/dashboard/plugin_api.py`

### 插件 UI 与生成 bundle

- `.hermes/plugins/product_creative/desktop_ui/index.js`
- `.hermes/plugins/product_creative/dashboard/dist/desktop.js`（构建产物）

### 测试

- `tests/hermes_cli/test_product_creative_m15_desktop_pilot.py`
- `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`
- `apps/desktop/src/app/desktop-plugins/distribution-bundle.test.ts`
- `apps/desktop/electron/bootstrap-runner.test.cjs`
- `apps/desktop/scripts/write-build-stamp.test.cjs`
- `tests/test_install_repository_override.py`

### 首次安装与打包

- `apps/desktop/electron/bootstrap-runner.cjs`
- `apps/desktop/electron/main.cjs`
- `apps/desktop/scripts/write-build-stamp.cjs`
- `apps/desktop/scripts/test-desktop.mjs`
- `apps/desktop/package.json`
- `scripts/install.ps1`
- `scripts/install.sh`

### 设计、计划与长期知识

- `docs/plans/2026-07-17-m15-desktop-internal-pilot-design.md`
- `docs/plans/2026-07-17-m15-desktop-internal-pilot-implementation-plan.md`
- `docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md`
- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/AI_HANDOFF.md`
- `docs/ARCHITECTURE_CURRENT.md`
- `docs/DECISION_LOG.md`
- `docs/OPEN_QUESTIONS.md`
- `.hermes/plugins/product_creative/README.md`

## 10. 已知限制与未完成门禁

- **Fresh-install gate：**旧包三次因路由器 DNS 将 `raw.githubusercontent.com` 返回为 `0.0.0.0`
  而停止；公开 DNS 查询能返回正常地址，hosts/WinHTTP proxy 无异常。新包已移除该前置依赖并成功使用
  包内 `install.ps1`，通过 manifest、uv、Python、Git、Node 和 system-packages 阶段。随后 HTTPS
  shallow clone 连接到 `github.com:443`，但 45 秒观察窗口内仓库保持 27,443 bytes、没有 HEAD，
  因此安全停止隔离 Hermes 和 5 个 clone 子进程。未切换代理、镜像或写 hosts，待网络可持续传输后复验。
- **Operator acceptance gate：**内部运营人员尚未在可运行的 Desktop 形态中亲自完成一次 onboarding → 自然语言任务 → 审阅 → 恢复 → 反馈全链，因此 M15 不能标记为最终 DONE。
- 已在用户授权下两次执行 `test:desktop:fresh`：旧包暴露 Raw DNS 问题，新包证明包内 bootstrap
  和 fork 路由生效，但 HTTPS clone 未完成；两者都不得记为 fresh-install 通过。
  `test:desktop:existing` 仍未执行，因为它会读取并使用用户真实 Hermes 配置，需在人工试用时单独确认。
- M14 动态真实 Provider Live Gate 仍独立 pending；M15 UI 通过不能替代真实样片质量。
- 主图上传复用 Hermes chat attachment，不是 Product Creative 页内文件选择器。
- Settings 只诊断，不代替 Hermes 通用模型/凭据配置。
- XHS/Douyin 是补充灵感来源，不是核心创作依赖。
- 当前旧构建仍是通用 Hermes Desktop 壳，不是最终独立品牌 Creative Studio；新 pilot ref 已包含 Product Creative runtime。
- 正式媒体工具可移植性仍需在干净机器安装验收；当前构建使用既有 Hermes Desktop 依赖。
- M11–M15 实现与测试已提交并推送到 pilot branch；未合并 main、未 tag、未 release。

## 11. 内部运营人工试用脚本

前置条件：重建薄安装器，使 stamp 指向可获取且包含 M15 的最终 pilot HEAD。旧 EXE 单独安装不满足该条件。

1. 记录 Git ref、Desktop 壳和插件分发 SHA-256，在非生产 workspace 安装并启动 Hermes Desktop。
2. 打开 Product Creative；选择一个空 workspace。
3. 只输入产品名称和一段产品描述，确认页面明确说明描述未进入 Canonical Brain。
4. 在聊天中附加当前产品主图/包装图，完成必要字段确认。
5. 在 Overview 输入“帮我做一个今天能发的产品视频”。
6. 确认 Hermes 能识别产品、主动询问关键未知、生成任务计划；不要求运营人员提供 product ID 或 Prompt。
7. 在 Tasks 查看原始目标、阶段和阻塞；中断后点击“继续任务”，确认已完成/付费步骤不重复。
8. 在 Review 依次检查产品事实、创意方向和成片质量；记录每次通过/修改/拒绝原因。
9. 在 Assets 预览输入素材、镜头、合成结果和最终媒体。
10. 在 Settings 确认核心能力状态；关闭 XHS/Douyin 时普通创作仍可继续。
11. 切换到第二 workspace，确认产品、任务、素材、诊断和媒体不串库。
12. 提交一次长期学习候选，确认未确认前 Canonical Brain hash 不变；确认后才产生新版本/receipt/event。
13. 由内部产品/内容负责人记录可用性、质量标准和是否接受 M15。

## 12. 丢失工作区后的恢复顺序

1. 读取 `AGENTS.md`、`docs/AI_HANDOFF.md`、`docs/PROJECT_STATE.md` 和本文。
2. 确认分支、HEAD、dirty tracked/untracked 文件；不得 reset/stash/clean。
3. 以 `.hermes/plugins/product_creative/desktop_ui/index.js` 为 UI 真源，不从 `dashboard/dist` 反推源码。
4. 运行 `build_desktop_bundle.py`，核对 bundle identity、版本、大小与 SHA-256。
5. 运行 M15 backend、Product Creative UI、Desktop bundle、typecheck/build。
6. 运行 M10–M15、M9 recovery 和 public-surface 回归。
7. 导出到全新临时目录，执行 validator、enabled user-plugin 离线安装和 distribution bundle 测试。
8. NSIS 壳构建后核对 install stamp；只有 stamp 对应的可获取 ref 实际包含 M15 runtime，才可进行干净机器安装验收。
9. 正式提交、push、tag、release 以及远端可获取 ref 均必须先得到单独授权。

## 13. 提交前审计与建议分组

2026-07-17 在不修改 Git index 的前提下完成审计：

- tracked changed：39 个文件。
- untracked candidate：排除测试临时树后 57 个文件，其中 `.py` 24、`.md` 25、`.json` 8；没有超过 1 MiB 的文件。
- 明确排除：`.t/` 29,303 个测试文件、`.test-tmp/` 3,762 个测试文件。两目录属于受保护临时现场，不删除、不提交。
- 同样不提交 `apps/desktop/release/`、临时分发/试运行目录、workspace 数据或任何生成媒体。
- 对 96 个候选文件进行私钥、Provider key、JWT 和 literal secret 扫描。命中项均为测试 validator 的故意假 secret、fixture API key 或 `task-...` 标识被 `sk-` 规则误判；没有发现真实 API Key、Cookie、Token、密码或私钥。
- 对 59 个本次修改/新增的插件源码文件扫描本机绝对路径和“周十五/益生菌/蜂蜜露”等具体产品字面量，结果 0 命中；产品资料没有固化进通用插件源码。
- `git diff --check` 通过；仅有 Windows LF→CRLF 提示。

获得用户授权后建议形成两个可独立审阅的提交：

1. `feat(product-creative): complete professional creative production and desktop pilot`
   - `.hermes/plugins/product_creative/`
   - `apps/desktop/src/app/desktop-plugins/`
   - `tests/hermes_cli/test_product_creative_m11_artifacts.py`
   - `tests/hermes_cli/test_product_creative_m12_skills.py`
   - `tests/hermes_cli/test_product_creative_m13_media_production.py`
   - `tests/hermes_cli/test_product_creative_m14_media_qa.py`
   - `tests/hermes_cli/test_product_creative_m15_desktop_pilot.py`
   - 与分发/live/M10 直接相关的既有测试修改。
2. `docs(product-creative): record M11-M15 implementation and standalone gates`
   - `AGENTS.md`
   - `docs/` 下的方向、架构、状态、路线、计划、实施、审阅和 Live Gate 文档。

实际结果：实现与测试形成提交 `25e26df`，已推送到 `origin/product-creative-rebaseline-20260716`；长期知识文档作为后续独立提交。未合并 main、未 tag、未 release。
