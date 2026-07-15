# Conflicts and Unknowns

## 主要冲突

1. **CONFLICTED — 当前阶段**：旧 Roadmap 仍说主优先级是 Hermes chat/M8；HEAD 已到 M9，工作区已到 M9.1。
2. **CONFLICTED — Desktop 架构**：HEAD 是核心内固定 Product Creative 页面；工作区目标是通用 Desktop Plugin SDK + plugin-owned bundle。
3. **CONFLICTED — 版本**：HEAD `9.0.0`；工作区 `0.9.0-alpha.1`。
4. **CONFLICTED — 存储文档**：旧架构强调 JSON/JSONL durable state；当前 SQLite 是运行真源，文件保留媒体/artifact/兼容职责。
5. **CONFLICTED — “完成”措辞**：Roadmap 的 M4–M8 closeout 多数证明契约/脚本闭环，不代表所有 production provider 默认可用。
6. **CONFLICTED — 单一路径**：架构要求 CommandBus 单一路径，但 `tool_handlers.py` 仍有直接 handler 调用表面。

## 高优先级 UNKNOWN

- M9.1 是否为用户确认的正式发布方向。
- `0.9.0-alpha.1` 如何从 `9.0.0` 升级。
- 目标用户是个人、内部团队还是公开分发用户。
- 正式 MVP 是否包含 Desktop guided launch。
- sidecar/真实 provider 的支持级别与 SLA。
- 历史 workspace 数据迁移与保留策略。
- 当前机器完整 Desktop build/E2E 是否通过。
- 早于 `1d223d3` 的细粒度 Git 历史。

## 风险排序

1. 未提交 M9.1 文件丢失或不完整保存。
2. 未验证的跨层迁移造成 Desktop build/运行断裂。
3. 版本/发布语义错误导致安装更新失效。
4. workspace header、本地绝对路径暴露及敏感产品资料保留策略。
5. 文档时代混用导致下一会话从错误阶段继续。
