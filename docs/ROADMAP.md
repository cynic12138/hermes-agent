# Roadmap

## 已完成底座：M9.1（DONE，本地已提交，未 push/release）

1. 已确认通用 Desktop Plugin SDK + plugin-owned UI 方向，版本为 `9.1.0-alpha.1`。
2. 已完成无外部 provider 副作用的 Node/Python 定向测试、Node 22 typecheck/build。
3. 已完成 tracked-only 导出、`SOURCE.json` 哈希、敏感数据扫描和离线 enabled user-plugin 安装。
4. 已验证 backend → bundle → registry → route/mount → API → review/confirmation/recovery。
5. 实现已提交为 `83b4e8f`；保持不 push/tag/release，等待用户分别授权。
6. 已形成 M9.1 实施恢复说明：`docs/M9_1_DESKTOP_PLUGIN_SDK_IMPLEMENTATION.md`。

验收：focused tests、typecheck/build、M9 recovery/public surface、隔离 E2E 通过；source 行为、版本、升级/回滚、无敏感数据分发均明确。

## 当前阶段：M10 产品认知驱动的自主创作（PARTIAL，本地提交 `33d096f`，未 push/release）

已实现自然语言 Creative Task、Evidence/Draft/Canonical/Task Context 分层、Readiness 与主动追问、有界 Goal Planner、任务授权、灵感/素材编排、Mock 文图视频交付、反馈 proposal/确认写回、Desktop 五视图增量和真实 Provider 的默认关闭 runner。

M10 仍未 DONE：真实网页/XHS/抖音和真实视频 Provider 未现场运行，用户尚未验收一次新产品建脑和一次真实视频。计划/状态见 `docs/plans/2026-07-14-m10-zero-to-product-brain-plan.md`，实现恢复见 `docs/M10_PRODUCT_COGNITION_AUTONOMOUS_CREATION_IMPLEMENTATION.md`。

## 下一阶段：M10.1 Live 纵向验收与适配器硬化（PLANNED）

只选择现有一个视频 Provider 和一个或多个已存在数据源，以“周十五蜂蜜露”当前确认主图做小调用上限验收：授权研究 → 素材选择 → 视频提交/轮询 → 可播放结果 → 反馈 → Brain 污染检查。不得在该阶段新增 Provider、抓取器或大型 UI。

依赖：用户确认测试素材、Provider、凭据、允许来源/Cookie、费用上限和实际执行窗口。验收：不重复扣费、失败可恢复、结果可播放、包装边界可解释、外部 evidence 不写 Canonical Brain。

## 风险

M10/M9.1 尚未 push、全量宿主 UI 既有失败、enabled plugin 信任边界、remote media descriptor、外部 provider/sidecar 不可复现。

## 明确暂不开发

新 provider/抓取/向量库/消息队列；完整 Web/团队/多租户/计费/云 SLA；自动发布或未经确认的付费调用/知识写回。

发现的问题不自动进入 Roadmap；范围外想法写入 `docs/PARKING_LOT.md`。
