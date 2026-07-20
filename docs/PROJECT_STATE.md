# Project State

- 日期：2026-07-20
- 分支：`product-creative-rebaseline-20260716`
- M11–M15 实现与测试提交：`25e26df`；长期状态文档提交：`5e87c86`；进入项目时运行 `git rev-parse HEAD` 重新确认当前提交
- M9.1 实现提交：`83b4e8f`
- M10 实现提交：`33d096f`
- 已提交阶段：M9.1 Desktop Plugin SDK 迁移（DONE、本地已提交）
- 当前阶段：M13.1/M14.1 动态镜头生产与动作质量门禁已达到
  `DONE_IN_PILOT_REF_UNPUBLISHED_LIVE_GATE_AND_USER_ACCEPTANCE_PENDING`
- M15 Desktop 内部试用状态：
  `PILOT_REF_AVAILABLE_UNPUBLISHED_INSTALLER_REBUILD_AND_OPERATOR_ACCEPTANCE_PENDING`
- 当前 Live Gate：`LOCAL_GATE_PASSED / EXPLICIT_EXTERNAL_DISCLOSURE_APPROVED / TENANT_POLICY_BLOCKED`；
  用户已明确授权，但 Codex 租户策略仍禁止外发 workspace 产品资料。本次调用数为 0。
  执行真源为
  `docs/M14_LIVE_GATE_20260717.md`
- 发布阶段：`origin/product-creative-rebaseline-20260716` 已建立；未合并 main、未 tag、未 release
- 工作区保护状态：原 `product-creative-runtime` 工作区未执行 clean/stash/reset/checkout；完整 patch、Git bundle、M0–M8、旧 runtime 和 pcbak 已归档并记录 SHA-256。

## DONE

- M0–M8 durable runtime 汇总基线（`1d223d3`；阶段细粒度历史不可恢复）。
- Product Brain、产品摄入、素材、文案、图片、视频、灵感、审阅、反馈/学习、exact-main-video。
- SQLite workflow/event/receipt/outbox/provider task/learning/recovery 数据模型。
- M9 backend、6 个受控恢复命令、HEAD 固定 Desktop 控制台（`f8bdb0c`）。
- Windows plugin clone 只读文件删除修复（`822d879`）。
- M9.1 通用 Desktop Plugin SDK v1：认证 discovery/bundle API、enabled bundled/user gate、project plugin executable page 禁止、路径/大小/哈希/API/版本/身份校验。
- 冷启动深链、完整宿主保留路由、bundle 注册事务隔离、loading/error 诊断、mount/cleanup 与 workspace/locale 重挂载。
- Product Creative plugin-owned Overview/Tasks/Review/Assets/Learning 五视图及确认原因门禁。
- `9.1.0-alpha.1` 版本统一、tracked-only 分发、`SOURCE.json` 双层哈希、敏感数据扫描、离线 enabled user-plugin 安装 E2E。
- Node `22.23.1` 定向 UI/typecheck/production build；M9 recovery 25/25、public surface 84 tools/84 CLI 回归通过。
- 发布 workflow 的 Desktop Vitest 调用已改为通过 `apps/desktop` 的 `test:ui` script 执行，避免从仓库根目录丢失 Vite alias 和 bundle 相对路径。
- M9.1 实施、恢复顺序、文件职责和验证证据已固化到 `docs/M9_1_DESKTOP_PLUGIN_SDK_IMPLEMENTATION.md`。
- 创建独立重建 worktree/分支；只迁入由 RED→GREEN 测试证明的 Live Provider、Web/XHS/Douyin 和自然语言任务增量。
- M0–M8 的 13 份历史文档与 46 个阶段验证脚本使用 `git mv` 移出插件分发目录，保留在 `docs/history/product-creative-legacy/`。
- 周十五产品已在全新隔离 workspace 以证据优先模式初始化；高风险健康表述只在 Evidence/Draft 和待确认 proposal，不在 Canonical Product Brain。
- 重建分支最终门禁：M10 35、Live 10、Desktop API/distribution 15、Desktop 定向 UI 17、bundle 2、M9 25/25、public surface 84/84、Brain/contract 零失败、typecheck/build 和离线安装全部通过。
- Live 实现提交：`855da56`；重建知识、M0–M8 历史和 M11 计划保存在本文件所在的后续本地提交。
- M11 新增 8 类带哈希的专业创作工件：Brief、Grounding、Research、3 Candidates、Decision、Story、Production Bible、Preflight QA。
- Goal Planner 在视频生成前声明并验证完整工件 Gate；生成式视频 Prompt 由 Production Bible 编译，不再直接使用用户原始消息作为最终 Prompt。
- Story/Production Bible 已接入 exact-main compositor；正式 M11 任务路径不再依赖硬编码通用剧情 fallback。
- Desktop Overview/Tasks/Review/Assets 已能展示 Grounding、工件进度、三个候选、Decision、Story、Production Bible 和 QA。
- 包装保真自然语言已覆盖“包装外观和文字不得变化”“产品包装文字必须保持不变”“主图原样保留，不允许改动”等表达；QA 会独立检查原始消息和生产路线。
- 任务修订中的制作时间约束可进入 Production Bible；“产品在第 4 秒左右出现”会把第一处产品 plate 调整为累计 4.0 秒，并写入结构化规格。
- M11 最终回归：M11 31、M10 35、Live adapter 10、distribution 3、Desktop backend/page 12；M9 recovery 25/25、contract invariants 51 actions/84 tools/84 CLI、public surface 84/84 均通过。
- Desktop Registry/UI、TypeScript typecheck、production build 和插件 bundle 构建通过；M12 bundle SHA-256 为 `7770a636e5357306a15f5f5fe9a8ff04c22a1a8c82d1e120cfdcef418ab5ed3f`。
- M12 新增八个版本化业务 Skill 和严格 Catalog；Skill 定义包含触发、输入/输出 Schema、允许工具、失败条件、Rubric 和正反例。
- 生产 Skill Runtime 复用 Hermes `PluginLlm.complete_structured`；不可用时 fail closed，不回退为固定剧情。
- Skill execution artifact 保存输入/输出哈希、版本、允许工具、实际动作、执行模式和失败诊断。
- Web、XHS、Douyin 和历史素材分别产生事件/时效、消费者语言/场景、前五秒/口播/节奏和历史模式洞察，仍保持 `not_product_fact`。
- 固定候选、静态评分和固定剧情 profile 已由 creative-strategy、creative-review、script-writer 和 storyboard-director 受控输出替换。
- 三候选继续保持 stable/variation/exploration，并保存历史结构相似度、相似工件和 novelty strategy。
- compliance-guard 已进入 Preflight QA；确定性包装/禁用表述硬失败始终覆盖语义 PASS。
- learning-analyst 已接入现有结果评估和 proposal/confirmation 边界，不直接写 Product Brain。
- Desktop Tasks/Review 已展示 Skill execution、版本、模式、状态、provenance、历史相似度和新颖性策略。
- M12 实施与恢复顺序已固化到 `docs/M12_PROFESSIONAL_BUSINESS_SKILLS_IMPLEMENTATION.md`。
- M12 最终回归：M12 26、M11/M12 工件链 34、M10 35、Desktop backend/distribution/live 25、Desktop UI 14、bundle 2，全部通过。
- M9 recovery 25/25、contract invariants 51 actions/84 tools/84 CLI、public surface 84/84、typecheck 和 production build 均通过。
- 10 个必读/恢复文件均存在；本次修改/新增 53 个文件敏感字面量扫描 0 finding；`git diff --check` exit 0。
- M13 新增五类媒体工件：Dependency Report、Product Plate、Media Execution Plan、
  Media Shot Result 和 Composite Manifest。
- Production Bible 可编译为逐镜头 Shot Graph；Provider 只生成背景、场景、人物和
  装饰，产品 plate 与字幕不进入生成模型。
- Product Plate 支持 source alpha、边缘连通背景和 full-rect 安全降级；源产品 RGB
  不被生成式重绘。
- 本地 compositor 使用 H.264/yuv420p、静音 AAC、ASS/libass 字幕和 faststart，
  单镜头独立保存并支持局部重试和重启恢复。
- preview-first 公开对话会在用户选择方向后等待明确生产确认；授权前只准备依赖、
  plate 和 plan，Provider 调用为零。
- 自然语言本地视频 E2E 已生成真实多镜头 MP4；ffprobe 验证 270×480、H.264、AAC、
  时长不少于 9.5 秒，Canonical Product Brain 指纹不变。
- M10–M13 Python 回归 `119 passed`；Desktop 插件 UI `17 passed`、bundle `2 passed`、
  typecheck/build、M9 recovery 25/25、public surface 84/84 均通过。
- 分发导出已修复为包含未提交但未忽略的第一方源码；临时包通过版本/哈希/敏感扫描、
  Desktop registry 和 enabled user-plugin 离线安装。
- M13 实施、恢复顺序、依赖边界和验证证据已固化到
  `docs/M13_RELIABLE_MEDIA_PRODUCTION_IMPLEMENTATION.md`。
- M14 新增不可变 Media QA Report、Repair Decision 和 Human Override 契约；PASS、
  REPAIR、HUMAN_REVIEW、REJECT 由确定性优先级决定。
- 技术 QA 已覆盖编码、画布、帧率、时长、faststart、镜头顺序、黑帧、冻结、静音和削波；
  字幕/OCR、Product Plate 包装保真和剧情连续性通过可替换 adapter fail closed。
- 自动返修只处理失败镜头，保留成功镜头，修复后重新合成并执行完整 QA；最多自动两轮。
- Creative Task 支持自然语言“继续修复这个视频”，并从最后 receipt/event 和 Repair
  Decision 恢复，禁止重复调用已成功镜头。
- 人工 approve、accept_with_warning、reject 需要 reason、actor 和 confirmation ID；
  原 QA Report 不可变，决定形成 receipt/audit 和 learning evidence，但不自动写 Brain。
- Desktop 五视图已展示 QA、失败证据、返修轮次、人工决定和学习证据。
- M14 最终本地 Gate：M14 `25 passed`、M10–M14 `145 passed`、M11/M13 `59 passed`、
  Desktop API/distribution `16 passed`、UI `16 passed`、bundle `2 passed`，
  typecheck/build、M9 recovery 25/25、public surface 84/84、离线分发安装和敏感扫描通过。
- M14 实施、恢复顺序和完整修改清单已固化到
  `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`。
- 依赖与恢复修复后的补充回归：M13 `39 passed`、M14 `30 passed`、M10–M14 与来源
  适配器组合 `191 passed in 210.85s`；Desktop 定向 5 文件 `17 passed`、bundle
  `2 passed`、typecheck/build、M9 recovery 25/25、public surface 84/84 通过。
- M13/M14 联合真实任务、授权、模型、来源、Product Brain hash 和恢复步骤已固化到
  `docs/M14_LIVE_GATE_20260717.md`。
- M13.1 将 exact-main 视频从静态图片循环改为“Seedance 无产品动态背景 + 本地不可变
  Product Plate + 确定性字幕”；2 秒故事镜头适配为 4 秒 Provider 请求后本地裁剪。
- 动态镜头携带 motion/action 契约；高冻结比例为 `FAIL/high`，VLM 逐镜输出
  `observed_action/action_completed`。完整冻结到 EOF 的 FFmpeg 日志漏报已修复。
- XHS/Douyin 已固定为可选研究来源；“今天能发的抖音视频”只请求 Web，不自动申请
  平台 Cookie；明确“搜索抖音爆款”时才加入 Douyin。
- M13.1 Gate：M10 `40 passed`、M13 `41 passed`、M14 `35 passed`、M11/M12/来源/
  分发 `85 passed`、Desktop API `12 passed`、UI `16 passed`、bundle `2 passed`；
  typecheck/build、M9 25/25、public surface 84/84、离线安装和分发扫描通过。
- M13.1 实施、恢复顺序、文件职责和验证证据见
  `docs/M13_1_DYNAMIC_SHOT_PRODUCTION_IMPLEMENTATION.md`。

## PARTIAL

- M9.1 已随当前 pilot 分支 push；云端独立分发仓库未修改，未 release。
- M10 自然语言 Creative Task：已实现产品认知分层、任务 Readiness、主动追问、有界编排、任务授权、素材/灵感、Mock 文图视频、反馈学习、Desktop 可见性和 Fake live provider 恢复；实现提交为 `33d096f`。
- M10 Live：已通过本机已安装 Hermes 和真实 Product workspace 执行 VLM、Web、Douyin、豆包图片生成和 Seedance 视频生成；真实结果、异步轮询、下载、导入、review/recovery 均有 durable 证据。普通 Seedance 产品视频会重绘包装，只可作为 Provider 链路审计样本。
- M10.1 包装保真：Goal Planner 已能把“不得重绘/原始像素/逐帧保持”等目标路由到现有 exact-main compositor；统一 Creative Task 已生成 10 秒 1080×1920 安全样片并进入 `AWAITING_FEEDBACK`。视觉仍是开发基线，composer 依赖本机外部 ffmpeg。
- M10.1 数据源：Web 真抓取、Douyin 真搜索/转录/DeepSeek 钩子/豆包前 5 秒分析已执行；XHS 已由安装版 Hermes 自然语言调用，产生 `source-snapshot-20260716-100618` 与 3 个候选，3 条均为 `not_product_fact`，Canonical Product Brain 未变化。
- M10 产品质量：用户已审阅两条样片并拒绝将其视为合格创作。exact-main 只有固定主图、通用字幕和装饰；Seedance 包装小字发生生成式乱码。两条结果不得记为成功模式。
- M11 工件链已阻止空 `selected_idea`、空剧情和缺失 Production Bible 进入视频 Provider；
  M14 已接管生成后 QA、返修和人工质量决策。
- 周十五真实主图已通过公开 `product_workflow_run` 形成 `r1` 审阅包：自然语言 preview-first 后选择 B，产品在 4.0 秒首次出现，只使用“外观可爱/方便随身携带”，路线为 `exact-main-composite`，Preflight QA 为 PASS；尚未获得用户创意方向验收，未生成最终视频。
- 2026-07-16 用户明确回复“全部接受，允许进入下一步”；M11 最后一项人工创意门禁通过。该接受不授权真实 Provider、Product Brain 写回、Git 提交或发布。
- M12 目前只完成离线、受控的专业创意链；没有执行本阶段范围外的真实联网、Cookie 或付费 Provider。
- M13 本地 fixture 真实媒体链已完成；新真实豆包逐镜头和 Seedance/DeepSeek 调用被
  Codex 租户策略阻塞，未发送数据。此前 `task-32f2…` 的真实五图与 exact-main 成片已由
  M14 正确判为 `REPAIR`，保留 shot-01、计划只重做 shot-02–05。
- M13 当前媒体工具来自本机 AIMIXMaster 内置 ffmpeg/ffprobe，只是验证依赖，不是
  Desktop 产品级分发方案。
- M14 本地离线 Gate 已完成；真实豆包 VLM/OCR、Seedance 逐镜头异步恢复和视觉阈值
  校准仍待单独 Live Gate。用户尚未亲自验收一条 QA PASS 和一条自动返修案例。
- M15 已完成无产品 onboarding、Evidence/Draft 安全摄入、自然语言任务入口、无 task ID
  恢复、三运营审阅节点、Settings 安全诊断、workspace/zh-CN/cleanup 隔离、插件分发和 NSIS
  Desktop 壳构建。本地“打包壳 + 当前 worktree runtime + 隔离 user plugin”后端试运行通过；
  包含 M15 的 origin pilot ref 已可获取；薄安装器已重建，install stamp 干净地固定到远端可获取提交
  `5e87c865c7fe105374300042c73d1cb1dd4ad746`。隔离 fresh-install 已启动，但首次引导因本机
  DNS 无法解析 `raw.githubusercontent.com` 而停止，尚未完成 runtime 下载和插件发现验证。
- M15 定向证据：backend `6 passed`；Product Creative bundle `11 passed`；Desktop
  routes/registry/page/Product Creative `22 passed`；bundle security `2 passed`；分发 bundle
  `1 passed`；M10–M15/来源/分发组合 `207 passed`；typecheck/build、分发扫描、离线安装
  和 NSIS 壳构建均通过；packaged payload 的 install-stamp、renderer 与三个 node-pty 二进制
  已通过只读 smoke validation；该旧 stamp 同时证明旧 EXE 不包含当前 M15 runtime。实施真源为
  `docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md`。

## PLANNED

- M15 fresh-install 网络复验、人工运营试用和 M16 母创意受控规模化。完整路线见 `docs/PRODUCT_AGENT_DIRECTION.md`。
- M15 人工 Gate 通过前不进入 M16；M14 真实动态样片 Gate 继续独立完成，不扩展新 Provider 或批量生产。

## BLOCKED

- M10 不能按旧口径标记 DONE：真实生成已完成，但旧样片创意质量和包装质量没有通过用户验收。
- M11/M12 已进入 origin pilot ref；尚未合并 main、tag 或 release。
- M13 已进入 origin pilot ref，状态为 `DONE_IN_PILOT_REF_UNPUBLISHED_LIVE_GATE_PENDING`。
- M14 已标记
  `DONE_IN_PILOT_REF_UNPUBLISHED_LIVE_GATE_AND_USER_ACCEPTANCE_PENDING`。
- M15 功能、插件分发和本地打包组合试运行已进入 pilot ref；新 stamp 安装器构建完成，但隔离
  fresh-install 被 `raw.githubusercontent.com` DNS 解析失败阻塞，内部运营人工全链也尚未完成。
- 正式可发布产品视频仍被 M13/M14 联合真实 Provider/VLM Live Gate 和用户质量验收阻塞。

## DEPRECATED

- Product Creative 专属 Desktop core route/component 是 HEAD 可用实现，但工作区目标已改为通用插件页面。
- 将脚本作为用户主入口；M2 继续追加小功能；M6 remote-url-first 旧理解。

## UNKNOWN

- MVP 发布口径、生产 SLA、多用户/平台发布路线。

## 技术债与风险

- enabled Desktop plugin 与宿主同源且被视为受信任；renderer workspace header 不是恶意插件隔离边界。
- media descriptor 使用本地绝对路径，remote Desktop 预览未验收。
- 宿主全量 UI 套件存在多项与 M9.1 无关的既有失败；M9.1 定向门禁已通过。
- 原 `product-creative-runtime` 工作区的 `pytest-of-unknown/` 属于历史测试副产物并随现场保留；新重建分支不包含该目录。
- `verify_m2_workflow_run.ps1` 在 Windows 嵌套 PowerShell 下长时间无输出，未完成，不能列为通过或失败。
- M13 已提供插件级 ffmpeg/ffprobe 发现和诊断，但当前借用本机 AIMIXMaster 内置
  二进制；换机和 Desktop 安装包可复现性仍不足。
- 豆包图片输出带“AI生成”水印；真实 Seedance 包装会发生模型重绘，二者只能按各自边界使用。
- exact-main 的硬编码通用字幕和 `anime_story` 名称容易让技术样片被误解为剧情视频，必须在 M11 前停用为正式交付。
- Product Brain 当前 `learning` 数组混合产品偏好、渠道模式和制作经验，后续需要分层迁移，但不得在 M10.2 直接改数据库结构。
- M12 的真实创意质量仍取决于所配置 LLM；离线 fixture 证明契约、编排和 Gate，不证明最终媒体可发布。
- executor 调用失败会写失败 Skill execution；部分 executor 返回后的业务 Schema 校验失败只阻断正式工件，尚未全部形成独立失败 execution artifact。
- 分发脚本已支持导出未提交但未忽略的第一方源码，临时独立安装已通过；但 dirty build
  stamp 与未提交来源仍禁止正式 release。
- Windows 深层测试临时路径可能触发 legacy `MAX_PATH`；本轮真实媒体 E2E 使用短
  `C:\tmp\...` 目录。
- M13 真实异步 Provider shot 的恢复尚未闭环，fixture 不得冒充 Live 验收。
- M14 没有配置真实 OCR/VLM adapter 时会进入 HUMAN_REVIEW；离线 fixture 证明契约、
  编排和返修边界，不证明真实视觉模型质量。
- Windows PowerShell 将中文 here-string 经标准输入传给 Python 时可能按旧代码页替换为 `?`；执行脚本必须显式设置 `$OutputEncoding` 和 `[Console]::OutputEncoding` 为 UTF-8，失败修订保留为证据。

## 2026-07-16 产品方向重定标

- 新权威方向：`docs/PRODUCT_AGENT_DIRECTION.md`。
- 产品定义：围绕具体产品长期工作的专业 AI 创意生产系统，而不是单纯 Product Brain 或一次性视频生成器。
- 四个支柱：Product Grounding、Creative Director、Production Engine、Evaluator & Learning。
- 架构方式：专业 Workflow + Skills + Capabilities + Gates；只在必要时使用有边界 Worker，不建设自由多 Agent 群。
- 早期核心指标：可发布内容数量 ÷ 运营人员投入时间。
- 学习基线：通过/修改/拒绝及原因优先；发布表现手动选填；不做自动投放效果分析。

## 2026-07-15 M10 工作区验证

- M10 Python：24 passed（真实 Hermes agent loop + fixture/mock/Fake Gateway；无网络/费用）。
- Desktop SDK Node bundle：2 passed。
- Desktop routes/registry/page/Product Creative UI：17 passed（5 files）；Desktop bundle 2 passed。
- Desktop backend API/distribution：15 passed（使用仓库现有 `.venv`；系统 Python 因缺 `python-multipart` 未进入收集）。
- Distribution bundle registry：1 passed；离线 user-plugin install passed；版本/哈希/敏感数据 validation passed。
- TypeScript typecheck passed；Desktop production build passed（dirty stamp、既有 CSS 和大 chunk warning）。
- M9 review/recovery：25/25；Product Brain boundary：0 failures；contract invariants：51 actions / 84 tools / 84 CLI；public-surface golden hash 匹配。
- `git diff --check`：通过，仅 CRLF 转换 warning。
- 真实执行：VLM 1 条完整结构化结果；Web snapshot；Douyin 3 个真实候选、SiliconFlow 转录、DeepSeek 钩子和豆包前 5 秒分析；豆包图片 1 次；Seedance 视频任务 2 次（其中一条为安全模板审计样本，另一条旧样本禁止交付）。
- 真实产物：`image-result-20260715-173453`、`video-result-20260715-174019`；exact-main 统一任务结果 `video-result-20260715-175851`。具体路径、哈希、任务 ID 和判定见 `docs/M10_LIVE_PROVIDER_AND_SOURCE_INTEGRATION.md`。
- 当前定向回归：M10 35 passed；Live adapter 10 passed；Douyin 多模态 12 passed（1 个弃用 warning）；M9 review/recovery 25/25；public surface 84/84；Desktop UI 17 passed；bundle 2 passed；typecheck/build passed。
- XHS sidecar：18 files / 106 tests passed；client/server TypeScript typecheck passed。首次 Vitest 仅因沙箱无权写 `.vite-temp` 未启动，获准后原样重跑通过。
- `git diff --check` exit 0（只有 LF→CRLF 提示）；可发布源码/文档敏感扫描 0 hits；9 个必读文档引用全部存在。
- XHS 旧账号的 `-104` 已通过专用 Edge 重新登录解决；安装版 Hermes 自然语言 E2E 保存 3 条 snapshot 与 3 个候选，两个后台 job 在取得证据后停止剩余队列。

## 下一步推荐

方案 A 已执行：包含 M15 runtime 的 origin pilot ref 已可获取，Desktop/NSIS 已重建，install stamp
固定到提交 `5e87c865c7fe105374300042c73d1cb1dd4ad746`，安装器 SHA-256 为
`AC759A1EEFC3F555E58F75209D4DF1169270688525231592F307A093F8998F56`。下一步在
`raw.githubusercontent.com` DNS 恢复后，从全新隔离 `HERMES_HOME`/workspace/user-data 原样重跑
fresh-install；不得切换镜像或跳过固定提交校验。随后由一名内部运营人员按
`docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md` 的脚本完成 onboarding、自然语言任务、
三节点审阅、中断恢复和反馈学习，并由产品/内容负责人记录接受或修改结论。

M14 真实动态样片仍是独立质量 Gate：用户可在 Codex 外部按 product-free Prompt 生成
Seedance 结果并放入本地验收目录，再按 `docs/M14_LIVE_GATE_20260717.md` 完成本地裁剪、
Product Plate 合成、QA/返修与验收；不得由 Codex 绕过租户策略发起外呼。

M11 实施与恢复细节见 `docs/M11_PROFESSIONAL_CREATIVE_WORKFLOW_IMPLEMENTATION.md`。
M12 实施与恢复细节见 `docs/M12_PROFESSIONAL_BUSINESS_SKILLS_IMPLEMENTATION.md`。
M13 实施与恢复细节见 `docs/M13_RELIABLE_MEDIA_PRODUCTION_IMPLEMENTATION.md`。
M13.1 动态镜头与动作门禁见 `docs/M13_1_DYNAMIC_SHOT_PRODUCTION_IMPLEMENTATION.md`。
M14 实施与恢复细节见 `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`。
M14 真实执行与中断恢复见 `docs/M14_LIVE_GATE_20260717.md`。
M15 Desktop 内部试用实施与人工验收见 `docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md`。

待确认问题见 `docs/OPEN_QUESTIONS.md`。
