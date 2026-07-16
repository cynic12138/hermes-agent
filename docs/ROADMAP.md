# Roadmap

> 目标架构和 Final 1.0 定义见 `docs/PRODUCT_AGENT_DIRECTION.md`。本路线从当前真实代码和用户验收结果出发，不把技术链路通过写成创作质量完成。

## 已完成底座

### M0–M8：Product Creative durable runtime

已具备 Product Brain、产品摄入、素材、文案、图片、视频、灵感、审阅、反馈/学习、Provider、Receipt/Event 和恢复能力。细粒度开发过程保存在 `docs/history/product-creative-legacy/`，不得把其中旧规划当作当前状态。

### M9/M9.1：审阅恢复与 Desktop Plugin SDK

- M9 review/recovery console 已提交。
- M9.1 通用 Desktop Plugin SDK、plugin-owned 五视图、Node 22 build、分发扫描和离线安装 E2E 已提交为 `83b4e8f`。
- 尚未 push、tag、release。

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
- 本地提交、提交后回归、typecheck/build 和离线分发安装均完成；未 push/tag/release。

## 当前唯一开发阶段：M11 专业创意工作流与产物 Gate

完整实施节点、契约、状态、测试和拆仓观察点见 `docs/plans/2026-07-16-m11-professional-creative-workflow-plan.md`。

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

## M12：专业业务 Skills 与创意导演

- 任务导演、研究、创意策略、独立评审、编剧、分镜、卡审和学习分析 Skills。
- Web/XHS/Douyin 输出来源专属洞察。
- 默认稳定、变化、探索三个候选。
- Skill 定义触发、输入、输出、工具白名单、失败条件、Rubric 和正反案例。

## M13：Production Bible 与可靠媒体生产

- Provider Compiler 和逐镜头任务计划。
- 产品 plate/抠图、生成背景、确定性字幕和后期合成。
- 包装保真与生成式剧情兼容。
- 单镜头重试、异步恢复和 ffmpeg/本机依赖诊断。

## M14：自动质检、返修和学习质量

- 包装、文字、人物、剧情、字幕、音画和技术质量检查。
- QA Report、Repair Decision 和人工豁免。
- 通过/修改/拒绝及原因成为标准反馈。
- Product Grounding、Creative Profile、Channel Strategy、Production Knowledge 分层学习。
- 手动发布表现可选；不开发自动投放效果分析。

## M15：Desktop 内部试用版

- 产品 onboarding、模型配置状态和 Sidecar 诊断。
- 对话主入口与三个默认审阅节点。
- Tasks、Creative Review、Assets、Learning、Settings 连续体验。
- Windows 可安装内部测试包。
- 非技术运营人员无需 CLI/Prompt 独立完成完整任务。

## M16：母创意与受控规模化

- 通过结果升级为 Mother Creative。
- 按钩子、场景、人物、节奏和 CTA 生成受控变体。
- 队列、调用上限、去重、相似度和批量审阅。
- 不实现自动发布、自动投流或矩阵账号运营。

## Final 1.0

交付可安装的 Product-Centric Creative Studio：能从零建立产品认知，从一句自然语言目标完成研究、创意、生产、QA、交付、反馈和安全学习，并在质量稳定后小批量扩展。

## 主要风险

- 原脏工作区作为证据保留；新分支尚未 push，远端不是最新恢复源。
- `ctx.llm` 桥接限制使部分深度灵感摘要退化。
- exact-main 依赖外部 ffmpeg，且当前模板质量不足。
- 普通生成式视频无法保证包装中文文字。
- 当前 Review 主要是审阅包，自动 QA/返修尚未实现。
- Product Brain 学习数组仍混合产品、渠道和制作经验。

## 明确暂不开发

新 Provider/抓取平台、Theme Brain、GEO/自动发帖、自动投流/效果分析、无边界多 Agent 群、多人/多租户/计费/云 SLA、完整视频时间轴和大型创作画布。

发现的问题不自动进入 Roadmap；范围外想法写入 `docs/PARKING_LOT.md`。
