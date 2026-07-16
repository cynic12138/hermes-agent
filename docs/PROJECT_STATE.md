# Project State

- 日期：2026-07-16
- 分支：`product-creative-rebaseline-20260716`
- 重建基础 HEAD：`d7d6ec0bf5a4ae9a1bc2377db668ed07a8a87c0b`；进入项目时运行 `git rev-parse HEAD` 获取最新提交
- M9.1 实现提交：`83b4e8f`
- M10 实现提交：`33d096f`
- 已提交阶段：M9.1 Desktop Plugin SDK 迁移（DONE、本地已提交）
- 当前阶段：M10.2 重建基线 `DONE_LOCAL`；创作质量仍未通过，下一开发阶段为 M11
- 发布阶段：未 push、未 tag、未 release
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

## PARTIAL

- M9.1 尚未 push/release；云端分发仓库未修改。
- M10 自然语言 Creative Task：已实现产品认知分层、任务 Readiness、主动追问、有界编排、任务授权、素材/灵感、Mock 文图视频、反馈学习、Desktop 可见性和 Fake live provider 恢复；实现提交为 `33d096f`。
- M10 Live：已通过本机已安装 Hermes 和真实 Product workspace 执行 VLM、Web、Douyin、豆包图片生成和 Seedance 视频生成；真实结果、异步轮询、下载、导入、review/recovery 均有 durable 证据。普通 Seedance 产品视频会重绘包装，只可作为 Provider 链路审计样本。
- M10.1 包装保真：Goal Planner 已能把“不得重绘/原始像素/逐帧保持”等目标路由到现有 exact-main compositor；统一 Creative Task 已生成 10 秒 1080×1920 安全样片并进入 `AWAITING_FEEDBACK`。视觉仍是开发基线，composer 依赖本机外部 ffmpeg。
- M10.1 数据源：Web 真抓取、Douyin 真搜索/转录/DeepSeek 钩子/豆包前 5 秒分析已执行；XHS 已由安装版 Hermes 自然语言调用，产生 `source-snapshot-20260716-100618` 与 3 个候选，3 条均为 `not_product_fact`，Canonical Product Brain 未变化。
- M10 产品质量：用户已审阅两条样片并拒绝将其视为合格创作。exact-main 只有固定主图、通用字幕和装饰；Seedance 包装小字发生生成式乱码。两条结果不得记为成功模式。
- 当前创意编排：`selected_idea` 和实际 `inspiration_context` 可能为空，仍可进入通用 video brief 或 exact-main；Review 尚未成为自动媒体 QA/返修 Gate。

## PLANNED

- M11：按 `docs/plans/2026-07-16-m11-professional-creative-workflow-plan.md` 实现 Creative Task Brief、Grounding Pack、Research Insight Pack、Creative Candidates、Creative Decision、Story Package、Production Bible 和 Preflight QA。
- M12–M16：专业 Skills、混合媒体生产、自动 QA/返修、Desktop 内部试用和母创意受控规模化。完整路线见 `docs/PRODUCT_AGENT_DIRECTION.md`。

## BLOCKED

- M10 不能按旧口径标记 DONE：真实生成已完成，但创意质量和包装质量没有通过用户验收。
- 正式视频交付被专业创意产物、混合包装保真路线和自动 QA 缺失阻塞。

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
- exact-main compositor 当前借用本机已有 ffmpeg，尚未提供插件级发现/安装机制；换机可复现性不足。
- 豆包图片输出带“AI生成”水印；真实 Seedance 包装会发生模型重绘，二者只能按各自边界使用。
- exact-main 的硬编码通用字幕和 `anime_story` 名称容易让技术样片被误解为剧情视频，必须在 M11 前停用为正式交付。
- Product Brain 当前 `learning` 数组混合产品偏好、渠道模式和制作经验，后续需要分层迁移，但不得在 M10.2 直接改数据库结构。

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

下一唯一推荐开发任务是 M11“专业创意工作流与质量门禁”：按版本化产物和 Gate 驱动 Planner，先完成周十五产品剧情短视频纵向闭环，阻止空创意、空剧情和通用模板进入真实生成。

待确认问题见 `docs/OPEN_QUESTIONS.md`。
