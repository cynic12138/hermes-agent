# Roadmap

> 目标架构和 Final 1.0 定义见 `docs/PRODUCT_AGENT_DIRECTION.md`。本路线从当前真实代码和用户验收结果出发，不把技术链路通过写成创作质量完成。

## 已完成底座

### M0–M8：Product Creative durable runtime

已具备 Product Brain、产品摄入、素材、文案、图片、视频、灵感、审阅、反馈/学习、Provider、Receipt/Event 和恢复能力。细粒度开发过程保存在 `docs/history/product-creative-legacy/`，不得把其中旧规划当作当前状态。

### M9/M9.1：审阅恢复与 Desktop Plugin SDK

- M9 review/recovery console 已提交。
- M9.1 通用 Desktop Plugin SDK、plugin-owned 五视图、Node 22 build、分发扫描和离线安装 E2E 已提交为 `83b4e8f`。
- pilot 分支已 push；未合并 main、未 tag、未 release。

### M10/M10.1：自然语言任务与真实外部链路

- M10 基线提交 `33d096f`：Creative Task、Readiness、主动追问、任务授权、Goal Planner、素材/灵感、Mock/Live provider、反馈学习和 Desktop 可见性。
- M10.1 工作区增量：Web/XHS/Douyin/VLM/豆包图片/Seedance 视频真实执行，Provider 轮询、下载、脱敏和恢复通过。
- 技术结论：外部能力可接通，任务可恢复，外部 evidence 未污染 Canonical Product Brain。
- 产品结论：现有 exact-main 样片只有主图、通用字幕和装饰；Seedance 样片会重绘包装文字。两者都是技术审计样本，不是合格产品视频。

## 已完成阶段：M10.2 重建基线收口

目标：

- 在独立 worktree 中只迁移经过测试的 Live 增量。
- 将用户对样片的拒绝原因固化为失败模式。
- 将 M0–M8 历史移出插件分发目录并建立索引。
- 为周十五产品建立证据优先严格基线。
- 重新运行必要回归并形成可恢复的本地提交；不 push/release。

完成条件：

- 明确区分“技术可运行”与“创作质量未完成”。
- 失败样片不会成为成功学习或正式交付。
- 新方向文档成为 Git 内权威入口。
- 原脏工作区和运行数据可通过校验过的归档恢复。
- 新开发分支不包含历史 runtime 数据、临时文件或密钥。
- 提交、回归、typecheck/build、离线分发安装和 pilot branch push 均完成；未合并 main、tag 或 release。

## 已完成阶段：M11 专业创意工作流与产物 Gate

完整实施节点、契约、状态、测试和拆仓观察点见 `docs/plans/2026-07-16-m11-professional-creative-workflow-plan.md`。

实现状态：`DONE_IN_PILOT_REF_UNPUBLISHED`。

目标：让真实生成依赖完整、可审阅的创意生产链。

核心交付：

- Creative Task Brief。
- Product Grounding Pack。
- Creative Candidates 与 Creative Decision。
- Story/Copy Package。
- Production Bible。
- QA Report。
- 产物驱动的 Goal Planner 和阶段 Gate。

验收：

- 空 `selected_idea`、空灵感、空剧情或缺失 Production Bible 时禁止调用真实 Provider。
- “帮我做一个今天能发的周十五产品视频”通过真实 Hermes 自然语言离线 E2E。
- 选中灵感真实进入剧情、分镜和 Provider 输入。
- 不再把通用字幕模板标记为剧情视频。

当前证据：

- 8 类版本化工件、Planner Gate、Provider Compiler、exact-main Story/Bible 接入和 Desktop 投影已完成。
- M11 31、M10 35、Live adapter 10、distribution 3、Desktop backend/page 12 项测试通过。
- 公共面保持 84 tools / 84 CLI；51 个 workflow action 契约无漂移。
- 周十五真实主图公开 `r1` 审阅包已形成：自然语言 preview-first 后选择 B，产品 4.0 秒出现，包装路线为 `exact-main-composite`，Preflight QA 为 PASS。

用户已于 2026-07-16 全部接受公开 `r1` 创意包并允许进入下一步。M11 尚未 commit、push、tag 或 release。

## 已完成阶段：M12 专业业务 Skills 与创意导演

进入条件：M11 创意包获得用户验收，且当前三个确定性候选的优缺点被转化为明确 Skill 需求。

- 任务导演、研究、创意策略、独立评审、编剧、分镜、卡审和学习分析 Skills。
- Web/XHS/Douyin 输出来源专属洞察。
- 默认稳定、变化、探索三个候选。
- Skill 定义触发、输入、输出、工具白名单、失败条件、Rubric 和正反案例。

实现状态：`DONE_IN_PILOT_REF_UNPUBLISHED`。

当前证据：

- 八个 Skill 已由 Catalog 校验并注册，生产无 executor 时 fail closed。
- Skill execution 保存版本、输入/输出哈希、允许工具、实际动作和失败状态。
- 固定候选、固定评分和固定剧情 profile 已由受控结构化 Skill 输出替换。
- Web、XHS、Douyin 和历史素材产生来源专属 Research Insight。
- stable/variation/exploration 候选具有历史结构相似度和 novelty strategy。
- creative-review 独立评审；硬包装/合规 Gate 优先于语义 PASS。
- script-writer、storyboard-director 和 compliance-guard 已进入 M11 工件链。
- Desktop 展示 Skill provenance、执行状态和历史相似度。
- 最终回归：M12 26、M11/M12 工件链 34、M10 35、Desktop backend/distribution/live 25、Desktop UI 14、bundle 2；M9 recovery、contract invariants、public surface、typecheck/build 均通过。

实施与恢复证据见 `docs/M12_PROFESSIONAL_BUSINESS_SKILLS_IMPLEMENTATION.md`。
M12 尚未 commit、push、tag 或 release。

## 已完成离线阶段：M13 Production Bible 与可靠媒体生产

- Provider Compiler 和逐镜头任务计划。
- 产品 plate/抠图、生成背景、确定性字幕和后期合成。
- 包装保真与生成式剧情兼容。
- 单镜头重试、异步恢复和 ffmpeg/本机依赖诊断。

实现状态：`DONE_IN_PILOT_REF_UNPUBLISHED_LIVE_GATE_PENDING`。

当前证据：

- 五类媒体工件、逐镜头 Shot Graph、Product Plate、确定性 ASS 字幕和本地
  H.264/AAC compositor 已完成。
- 自然语言 preview-first → 方向选择 → 生产确认 → 任务授权 → 多镜头真实本地 MP4
  E2E 已通过。
- 成功镜头可复用，失败镜头可独立 attempt/resume；任务和媒体路径按 workspace 隔离。
- M10–M13 回归 `119 passed`；Desktop UI `17 passed`、bundle `2 passed`、
  typecheck/build、M9 recovery 25/25、public surface 84/84 均通过。
- 临时分发包通过版本/哈希/敏感扫描和 enabled user-plugin 离线安装。

剩余 Live Gate：

- 真实豆包/Seedance 逐镜头异步提交、轮询、下载、重启恢复和最终合成。
- 正式 Desktop 包自带或可配置的 ffmpeg/ffprobe。

实施与恢复证据见 `docs/M13_RELIABLE_MEDIA_PRODUCTION_IMPLEMENTATION.md`。

## 已完成本地阶段：M14 自动质检、返修和学习质量

逐节点实施计划：
`docs/plans/2026-07-16-m14-automatic-media-qa-repair-plan.md`。

- 技术、字幕/OCR、包装保真、人物/场景、剧情连续性和音画检查已接入。
- QA Report、Repair Decision、Human Override 和最多两轮局部返修已完成。
- 自然语言恢复只重做失败镜头；通过/警告接受/拒绝形成审计和学习证据。
- 未确认学习不会写 Canonical Product Brain。
- M14 专项 `25 passed`、M10–M14 `145 passed`；Desktop、构建、M9/public surface、
  分发扫描和 enabled user-plugin 离线安装通过。
- 依赖与恢复修复后的 2026-07-17 补充回归：M13 `39 passed`、M14 `30 passed`、
  M10–M14 与来源适配器组合 `191 passed`；Desktop 定向 `17 passed`。

实现状态：
`DONE_IN_PILOT_REF_UNPUBLISHED_LIVE_GATE_AND_USER_ACCEPTANCE_PENDING`。

剩余门禁：

- 用户已明确授权，但 Codex 租户策略仍禁止外发 workspace 产品资料；新调用为 0。已有真实
  五图与 exact-main 成片形成 `REPAIR` 案例，仍缺真实 QA PASS 和返修后生成。安全下一步是
  用户在 Codex 外部提供去敏结果，Codex 本地导入和 QA。执行真源见
  `docs/M14_LIVE_GATE_20260717.md`。
- 用户亲自验收一条 QA PASS 和一条自动返修案例。

实施与恢复证据见 `docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md`。

## M13.1 / M14.1：动态镜头与动作质量收口

- exact-main 视频默认使用 Seedance 生成无产品的动态场景/人物/动作，Product Plate 与
  字幕继续本地确定性合成。
- Seedance 4–15 秒约束已进入 Provider Registry；短故事镜头在 Provider 端扩展后按
  Production Bible 时长裁剪。
- 动态镜头高冻结比例直接失败；VLM 必须验证计划动作是否完成。
- 已通过真实变化 fake async MP4、重启不重复提交、冻结 shot-scoped repair 和完整
  分发/Display Gate。
- 状态：`DONE_IN_PILOT_REF_UNPUBLISHED_LIVE_ACCEPTANCE_PENDING`。
- 下一门禁：外部生成一组去敏动态 Seedance shots，本地合成/QA/返修并由用户验收。
- 证据：`docs/M13_1_DYNAMIC_SHOT_PRODUCTION_IMPLEMENTATION.md`。

## M15：Desktop 内部试用版

状态：`PACKAGED_FRESH_INSTALL_AND_PLUGIN_UI_ACCEPTED_UNPUBLISHED_OPERATOR_FULL_FLOW_PENDING`。

已实现：

- 产品 onboarding；描述只进入 Evidence/Draft，不自动确认 Canonical Brain。
- Overview 自然语言任务与预设、Tasks 无 task ID 恢复、产品事实/创意方向/成片质量三个审阅节点。
- Overview、Tasks、Review、Assets、Learning、Settings 六视图连续体验。
- `DOUBAO_API_KEY` 优先级、real-provider、ffmpeg/ffprobe 和可选 XHS/Douyin 的无密钥诊断。
- workspace、`zh-CN` 和 cleanup 隔离；cleanup RED→GREEN 修复了旧 DOM 仍可触发聊天的问题。
- 分发扫描、版本/哈希、enabled user-plugin 离线安装和 Windows NSIS Desktop 壳构建通过。
- 本地“打包壳 + 当前 worktree runtime + 隔离 user plugin”后端、bundle、诊断和 onboarding 通过。
- 新 NSIS 固定到 `a0081dd`，通过代理仅限当前进程的隔离 fresh-install；固定 runtime、seed
  user-plugin、认证 API、动态插件深链和 Overview/Tasks/Review/Assets/Learning 真实 Electron 验收通过。
- 首次真实 UI 发现 `:sessionId` 吞掉插件路由；`a0081dd` 以通用 route surface 修复并完成重装复验。

剩余完成门禁：

- 方案 A、仓库来源修复、`a0081dd` 深链修复和 packaged fresh-install 均已完成并推送至 origin pilot ref。
- 修复/确认 Electron `userData` 与最近项目状态隔离；正式 Hermes 目录在验收窗口出现时间戳变化，
  当前因果关系 `UNKNOWN`，在关闭前不得宣称零触碰。
- 一名内部运营人员在可复现安装形态中完成 onboarding → 自然语言任务 → 三节点审阅 → 中断恢复 → 反馈/学习全链。
- 由产品/内容负责人记录可发布质量 Rubric 和接受/修改结论。
- 证据与操作脚本：`docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md`、
  `docs/M15_PACKAGED_SEED_PLUGIN_ACCEPTANCE_20260720.md`。

M14 真实动态样片 Gate 与 M15 人工可用性 Gate 相互独立；不能用其中一个替代另一个。

## M16：母创意与受控规模化

- 通过结果升级为 Mother Creative。
- 按钩子、场景、人物、节奏和 CTA 生成受控变体。
- 队列、调用上限、去重、相似度和批量审阅。
- 不实现自动发布、自动投流或矩阵账号运营。

## Final 1.0

交付可安装的 Product-Centric Creative Studio：能从零建立产品认知，从一句自然语言目标完成研究、创意、生产、QA、交付、反馈和安全学习，并在质量稳定后小批量扩展。

## 主要风险

- 原脏工作区作为证据保留；重建 pilot 分支已 push，main 和正式发布线保持不变。
- `ctx.llm` 桥接限制使部分深度灵感摘要退化。
- M13 当前依赖本机其他软件内置 ffmpeg/ffprobe，Desktop 分发尚未自带媒体工具。
- 普通生成式视频无法保证包装中文文字。
- M14 默认没有真实 OCR/VLM adapter 时会进入 HUMAN_REVIEW；真实阈值尚未校准。
- Product Brain 学习数组仍混合产品、渠道和制作经验。
- M12 的真实创意质量仍依赖所配置 LLM；离线 fixture 只证明契约和编排，不证明最终媒体质量。
- 临时分发已能包含未提交第一方源码并通过离线安装，但 dirty build 仍不能正式发布。
- M13 fixture 证明媒体生产边界，不证明真实 Provider shot 的创意质量或异步恢复。
- M14 fixture 证明 QA/返修契约和隔离，不证明真实 VLM 对包装、文字和连续性的稳定判断。

## 明确暂不开发

新 Provider/抓取平台、Theme Brain、GEO/自动发帖、自动投流/效果分析、无边界多 Agent 群、多人/多租户/计费/云 SLA、完整视频时间轴和大型创作画布。

发现的问题不自动进入 Roadmap；范围外想法写入 `docs/PARKING_LOT.md`。
