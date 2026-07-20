# Decision Log

| 日期 | 决策 | 背景/理由 | 替代/放弃 | 影响 | 证据 | 有效性 |
|---|---|---|---|---|---|---|
| 2026-07-08 前 | Product Creative 是 Hermes 插件 | 保持宿主窄腰 | 产品专属 core 实现 | 插件/工具注册 | `PRODUCT_AGENT_DIRECTION.md:346-398`；根 AGENTS footprint ladder | 是 |
| 2026-07-07 | M3 不引入重型向量库 | 复用 image analysis/material cards | 复杂向量检索 | 素材架构 | Roadmap:351-385 | 是 |
| 2026-07-08 | real provider 默认关闭并确认门控 | 成本、安全、数据边界 | 自动 live 调用 | provider/policy | README:44-48；`provider_gateway.py:13-16` | 是 |
| 2026-07-08 | 学习经 proposal + confirmation | 防止污染长期认知 | 自动写回 | learning/recovery | runtime architecture:173-204 | 是 |
| 2026-07-08 | 固定主图走 exact-main-video | 防止包装被重绘 | 默认 image-to-video | video | conversation protocol:19-23 | 是 |
| 2026-07-12 | SQLite + workspace files | 事务/恢复/审计且大媒体不入 DB | 纯 JSON durable state | data/recovery | `1d223d3`；`database.py:19-37` | 是 |
| 2026-07-12 | M9 review/recovery console | 长流程需可见和受控恢复 | 仅脚本/对话 | API/Desktop | `f8bdb0c` | 是 |
| 2026-07-15 | M9.1 通用 Desktop Plugin SDK | 插件拥有 UI，宿主保持通用，避免 Product Creative 业务回流 core | 固定 Product route/component | Desktop/distribution | 用户批准的 M9.1 计划；`83b4e8f`；`docs/M9_1_DESKTOP_PLUGIN_SDK_IMPLEMENTATION.md` | 是 |
| 2026-07-15 | 版本采用 `9.1.0-alpha.1` | 必须从独立仓库已有 `9.0.0` 单调升级 | `0.9.0-alpha.1` | 安装/升级/CI/分发元数据 | 用户批准计划；`plugin.yaml:2`；distribution validator | 是 |
| 2026-07-15 | 内层插件目录是唯一源码真源 | 独立仓库是自动生成分发物，避免双向维护和漂移 | 在独立仓库直接开发业务代码 | 发布/恢复/维护 | 用户批准计划；publish workflow；`SOURCE.json` contract | 是 |
| 2026-07-15 | Desktop v1 仅加载 enabled bundled/user plugin | project plugin 不得向 Desktop 注入同源可执行代码；enabled plugin 明确视为受信任 | 自动执行 project plugin 页面 | Desktop security | `web_server.py`；registry/API tests；离线 user-plugin E2E | 是 |
| 2026-07-15 | M10 合并“建脑”和“自主创作” | 产品认知必须直接服务任务，任务反馈又安全反哺认知 | 独立建脑向导、单一“今日视频”命令 | product/runtime/UX | 用户批准的 M10 计划；`docs/M10_PRODUCT_COGNITION_AUTONOMOUS_CREATION_IMPLEMENTATION.md` | 是 |
| 2026-07-15 | Evidence/Draft/Canonical/Task Context 四层隔离 | 临时搜索、模型推断和单次创意不能污染长期产品事实 | 网页预填 Brain、ingest 直接写 Canonical | brain/ingest/learning | `brain/discovery.py`；`capabilities/product/ingestion_service.py`；M10 tests | 是 |
| 2026-07-15 | M10 复用单入口与能力注册表 | 保持 Hermes 窄腰并避免平行 Agent/workflow | 新聊天工具、新任务 DB、自由 LLM 工具执行 | public surface/runtime | `runtime/agent.py`；`application/planner.py`；84/84 golden | 是 |
| 2026-07-15 | 外部副作用采用任务授权，Brain 写回独立确认 | 费用/Cookie/数据源授权只对当前任务有效；长期认知风险更高 | 一次授权同时允许抓取、付费和 Brain 写回 | authorization/provider/learning | `runtime/authorization.py`；M10 authorization/learning tests | 是 |
| 2026-07-15 | Live Provider 双重 opt-in | 防止仅有授权记录就从开发/恢复环境发起真实调用 | 授权后自动打开 Provider | provider safety/recovery | `runtime/creative_tasks.py`；Fake Gateway test | 是 |
| 2026-07-16 | Product Brain 从“整体大脑”重新定位为产品真实性与长期认知底座 | 真实样片证明懂产品不等于会选题、会制作或会质检 | 继续只扩充 Product Brain | 产品定义、认知架构、Roadmap | 用户产品讨论；`docs/PRODUCT_AGENT_DIRECTION.md` | 是 |
| 2026-07-16 | 采用专业工作流 + Skills/Capabilities/Gates，而非无边界多 Agent 群 | 多个自由 Agent 会放大上下文漂移、错误、成本和不可恢复性 | “灵感大师/编剧大师/卡审大师”自由互聊 | runtime、skills、workflow、测试 | 用户确认；`docs/PRODUCT_AGENT_DIRECTION.md` | 是 |
| 2026-07-16 | 生成文件不等于创作完成 | exact-main 样片只有通用字幕，Seedance 样片包装文字乱码；技术链路通过但产品质量失败 | 只做 Provider 连通与结果下载验收 | Creative Gate、Production Bible、QA、Roadmap | M10.1 真实结果与用户反馈；`docs/M10_LIVE_PROVIDER_AND_SOURCE_INTEGRATION.md` | 是 |
| 2026-07-16 | 早期核心指标为可发布内容/运营投入，而非原始生成量 | 大量不可用视频不能降低业务成本 | 直接追求每日上千条生成 | 产品指标、批量阶段顺序 | 用户产品讨论；`docs/PRODUCT_AGENT_DIRECTION.md` | 是 |
| 2026-07-16 | 第一阶段学习由通过/修改/拒绝及原因驱动，发布表现仅手动选填 | 先建立内部质量标准，避免少量平台数据误导长期学习 | 自动投放与效果分析 | feedback、learning、Desktop | 用户确认；`docs/PRODUCT_AGENT_DIRECTION.md` | 是 |
| 2026-07-16 | 产品稳定前采用方案 1，同仓开发、稳定后拆分 | 当前契约、workflow 和 Desktop 边界仍在快速变化；立即拆仓会叠加依赖、测试、发布和双仓调试成本 | 立即把独立仓库改为源码真源 | repository、CI、release、handoff | 用户明确选择；`docs/REBASELINE_AND_CLEANUP_20260716.md`；M11 plan | 是 |
| 2026-07-16 | 从干净 Git 基线选择性迁移，不在原脏工作区继续叠加 | 需要保留真实调用证据，同时避免临时数据和未验证修改进入新基线 | 清理原工作区后继续、整包复制脏目录 | recovery、testing、Git | archive SHA-256、RED→GREEN 结果、rebaseline branch | 是 |
| 2026-07-16 | 周十五初始化采用证据优先严格基线 | 用户原始描述含高风险健康与适用人群表述；外部/模型信息不能自动成为事实 | 把用户描述和网页资料直接预填 Canonical Brain | Product Brain、compliance、readiness | `docs/product-bases/zhou-shiwu-honeydew/STRICT_BASELINE.md` | 是 |
| 2026-07-16 | M0–M8 历史移出插件发行包但保留 Git 历史 | 历史过程对恢复有价值，但旧脚本和规划会增加分发体积并误导当前开发 | 删除历史、继续随插件发布 | distribution、recovery、documentation | `git mv`；`docs/history/product-creative-legacy/README.md` | 是 |
| 2026-07-16 | M11 以 8 类版本化工件作为真实生成前置 Gate | 技术链路成功不能证明创意质量；旧样片曾在空创意/通用模板下进入生成 | 继续只依赖静态 action list、selected_idea 或原始 Prompt | planner、runtime、provider、Desktop、recovery | `contracts/creative_artifacts.py`；`runtime/creative_direction.py`；M11 31 tests | 是 |
| 2026-07-16 | Provider 视频 Prompt 必须由 Production Bible 编译 | 用户原始描述不足以承担逐镜头执行、连续性、素材角色和包装边界 | 把 raw user message 直接发送给视频 Provider | provider payload、审计、可恢复性 | `provider_payloads.py`；M11 compiler tests | 是 |
| 2026-07-16 | 包装保真要求同时由自然语言解析和 Preflight QA 防守 | 实际审阅 fixture 发现“包装外观和文字不得变化”未命中旧关键词，错误选择 reference-guided generation | 仅增加一个精确短语、只依赖请求 Boolean | intent、Production Bible、QA | RED→GREEN 5 tests；`requires_exact_packaging`；周十五审阅 fixture | 是 |
| 2026-07-16 | 用户对产品出场时点的修订必须改变 Production Bible，而非只留在文本记录 | 周十五工程任务 `r2` 收到“第 4 秒出现”后仍按固定第 4 镜头在 6 秒出现，证明方向选择不等于执行约束落地 | 只在 selection reason 中保留用户原话 | revision、shot planning、provider input、QA | RED→GREEN revision test；`runtime/creative_direction.py`；公开审阅任务 `r1` | 是 |
| 2026-07-16 | preview-first 的候选选择必须通过同一公开任务继续，而不是内部脚本编译 | 原实现能返回三候选，但 `product_workflow_run(task_id, message)` 无法接受用户选择并形成 Story/Bible | 把人工审阅包作为独立内部脚本产物 | conversation UX、revision、audit、provider gate | RED→GREEN public continuation test；`task-2e495b5048ed4f45a62be4e05f59b6ad` | 是 |
| 2026-07-16 | Preflight QA 区分可修改创意问题与硬阻塞 | 通用剧情/文案问题可以通过 revision 修复，不应与 Grounding、包装路线或生产条件不足混为 `BLOCKED` | 所有 QA 失败统一标记 `BLOCKED` | QA、task state、Desktop diagnosis | `NEEDS_REVISION` RED→GREEN test；`ensure_preflight_qa` | 是 |
| 2026-07-16 | M11 技术 PASS 不等于阶段 DONE | Preflight 证明结构、安全和可执行性，但产品创意仍需用户判断 | 测试通过后自动进入 M12 或真实生成 | Roadmap、handoff、acceptance | `docs/reviews/M11_ZHOU_SHIWU_CREATIVE_PACK_REVIEW.md` | 是 |
| 2026-07-16 | M12 专业角色实现为八个版本化业务 Skill，不建立自由 Agent 群 | 需要复用 Hermes Runtime，同时控制上下文漂移、工具权限、失败恢复和审计 | 多个“创意大师”Agent 自由互聊；继续把方法硬编码在 workflow | skills、runtime、artifact、Desktop | `runtime/business_skills.py`；`skills/*`；`docs/M12_PROFESSIONAL_BUSINESS_SKILLS_IMPLEMENTATION.md` | 是 |
| 2026-07-16 | 创意判断由 LLM Skill 负责，产品与生产硬约束由确定性 Capability/Gate 负责 | 专业创意需要模型判断，但包装、授权、素材、时间和合规不能依赖模型自觉 | 全部确定性模板；让 LLM 自由决定全部生产约束 | creative direction、QA、provider safety | `runtime/creative_direction.py`；M12 hard-failure tests | 是 |
| 2026-07-16 | Business Skill Runtime 无 executor 时 fail closed | 固定 fallback 会再次产生“形式完整但创意空洞”的伪专业结果 | 无 LLM 时自动使用固定候选/剧情 | runtime、recovery、testing | `runtime/business_skills.py`；M12 no-executor test | 是 |
| 2026-07-16 | M12 使用结构化历史相似度，不引入向量数据库 | 当前只需识别钩子、冲突、推进、产品角色和结尾的重复，重型检索会提前平台化 | 新向量库；只比较文字表面 | creative strategy、novelty gate | `runtime/creative_direction.py`；M12 similarity tests | 是 |
| 2026-07-16 | M13 采用混合 Shot Graph，而非整条视频模型或纯本地模板 | 整条生成无法保证包装文字，纯模板无法承担剧情表现；逐镜头混合路线可审计、局部重试并保留包装 | 整条 Seedance 直接生成；固定主图通用字幕 | media production、provider、recovery | `docs/plans/2026-07-16-m13-reliable-media-production-design.md`；M13 tests | 是 |
| 2026-07-16 | 产品包装和文字不进入生成模型 | Prompt 无法提供逐像素包装保证；产品应以不可变 plate 在后期合成 | 让视频模型参考主图并承诺不改包装 | product plate、provider payload、compositor | `runtime/product_plate.py`；`provider_shots.py`；自然语言 MP4 E2E | 是 |
| 2026-07-16 | 中文字幕和品牌文字使用确定性 ASS 后期渲染 | 生成模型容易产生中文乱码，且不可审计字体和内容 | 让图片/视频模型直接绘制字幕 | media compositor、QA、delivery | `runtime/media_compositor.py`；ffprobe E2E | 是 |
| 2026-07-16 | M13 成功镜头持久化，恢复只重试失败镜头 | 视频异步耗时且可能付费，整条重跑会浪费成功结果并重复扣费 | 任一失败后重跑整条任务 | media artifacts、idempotency、recovery | `runtime/media_production.py`；M13 recovery tests | 是 |
| 2026-07-16 | M13 离线 Gate 与真实 Provider Live Gate 分离 | fixture 能证明契约、合成和恢复，但不能证明真实异步 Provider；不得把 mock 冒充 live | 离线通过即宣称真实生产完成 | status、release、user authorization | `docs/M13_RELIABLE_MEDIA_PRODUCTION_IMPLEMENTATION.md` | 是 |
| 2026-07-16 | Release candidate 导出包含未提交但未忽略的第一方源码 | M11–M13 在用户批准提交前也必须能进行完整独立安装验收；tracked-only 导出曾漏掉新模块 | 只有 commit 后才能发现漏包 | distribution、gate、recovery | `scripts/export_distribution.ps1`；offline install regression | 是 |
| 2026-07-17 | 生成媒体必须通过不可变 QA Report 才能进入交付 | 可播放文件不等于可发布，且旧样片曾出现黑帧、乱码和包装问题 | 合成成功即进入 AWAITING_FEEDBACK | media production、task state、Desktop | `runtime/media_qa.py`；`docs/M14_AUTOMATIC_MEDIA_QA_REPAIR_IMPLEMENTATION.md` | 是 |
| 2026-07-17 | 确定性检查优先于 OCR/VLM，adapter 不可用时返回 UNKNOWN | 包装 hash、编码和授权等硬事实不能被语义模型的 PASS 覆盖 | 让单一多模态模型决定最终质量；adapter 缺失时默认通过 | QA、safety、Live Gate | `runtime/media_technical_qa.py`；`runtime/packaging_visual_qa.py`；M14 tests | 是 |
| 2026-07-17 | 自动返修只处理失败镜头并最多执行两轮 | 视频调用耗时且可能付费，整条重跑会浪费成功结果并形成无限循环 | 任一失败重跑整条；无限自动重试 | repair、provider、idempotency、recovery | `runtime/media_repair.py`；M14 natural-language E2E | 是 |
| 2026-07-17 | 人工质量决定不覆盖原 QA Report，必须确认并保存 receipt/audit | 需要保留机器判断与人工豁免的差异，避免事后改写证据 | 直接修改 QA 结果；无原因的一键通过 | review、audit、Desktop、recovery | `runtime/media_review.py`；`dashboard/plugin_api.py`；M14 tests | 是 |
| 2026-07-17 | QA 与人工反馈只形成学习证据，不自动写 Canonical Product Brain | 单次媒体问题可能是任务或 Provider 偶发，不能直接污染长期产品事实 | reject/approve 自动改 Brain | learning、Product Brain、confirmation | `runtime/media_review.py`；Brain hash regression | 是 |
| 2026-07-17 | exact-main 视频采用动态 Provider 背景与本地不可变 Product Plate 的混合路线 | 静态图片循环保护了包装，却无法交付真实人物/场景动作 | 继续图片循环；让 Seedance 重绘完整产品 | media plan、provider、compositor、packaging | `docs/M13_1_DYNAMIC_SHOT_PRODUCTION_IMPLEMENTATION.md`；M13 dynamic async E2E | 是 |
| 2026-07-17 | 动态镜头必须同时通过冻结比例与动作完成度门禁 | 可播放 MP4、人物/场景相似都不能证明镜头发生了计划动作；EOF 冻结曾被漏报 | 只看封装/时长；只由 VLM 主观判断 | technical QA、VLM QA、repair | `media_technical_qa.py`；`story_continuity_qa.py`；M14 frozen/action tests | 是 |
| 2026-07-17 | XHS/Douyin 是可选研究来源，不是创作硬依赖 | 普通 Web、Product Brain、本地和历史素材通常已足够，平台登录/限流不应阻断生产 | 每条视频固定抓取两个平台 | research、authorization、UX | `runtime/authorization.py`；M10 channel authorization test | 是 |
| 2026-07-17 | M15 Desktop 是引导工作台，Hermes chat 仍是执行入口 | 需要降低运营人员的 Prompt/CLI/task ID 负担，同时避免第二套 Agent loop 和任务状态 | Desktop 直接复制业务编排；只保留只读五视图 | Desktop、Agent Runtime、recovery | `desktop_ui/index.js`；M15 UI tests；`docs/M15_DESKTOP_INTERNAL_PILOT_IMPLEMENTATION.md` | 是 |
| 2026-07-17 | Onboarding 描述只进入 Evidence/Draft | 运营人员初始描述可能不完整或包含高风险表述，不能自动变成产品事实 | 创建产品时直接确认全部描述 | Product Brain、ingest、audit | `POST /v1/products`；M15 Brain hash tests | 是 |
| 2026-07-17 | M15 继续复用现有 Hermes Desktop Electron/NSIS 薄安装架构，但 standalone Gate 必须校验 runtime stamp | 当前目标是尽快取得内部可用性证据，独立品牌和预捆绑媒体工具会扩大范围；实际构建证明 NSIS 只含 Desktop 壳，dirty worktree 不会自动进入首次启动 runtime | 立即重做独立 Creative Studio 安装器；把壳构建成功等同于 M15 可独立安装 | packaging、release、pilot | `apps/desktop/package.json`；`write-build-stamp.cjs`；M15 implementation record | 是；可获取 ref/bootstrap 尚待决策 |
| 2026-07-17 | Desktop 诊断只返回存在性且 Sidecar 固定 loopback | 运营需要知道环境缺口，但不能把密钥暴露给 renderer，也不能形成任意 URL 探测 | 返回凭据值；允许用户指定诊断 URL；把 XHS/Douyin 设为必需 | security、Settings、optional sources | `runtime/desktop_diagnostics.py`；M15 diagnostics tests | 是 |
| 2026-07-17 | 本地打包试运行使用显式 worktree runtime + enabled user plugin，不把它冒充干净机器安装证据 | 原生隔离环境已证明 backend、bundle、diagnostics 和 onboarding 可运行，但 install stamp 仍指向旧 HEAD | 隐瞒 worktree override；直接把 EXE 交给运营 | pilot、recovery、documentation | `m15-pilot-native-20260717-1720`；M15 implementation record | 是 |
| 2026-07-20 | M15 采用方案 A：推送可获取 pilot ref，不合并 main、不 tag/release | 薄安装器必须从 Git ref 获取包含 M15 的 runtime；本地 worktree override 不能作为运营交付 | 重做通用 bootstrap；继续仅本机预装 | git、packaging、pilot | 用户明确授权；实现提交 `25e26df`；origin pilot branch | 是；installer rebuild pending |

无法确认来源或理由的历史选择未写成确定事实。
