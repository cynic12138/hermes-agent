# AI Handoff

- 最后更新：2026-07-16
- 分支：`product-creative-rebaseline-20260716`
- 重建基础 HEAD：`d7d6ec0bf5a4ae9a1bc2377db668ed07a8a87c0b`；进入项目时必须重新运行 `git rev-parse HEAD`
- M9.1 实现基线：`83b4e8f`
- 当前阶段：M10.2 重建基线已在本地完成；M10.1 技术链路完成但创作质量验收未通过；下一唯一开发任务为 M11

## 新会话先读

1. `AGENTS.md`
2. `docs/PRODUCT_AGENT_DIRECTION.md`
3. `docs/AI_HANDOFF.md`
4. `docs/PROJECT_STATE.md`
5. `docs/MVP_SCOPE.md`
6. `docs/ARCHITECTURE_CURRENT.md`
7. `docs/REBASELINE_AND_CLEANUP_20260716.md`
8. `docs/plans/2026-07-16-m11-professional-creative-workflow-plan.md`

M10 必读 `docs/M10_PRODUCT_COGNITION_AUTONOMOUS_CREATION_IMPLEMENTATION.md`、`docs/M10_LIVE_PROVIDER_AND_SOURCE_INTEGRATION.md` 和 `docs/plans/2026-07-14-m10-zero-to-product-brain-plan.md`。M9.1 SDK/插件 UI/分发再读 `docs/M9_1_DESKTOP_PLUGIN_SDK_IMPLEMENTATION.md`。

审计证据：`docs/recovery/20260712-154151/`、`docs/REBASELINE_AND_CLEANUP_20260716.md`。M0–M8 历史索引：`docs/history/product-creative-legacy/README.md`。

## 当前目标与阶段

目标已经重新定义为专业 AI 创意生产系统：Product Brain 负责产品真实性和长期认知，专业 Workflow/Skills 负责研究、创意、剧情、分镜、生产、QA 和学习。M10.1 已取得真实 Provider/Web/XHS/Douyin 结果，但用户确认现有样片创意空洞或包装乱码，因此当前不是等待形式验收，而是进入质量架构重建。

## 最近完成

- `1d223d3` durable runtime 基线。
- `f8bdb0c` M9 review/recovery console。
- `822d879` Windows plugin clone 删除修复。
- `83b4e8f` M9.1：`9.1.0-alpha.1`、通用 SDK、五视图、确认门禁、Node 22 build、离线安装 E2E、分发扫描。
- 发布 workflow 的 Vitest 调用已固定在 `apps/desktop` 工作目录；M9.1 实施和恢复细节已写入专题文档。
- M10 新增四个任务/认知契约、Readiness/追问、Goal Planner、任务授权、研究降级、Mock 文图视频、Live provider 提交/恢复、反馈学习与 Desktop task 可见性。
- M10 保持 84 tools / 84 CLI，不增加 Product Creative core tool；真实 Provider 默认关闭。
- M10.1 已从本机安装版 Hermes 完成真实 VLM、Web、Douyin、豆包图片和 Seedance 视频；普通 Seedance 视频不能证明包装逐像素保真，exact-main 统一任务已生成包装不重绘的开发样片。
- Provider 签名下载 URL 会在持久化前移除 query/fragment；失败在 review/delivery 的已付费任务可离线恢复，禁止重复提交。
- 2026-07-16 用户产品讨论确认：不建设无边界多 Agent 群；采用专业 Workflow + Skills/Capabilities/Gates；第一阶段学习依赖通过/修改/拒绝及原因；核心指标是可发布内容/运营投入。
- 新方向与 Final 1.0 路线已写入 `docs/PRODUCT_AGENT_DIRECTION.md`。
- 新建干净 worktree/分支，原脏工作区与运行数据已通过 patch、Git bundle、zip 和 SHA-256 完整保护。
- Live 增量经过选择性迁移：M10 先出现 13 个预期失败、Live source 10 个预期失败，迁入最小实现后分别 35/35 和 10/10 通过。
- 周十五严格 workspace 只确认产品名称和素材登记；高风险健康表述未进入 Canonical Product Brain。详见 `docs/product-bases/zhou-shiwu-honeydew/STRICT_BASELINE.md`。
- Live 选择性迁移已提交为 `855da56`；重建知识、M0–M8 历史和 M11 计划保存在本文件所在的后续本地提交。尚未 push/tag/release。

## 当前待办/下一入口

下一开发入口是 M11：按 `docs/plans/2026-07-16-m11-professional-creative-workflow-plan.md` 定义并接通 Brief、Grounding、Research Insight、Candidates、Decision、Story、Production Bible 和 Preflight QA，使 Goal Planner 由这些产物和 Gate 驱动。

## 阻塞

- M9.1 已本地提交；尚未 push，自动发布仍未实际触发。
- 全量宿主 UI 套件有多项与 M9.1 无关的既有失败；定向 M9.1 测试与 Node 22 build 已通过。
- XHS 旧账号 `-104` 已解决；当前限制是自然语言 E2E 中 `ctx.llm` 不可用，导致深度 LLM 摘要包未生成，但 snapshot 与规则候选均已保存。
- exact-main composer 本次借用本机已有 ffmpeg；插件尚无独立发现/安装机制。
- 豆包图片带“AI生成”水印；Seedance 会生成式重绘包装，只可作为链路审计，不能宣传为包装保真。
- M10 的旧 DONE 口径已被真实样片推翻：Provider 链路虽成功，但创意和包装质量未通过。不得再把“获得可播放文件”写成 M10 完成。
- `verify_m2_workflow_run.ps1` 本轮未完成；不得写成通过。

## 关键决策

- Product Creative 留在插件；Hermes core 只提供通用扩展面。
- 内层 `.hermes/plugins/product_creative` 是唯一源码真源；独立仓库仅由发布流程生成。
- 用户已选择方案 1：产品稳定前保持上述同仓源码真源；连续里程碑和独立安装边界稳定后再拆分。
- enabled bundled/user Desktop plugin 是 v1 的受信任同源代码；project plugin 不可注入可执行页面/backend API。
- Product Brain 支持从空白开始；Hermes 应通过自然语言主动追问和索要证据逐步建脑，而不是用网页检索结果预填正式认知。
- Product Brain 不是完整创作大脑；Creative Director、Production Engine、Evaluator & Learning 是同等重要的系统支柱。
- 专业角色优先实现为 Skill/Capability/Gate；只有复杂研究需要时才允许有边界只读 Worker。
- 空 `selected_idea`、无有效剧情/分镜或缺少 Production Bible 时不得调用真实生成。
- 自动质检未通过的结果不得标记为可发布；固定主图加通用字幕不得称为剧情视频。
- Evidence Inbox、Draft Understanding、Canonical Product Brain 必须分层；高影响字段逐项确认后写回。
- SQLite 为 durable runtime 真源，大文件在 workspace。
- 生成通过 Hermes chat 启动；M9/M9.1 Desktop 当前只审阅/恢复。
- M10 `product_workflow_run` 通过 `task_id` 继续 Creative Task；外部研究授权与 Brain 写回确认完全分离。
- Live Provider 需要 task authorization 和 `PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1` 双重开关；视频状态恢复不重复消耗生成次数。
- 真实副作用和 Product Brain 写回必须确认。

产品基座与从 0 建脑流程：`docs/product-bases/zhou-shiwu-honeydew/README.md`、`ZERO_TO_PRODUCT_BRAIN.md`。

## 命令

```powershell
node --test apps/desktop/electron/desktop-plugin-bundle.test.cjs
powershell -ExecutionPolicy Bypass -File .hermes/plugins/product_creative/scripts/verify_m9_review_recovery.ps1
powershell -ExecutionPolicy Bypass -File .hermes/plugins/product_creative/scripts/verify_public_surface_golden.ps1
npm.cmd --prefix apps/desktop run typecheck
npm.cmd --prefix apps/desktop run build
python .hermes/plugins/product_creative/scripts/validate_distribution.py <distribution>
python .hermes/plugins/product_creative/scripts/verify_distribution_install.py <distribution>
python -m pytest tests/hermes_cli/test_product_creative_m10.py -q -p no:cacheprovider --basetemp <C:\tmp\unique-m10-dir>
```

逐命令确认不会触发真实 workspace、外部 API、消息或费用。不要直接运行会修改 config 的开发启动脚本或 provider live 测试。

## 禁止事项

不清理原脏工作区、不覆盖用户改动、不升级依赖、不 push/release；未来业务/契约修改必须以 `docs/PRODUCT_AGENT_DIRECTION.md` 和当前里程碑为准，并经正常计划与用户授权。
