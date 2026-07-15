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

无法确认来源或理由的历史选择未写成确定事实。
