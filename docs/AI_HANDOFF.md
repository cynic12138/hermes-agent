# AI Handoff

- 最后更新：2026-07-15
- 分支：`product-creative-runtime`
- 当前 HEAD：进入项目时运行 `git rev-parse HEAD`；M10 实现提交为 `33d096f`
- M9.1 实现基线：`83b4e8f`
- 当前阶段：M10 PARTIAL，已本地提交/未推送/未发布

## 新会话先读

1. `AGENTS.md`
2. `docs/AI_HANDOFF.md`
3. `docs/PROJECT_STATE.md`
4. `docs/MVP_SCOPE.md`
5. `docs/ARCHITECTURE_CURRENT.md`

M10 必读 `docs/M10_PRODUCT_COGNITION_AUTONOMOUS_CREATION_IMPLEMENTATION.md` 和 `docs/plans/2026-07-14-m10-zero-to-product-brain-plan.md`。M9.1 SDK/插件 UI/分发再读 `docs/M9_1_DESKTOP_PLUGIN_SDK_IMPLEMENTATION.md`。

审计证据：`docs/recovery/20260712-154151/`。

## 当前目标与阶段

长期 Product Brain 驱动、可审阅/可恢复的产品内容闭环。M10 正把自然语言了解产品、任务规划、灵感/素材、文图视频生成和安全学习串成同一 Creative Task；离线链路已实现，Live 用户验收未完成。

## 最近完成

- `1d223d3` durable runtime 基线。
- `f8bdb0c` M9 review/recovery console。
- `822d879` Windows plugin clone 删除修复。
- `83b4e8f` M9.1：`9.1.0-alpha.1`、通用 SDK、五视图、确认门禁、Node 22 build、离线安装 E2E、分发扫描。
- 发布 workflow 的 Vitest 调用已固定在 `apps/desktop` 工作目录；M9.1 实施和恢复细节已写入专题文档。
- M10 新增四个任务/认知契约、Readiness/追问、Goal Planner、任务授权、研究降级、Mock 文图视频、Live provider 提交/恢复、反馈学习与 Desktop task 可见性。
- M10 保持 84 tools / 84 CLI，不增加 Product Creative core tool；真实 Provider 默认关闭。

## 当前待办/下一入口

M10 实现已本地提交为 `33d096f`。下一唯一推荐任务为 M10.1 Live 纵向验收与适配器硬化：选择现有一个视频 Provider 和已存在数据源，使用任务级调用上限，不新增平台。`pytest-of-unknown/` 不删除、不提交。

## 阻塞

- M9.1 已本地提交；尚未 push，自动发布仍未实际触发。
- 全量宿主 UI 套件有多项与 M9.1 无关的既有失败；定向 M9.1 测试与 Node 22 build 已通过。
- 真实 provider/sidecar 依赖外部凭据/服务/确认。
- M10 的 DONE 还要求用户亲自验收一次新产品建脑和一次真实视频交付。
- `verify_m2_workflow_run.ps1` 本轮未完成；不得写成通过。

## 关键决策

- Product Creative 留在插件；Hermes core 只提供通用扩展面。
- 内层 `.hermes/plugins/product_creative` 是唯一源码真源；独立仓库仅由发布流程生成。
- enabled bundled/user Desktop plugin 是 v1 的受信任同源代码；project plugin 不可注入可执行页面/backend API。
- Product Brain 支持从空白开始；Hermes 应通过自然语言主动追问和索要证据逐步建脑，而不是用网页检索结果预填正式认知。
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

不清理脏工作区、不覆盖用户改动、不改业务/DB/API/样式、不升级依赖、不提交/推送；除非用户明确授权。
