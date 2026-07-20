# AI Handoff

- 最后更新：2026-07-20
- 分支：`product-creative-rebaseline-20260716`
- M11–M15 实现与测试提交：`25e26df`；打包深链修复/验收代码基线：`a0081dd`；进入项目时必须重新运行 `git rev-parse HEAD`
- M9.1 实现基线：`83b4e8f`
- 当前阶段：M14 自动媒体 QA、返修与学习质量已达到
  `DONE_IN_PILOT_REF_UNPUBLISHED_LIVE_GATE_AND_USER_ACCEPTANCE_PENDING`
- M15 Desktop 状态：
  `PACKAGED_FRESH_INSTALL_AND_PLUGIN_UI_ACCEPTED_UNPUBLISHED_OPERATOR_FULL_FLOW_PENDING`
- 当前 Live Gate：`LOCAL_GATE_PASSED / EXPLICIT_EXTERNAL_DISCLOSURE_APPROVED / TENANT_POLICY_BLOCKED`；
  当前任务、策略阻塞、已有真实 `REPAIR` 案例和恢复步骤见 `docs/M14_LIVE_GATE_20260717.md`

## 新会话先读

1. `AGENTS.md`
2. `docs/PRODUCT_AGENT_DIRECTION.md`
3. `docs/AI_HANDOFF.md`
4. `docs/PROJECT_STATE.md`
5. `docs/MVP_SCOPE.md`
6. `docs/ARCHITECTURE_CURRENT.md`
7. `docs/REBASELINE_AND_CLEANUP_20260716.md`
8. `docs/plans/2026-07-16-m11-professional-creative-workflow-plan.md`
9. `docs/M11_PROFESSIONAL_CREATIVE_WORKFLOW_IMPLEMENTATION.md`
10. `docs/reviews/M11_ZHOU_SHIWU_CREATIVE_PACK_REVIEW.md`
11. `docs/M12_PROFESSIONAL_BUSINESS_SKILLS_IMPLEMENTATION.md`
12. `docs/plans/2026-07-16-m12-professional-business-skills-design.md`
13. `docs/M13_RELIABLE_MEDIA_PRODUCTION_IMPLEMENTATION.md`
14. `docs/plans/2026-07-16-m13-reliable-media-production-design.md`
15. `docs/plans/2026-07-16-m14-automatic-media-qa-repair-plan.md`
16. `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`
17. `docs/M14_LIVE_GATE_20260717.md`
18. `docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md`
19. `docs/M15_PACKAGED_SEED_PLUGIN_ACCEPTANCE_20260720.md`
20. `docs/M15_FRESH_INSTALL_USER_DATA_ISOLATION_20260720.md`

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
- Live 选择性迁移提交为 `855da56`；重建知识和 M11–M15 实现已随 pilot branch push。未合并 main、未 tag、未 release。
- M11 已实现 8 类专业工件、三个候选与决策、Story、Production Bible、Preflight QA、Provider Compiler、exact-main 工件接入和 Desktop 展示。
- M11 真实 Hermes 自然语言 E2E 会在生成前建立完整专业工件；无 QA、无 Story 或无 Production Bible 时 Provider dispatch 为零。
- 周十五审阅 fixture 使用真实主图和低风险确认字段，产生 `exact-main-composite` 五镜头方案；没有联网、没有 Provider 调用、没有 Product Brain 写回。
- 审阅时发现并修复包装保真自然语言漏判；现在解析和 QA 双层防护“包装外观和文字不得变化”等表达。
- 当前公开任务 `task-2e495b5048ed4f45a62be4e05f59b6ad` 的 `r1` 完整审阅包选中包内物件 Variation，产品在累计 4.0 秒首次出现；文案只表达“外观可爱/方便随身携带”，QA PASS，任务停在 `NEEDS_INPUT`。
- 用户已于 2026-07-16 回复“全部接受，允许进入下一步”；M11 人工门禁通过。
- 修订时间约束已结构化进入 Production Bible；PowerShell 通过 stdin 执行中文 Python 脚本时必须显式设置 UTF-8，`r3` 保留为编码失败证据。
- M12 已实现八个版本化业务 Skill：task-director、research-director、creative-strategy、creative-review、script-writer、storyboard-director、compliance-guard 和 learning-analyst。
- 生产 Skill Runtime 复用 Hermes `PluginLlm.complete_structured`；没有 executor 时 fail closed，不回退为固定剧情。离线 fixture 只用于测试。
- Skill execution artifact 保存版本、输入/输出哈希、允许工具、实际动作、模式和失败诊断；外部来源继续保持 `not_product_fact`。
- Creative Candidates 已由受控 Skill 输出替换固定三套 profile；保留 stable/variation/exploration，并增加历史结构相似度和 novelty strategy。
- creative-review 独立执行；script-writer、storyboard-director 和 compliance-guard 已进入 Story、Production Bible 和 Preflight QA 链。
- Desktop Tasks/Review 已显示 Skill execution、provenance、历史相似度和新颖性策略。
- M12 实施与恢复细节已写入 `docs/M12_PROFESSIONAL_BUSINESS_SKILLS_IMPLEMENTATION.md`。
- M12 最终回归：M12 26、M11/M12 工件链 34、M10 35、Desktop backend/distribution/live 25、Desktop UI 14、bundle 2，全部通过；M9 recovery 25/25、contract invariants 51/84/84、public surface 84/84、typecheck/build 均通过。
- M13 已实现 Dependency Report、Product Plate、Media Execution Plan、逐镜头 Provider
  边界、确定性 compositor、单镜头恢复和最终 Composite Manifest。
- 自然语言 E2E 已从 preview-first 选择方向、确认生产和任务授权生成真实本地多镜头
  MP4；ffprobe 验证 270×480、H.264、AAC 和约 10 秒时长，Canonical Product Brain
  指纹不变。
- M10–M13 回归 `119 passed`；Desktop 定向 UI `17 passed`、bundle `2 passed`、
  typecheck/build、M9 recovery 25/25、public surface 84/84 均通过。
- 临时分发已通过版本/哈希/敏感扫描、Desktop registry 和 enabled user-plugin 离线
  安装；导出脚本已修复为包含未提交但未忽略的第一方源码。
- 当前 bundle SHA-256：
  `9d65b3fe2a6ebfffaeb948a88a4b45914716e15e774d991fc8691d7e5ff4c014`。
  本机 build 使用 Node 24.15.0；Node 22 仍是 CI/发布权威。
- M14 已实现不可变 QA Report、Repair Decision、Human Override、技术/字幕/包装/剧情
  检查、只返修失败镜头、最多两轮自动修复、自然语言继续、人工确认门禁和 Learning
  evidence；Canonical Product Brain 不会因 QA 或未确认学习自动变化。
- M14 自然语言 E2E 已证明黑色 `shot-03` 只重做一次，其他四镜头不重复调用；修复后
  完整复检并进入 `AWAITING_FEEDBACK`。
- M14 最终本地 Gate：M14 `25 passed`、M10–M14 `145 passed`、M11/M13 `59 passed`、
  Desktop API/distribution `16 passed`、UI `16 passed`、bundle `2 passed`，
  typecheck/build、M9 recovery 25/25、public surface 84/84、离线安装和敏感扫描通过。
- 当前 M14 bundle SHA-256：
  `1ef2752e91fd5590fa43ae1d21796cc9c267f8104d9a9c057f16141bef71e94e`。
  实施与恢复细节见 `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`。
- 依赖和恢复修复后的补充回归：M13 `39 passed`、M14 `30 passed`、M10–M14 与来源
  适配器组合 `191 passed in 210.85s`；Desktop 定向 5 文件 `17 passed`。
- 用户已于 2026-07-17 明确允许将必要本地主图、参考图和提示词发送给豆包/DeepSeek，
  并限定调用和数据范围；Codex 租户策略仍拒绝外发。本次 Task Authorization 为 0、主计划
  shot result 为 0，不得写成调用已发生。
- 已有真实任务 `task-32f2c87065fc4aff9d44ffdf36203355` 的五图、exact-main 视频和
  真实 VLM QA 可安全复用；结果为 `REPAIR`，失败镜头 shot-02–05，shot-01 preserved。
- M15 已完成产品 onboarding、Evidence/Draft 安全摄入、自然语言任务入口、无 task ID
  恢复、产品事实/创意方向/成片质量三节点、Settings 无密钥诊断和 workspace/locale/cleanup
  隔离。分发扫描、enabled user-plugin 离线安装和 Windows NSIS Desktop 壳构建通过。
- M15 bundle SHA-256 为
  `8291e28588ca06d5a1613c05f30699032540ff42c33b5dfce2694ed60adf9937`；最终 fresh-install 安装器
  SHA-256 为 `90BCE51012171CDD151FFFB2E782F351E89B86035A76627B04FEF79870EF7175`。
- `C:\tmp\hermes-desktop-fresh-install-PFu67p` 已完成固定 `a0081dd` runtime、enabled seed user plugin、
  backend、认证 discovery/bundle/diagnostics、插件深链及 Overview/Tasks/Review/Assets/Learning 真实
  Electron 验收。real-provider 保持关闭，XHS/Douyin 可选离线，外部调用为 0。完整证据见
  `docs/M15_PACKAGED_SEED_PLUGIN_ACCEPTANCE_20260720.md`。
- fresh-install user-data 隔离已在当前 worktree 修复并实测：测试模式缺少、相对或越界路径即
  fail closed，Chromium 使用显式 `--user-data-dir`；临时沙箱有运行写入而受保护的 37 个正式
  Hermes 状态文件前后差异为 0，残留测试进程为 0。实现随本文所在本地提交保存、尚未推送，证据见
  `docs/M15_FRESH_INSTALL_USER_DATA_ISOLATION_20260720.md`。

## 当前待办/下一入口

M15 packaged fresh-install、插件 UI 和正式宿主数据隔离已通过。下一工程动作是由内部运营人员按
`docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md` 和
`docs/M15_PACKAGED_SEED_PLUGIN_ACCEPTANCE_20260720.md` 完成自然语言全链并记录接受/修改结论。
M15 人工门禁和 M14 独立真实样片门禁都完成前不进入 M16。

M14 真实动态样片仍是独立门禁：用户可在 Codex 外部生成 product-free Seedance 镜头，
Codex 只做本地导入、Product Plate 合成、QA/返修；不得绕过租户披露策略。M15 UI 验收
不能替代 M14 样片质量验收。

## 阻塞

- M9.1 及 M11–M15 实现均已随 pilot 分支推送；自动发布未触发，独立分发仓库未更新。
- 全量宿主 UI 套件有多项与 M9.1 无关的既有失败；定向 M9.1 测试与 Node 22 build 已通过。
- XHS 旧账号 `-104` 已解决；当前限制是自然语言 E2E 中 `ctx.llm` 不可用，导致深度 LLM 摘要包未生成，但 snapshot 与规则候选均已保存。
- M13 已提供 ffmpeg/ffprobe 路径发现和 readiness；M15 通用 Hermes Desktop NSIS、固定 fork
  runtime、seed plugin 和真实 UI 已通过。媒体工具可移植性和独立品牌安装包仍未验收。
- 历史验收窗口内正式 Hermes 状态文件时间戳变化的原因仍不可追溯且未回滚；新构建已通过
  fail-closed user-data 路径约束和 37 个受保护文件零差异验收，不再是当前阻塞。
- 豆包图片带“AI生成”水印；Seedance 会生成式重绘包装，只可作为链路审计，不能宣传为包装保真。
- M10 的旧 DONE 口径已被真实样片推翻：Provider 链路虽成功，但创意和包装质量未通过。不得再把“获得可播放文件”写成 M10 完成。
- `verify_m2_workflow_run.ps1` 本轮未完成；不得写成通过。
- M12 离线 fixture 证明契约、编排和 Gate，不证明配置的真实 LLM 一定产生可发布创意。
- M11–M15 实现已提交并推送到 pilot ref；尚未合并 main、tag 或 release。
- M14 默认没有真实 OCR/VLM adapter 时会 fail closed 到 `HUMAN_REVIEW`；真实模型
  稳定性和阈值尚需 Live Gate 校准。
- M13.1 fake async 动态 shot 恢复、冻结门禁和动作 QA 已通过；真实 Seedance shot 与
  真实 VLM 动作判断尚未完成联合 Live Gate。
- Windows 深层测试临时目录可能触发 legacy `MAX_PATH`；媒体 E2E 使用短
  `C:\tmp\...` 隔离目录。
- 新建项目对话框的长目录路径会导致横向溢出；当前不阻断链路，但属于运营 UX 缺陷。
- 本机最终回归为 Node 24.x；正式发布仍需 Node 22 CI 权威门禁。

## 关键决策

- Product Creative 留在插件；Hermes core 只提供通用扩展面。
- 内层 `.hermes/plugins/product_creative` 是唯一源码真源；独立仓库仅由发布流程生成。
- 用户已选择方案 1：产品稳定前保持上述同仓源码真源；连续里程碑和独立安装边界稳定后再拆分。
- enabled bundled/user Desktop plugin 是 v1 的受信任同源代码；project plugin 不可注入可执行页面/backend API。
- Product Brain 支持从空白开始；Hermes 应通过自然语言主动追问和索要证据逐步建脑，而不是用网页检索结果预填正式认知。
- Product Brain 不是完整创作大脑；Creative Director、Production Engine、Evaluator & Learning 是同等重要的系统支柱。
- 专业角色优先实现为 Skill/Capability/Gate；只有复杂研究需要时才允许有边界只读 Worker。
- Skill 只保存稳定方法，不保存具体产品事实；Skill 输出必须经过 Schema、hash、确定性 Gate 和 artifact 审计。
- LLM Skill 负责创意判断，Capability/Compiler 负责包装、时间、素材、字幕、授权和 Provider 硬约束；LLM PASS 不能覆盖硬失败。
- 空 `selected_idea`、无有效剧情/分镜或缺少 Production Bible 时不得调用真实生成。
- 自动质检未通过的结果不得标记为可发布；固定主图加通用字幕不得称为剧情视频。
- Evidence Inbox、Draft Understanding、Canonical Product Brain 必须分层；高影响字段逐项确认后写回。
- SQLite 为 durable runtime 真源，大文件在 workspace。
- 生成通过 Hermes chat 启动；M15 Desktop 增加 onboarding、任务引导、三节点审阅、
  恢复和诊断，但不建立平行 Agent loop。
- M10 `product_workflow_run` 通过 `task_id` 继续 Creative Task；外部研究授权与 Brain 写回确认完全分离。
- Live Provider 需要 task authorization 和 `PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1` 双重开关；视频状态恢复不重复消耗生成次数。
- 真实副作用和 Product Brain 写回必须确认。
- 方案 1 的拆仓门槛：至少两个连续产品里程碑保持公开契约稳定、导出安装无 in-tree 假设、兼容矩阵可独立维护后才重新评估拆分。

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
python -m pytest tests/hermes_cli/test_product_creative_m11_artifacts.py -q -p no:cacheprovider --basetemp <unique-dir>
python -m pytest tests/hermes_cli/test_product_creative_m12_skills.py -q -p no:cacheprovider --basetemp <unique-dir>
python -m pytest tests/hermes_cli/test_product_creative_m13_media_production.py -q -p no:cacheprovider --basetemp <C:\tmp\unique-m13-dir>
```

逐命令确认不会触发真实 workspace、外部 API、消息或费用。不要直接运行会修改 config 的开发启动脚本或 provider live 测试。

## 禁止事项

不清理原脏工作区、不覆盖用户改动、不升级依赖、不 push/release；未来业务/契约修改必须以 `docs/PRODUCT_AGENT_DIRECTION.md` 和当前里程碑为准，并经正常计划与用户授权。
