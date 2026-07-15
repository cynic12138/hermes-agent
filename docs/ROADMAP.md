# Roadmap

## 当前阶段：M9.1 收口（DONE，本地已提交，未 push/release）

1. 已确认通用 Desktop Plugin SDK + plugin-owned UI 方向，版本为 `9.1.0-alpha.1`。
2. 已完成无外部 provider 副作用的 Node/Python 定向测试、Node 22 typecheck/build。
3. 已完成 tracked-only 导出、`SOURCE.json` 哈希、敏感数据扫描和离线 enabled user-plugin 安装。
4. 已验证 backend → bundle → registry → route/mount → API → review/confirmation/recovery。
5. 实现已提交为 `83b4e8f`；保持不 push/tag/release，等待用户分别授权。
6. 已形成 M9.1 实施恢复说明：`docs/M9_1_DESKTOP_PLUGIN_SDK_IMPLEMENTATION.md`。

验收：focused tests、typecheck/build、M9 recovery/public surface、隔离 E2E 通过；source 行为、版本、升级/回滚、无敏感数据分发均明确。

## 下一阶段：M10 产品定义与设计门禁（PLANNED，尚未获实现授权）

让用户只提供产品名称、少量素材或目标后，由 Hermes 主动发现 Product Brain 缺口、索要证据、区分 Evidence/Draft/Canonical、逐字段确认，再进入 guided generation。现有空白 Wiki、conversation adapter、ingest 和 writeback guard 可复用，但真实自由对话从 0 建脑尚未验收。

下一任务的实施计划已写入 `docs/plans/2026-07-14-m10-zero-to-product-brain-plan.md`。其第一版只实现自然语言 discovery、Evidence/Draft/Canonical 分层、字段确认和生成 readiness；未经用户再次授权不得实现。不得把网页检索结果作为 Product Brain 默认初始化数据。

## 风险

未 push 的本地提交丢失、全量宿主 UI 既有失败、enabled plugin 信任边界、remote media descriptor、外部 provider/sidecar 不可复现。

## 明确暂不开发

新 provider/抓取/向量库/消息队列；完整 Web/团队/多租户/计费/云 SLA；自动发布或未经确认的付费调用/知识写回。

发现的问题不自动进入 Roadmap；范围外想法写入 `docs/PARKING_LOT.md`。
