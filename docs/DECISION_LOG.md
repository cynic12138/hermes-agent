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

无法确认来源或理由的历史选择未写成确定事实。
