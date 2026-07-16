# Product Creative 重建基线与清理记录

- 日期：2026-07-16
- 决策：方案 1——产品稳定前继续在 Hermes 仓库内开发插件，稳定后再拆分源码仓库
- 新分支：`product-creative-rebaseline-20260716`
- 基础 HEAD：`d7d6ec0bf5a4ae9a1bc2377db668ed07a8a87c0b`
- 新 worktree：`C:\data\work file\hermers-agent for me\hermes-agent-rebaseline`
- 原工作区：`C:\data\work file\hermers-agent for me\hermes-agent`
- 状态：`DONE_LOCAL`；已验证并本地提交，未 push、未 tag、未 release

## 1. 本次目标

本次不是重写 Product Creative，而是从可验证的 Git 基线中重建一个干净、可继续开发的工作区：

1. 完整保护原脏工作区、M0–M8 历史和真实运行数据。
2. 只迁移已被测试证明有效的 M10.1 Live Provider/数据源增量。
3. 把历史资料移出插件发行包，但保留 Git 历史和恢复索引。
4. 为“周十五益生菌蜂蜜露”建立不预填高风险事实的严格证据基线。
5. 让后续开发只围绕专业创意工作流与质量门禁推进。

## 2. 源码与仓库边界

当前采用方案 1：

```text
Hermes repository
└─ .hermes/plugins/product_creative/   唯一业务源码真源
   ├─ contracts / capabilities
   ├─ application / runtime
   ├─ provider adapters
   └─ desktop_ui

hermes-product-creative remote
└─ 发布流程生成的可安装分发物，不直接双向维护业务源码
```

选择理由：

- 当前 Product Creative 仍在快速调整契约、工作流和 Desktop 接口。
- 同仓开发可以直接运行 Hermes 自然语言 E2E 和宿主兼容回归。
- 立即拆仓会同时引入依赖边界、测试夹具、版本发布和双仓调试成本。
- 等公开契约、插件包依赖和发布节奏稳定后，再把独立仓库升级为源码真源。

拆分触发条件见 M11 计划：连续里程碑稳定、分发包不依赖仓库内隐式路径、Hermes 兼容矩阵自动化、数据/迁移边界明确。

## 3. 工作区保护

原 `product-creative-runtime` 工作区保持原样，没有执行 `reset`、`stash`、`checkout`、`clean` 或覆盖。它仍是未提交 Live 调用过程的现场证据。

恢复归档目录：

`C:\data\work file\hermers-agent for me\recovery-archives\20260716-163504`

| 文件 | SHA-256 |
|---|---|
| `product-creative-git-history.bundle` | `4631523291a8e41b0c7c5ece0fabda96aa046f1423ef53eecefd6165cde036f6` |
| `product-creative-legacy-runtime.zip` | `6c79df2b2be3b81c8f920023fd9813f1932af9c173a5991b17e458b8a9f50d41` |
| `product-creative-m0-m8-development-history.zip` | `4939168af43032ea6cf4d5890527e74cbf7a56123cfa547bbbe22e24fccbe4d2` |
| `product-creative-pcbak-20260711.zip` | `7e750d00403c801ac3693be747408ac205f10cecd77497219de3e47afcc2c35f` |
| `product-creative-runtime-worktree.patch` | `26d0dd3038728a2bc87ee65359e6078cf16bcfe074cee186a450717a92abd4f1` |

另外单独保存了未跟踪的 Live 文档、产品方向文档和 Live source 测试；其哈希记录于归档目录的 `SHA256SUMS.txt`。

## 4. 选择性迁移

迁移范围只包含：

- 豆包凭据优先级与 Windows 环境变量读取。
- 最新豆包 VLM、图片与 Seedance 视频 Provider 配置。
- XHS/Douyin 数据源适配器补强。
- Douyin SiliconFlow 转录、DeepSeek 钩子和豆包前 5 秒分析。
- Provider 异步恢复、签名 URL 脱敏、任务结果绑定。
- exact-main 路由和包装安全提示。
- 对应 M10 与 Live source 测试。

没有迁入：

- 旧 workspace 数据库和 artifact。
- 临时日志、缓存或 pytest 目录。
- 失败样片作为成功学习。
- 未经测试的平行模块。
- 任何 API key、Cookie、token 或签名下载 URL。

### TDD 证据

先迁入测试，RED 结果：

- M10：13 failed / 22 passed。
- Live sources：10 failed。

再迁入最小实现，GREEN 结果：

- M10：35 passed。
- Live sources：10 passed。
- Public surface：84 tools / 84 CLI，golden hash 匹配。

这证明新分支中的 Live 增量不是从脏工作区整包复制，而是由明确失败测试驱动的选择性迁移。

## 5. M0–M8 历史保留与活跃树清理

共 13 份旧插件文档和 46 个 `verify_m0`–`verify_m8` 脚本通过 `git mv` 移至：

`docs/history/product-creative-legacy/original/`

效果：

- 历史开发过程可追溯。
- 文件级 Git 历史保留。
- 插件发行包不再包含大量失效阶段资料。
- 当前开发者不会把旧脚本误当现行门禁。

详细索引见 `docs/history/product-creative-legacy/README.md`。

## 6. 周十五严格产品基线

全新隔离 workspace：

`C:\data\work file\hermers-agent for me\product-creative-clean-workspace`

导入内容：

- 用户原始描述作为 Evidence/Draft。
- 两张用户提供图片登记为 `product_photo`。
- 高风险宣称形成待确认 proposal。

没有导入 Canonical Product Brain：

- “快速有效通便”。
- “温和不刺激”。
- “安全有效”。
- 孕妇适用。
- 治疗便秘。
- 未核验成分、使用方式和健康效果。

当前 Readiness 被 SKU/版本和合规边界阻断；两张图片尚未自动选为 `current_main_image`。严格字段矩阵见 `docs/product-bases/zhou-shiwu-honeydew/STRICT_BASELINE.md`。

## 7. 运行环境

本次没有下载依赖或访问网络。新 worktree 通过被 Git 忽略的本地 junction 复用原仓库现有 `.venv`、根 `node_modules` 和 Desktop `node_modules`；这些 junction 不进入提交和分发。

仓库的 `scripts/run_tests.sh` 是 POSIX 入口并假设 `.venv/bin/python`。Windows 验证使用同一虚拟环境中的 `.venv\Scripts\python.exe` 和独立 `--basetemp`，避免系统 temp ACL 影响。此差异是平台包装问题，不改变测试内容。

## 8. 恢复顺序

如果本地 Codex 或工作区再次丢失：

1. 克隆/打开 Hermes 仓库并读取 `AGENTS.md`。
2. 读取本文件、`PRODUCT_AGENT_DIRECTION.md`、`PROJECT_STATE.md` 和 `AI_HANDOFF.md`。
3. 运行 `git status`、`git branch --show-current`、`git rev-parse HEAD`。
4. 校验恢复归档 `SHA256SUMS.txt`。
5. 如 Git 历史缺失，从 `product-creative-git-history.bundle` 创建临时仓库。
6. 如需核查旧现场，在临时目录解压 runtime/pcbak；不得覆盖当前 workspace。
7. 运行当前定向门禁，不直接运行 M0–M8 历史脚本。
8. 按 `docs/plans/2026-07-16-m11-professional-creative-workflow-plan.md` 接续开发。

## 9. 已知限制

- 原工作区仍然脏，这是有意保留的取证现场，不是新开发基线。
- M10.1 证明真实外部链路可用，但两条真实样片未通过创意质量验收。
- XHS/Douyin 依赖独立 sidecar、登录状态、平台风控和网络。
- exact-main 当前依赖本机 ffmpeg，插件级依赖诊断尚未完成。
- 方案 1 会让当前 Hermes 仓库继续承担插件源码；未来拆仓仍需专门迁移里程碑。

## 10. 最终验证结果

所有真实外部能力均显式关闭，本节没有访问网络、Cookie、真实 Provider 或生产 workspace。

| 验证 | 结果 |
|---|---|
| M10 自然语言/任务测试 | 35 passed |
| Live source/provider adapter 测试 | 10 passed |
| Desktop plugin backend API + distribution | 15 passed |
| Desktop bundle 契约 | 2 passed |
| Desktop routes/registry/page/Product Creative/distribution bundle | 17 passed + distribution 单测 1 passed |
| M9 review/recovery | 25/25 |
| Product Brain boundary | 0 failures |
| Contract invariants | 51 actions；84 tools；84 CLI；0 failures |
| Public surface golden | 84/84；SHA-256 匹配 |
| TypeScript typecheck | passed |
| Desktop production build | passed |
| 分发 validate + enabled user-plugin 离线安装 | passed |
| 分发内容 | 260 files；无 SQLite/runtime workspace；无 M0–M8 脚本；无 `docs/` |
| 版本 | `plugin.yaml`、dashboard manifest/API、README、workflow、SOURCE 均为 `9.1.0-alpha.1` |
| 敏感值扫描 | 0 hits |
| `git diff --check` | exit 0；只有 Windows LF→CRLF 提示 |

本机可用 Node 为 `24.15.0`，因此 typecheck/build 是 Node 24 补充证据；发布 workflow 的 Node 22 仍是正式发布权威环境，本次没有为取得 Node 22 而联网下载依赖。

宿主全量 `test:ui` 仍有多个与 Product Creative 无关的既有失败，包括 pane、preview、assistant UI、settings 等。M9.1 发布 workflow 使用的五个定向测试文件全部通过；本次没有顺带修改宿主失败。

首次尝试导出到 `C:\tmp` 因本机目录 ACL 被拒绝，尚未进入构建逻辑；随后在项目根目录之外且可写的 `C:\data\work file\hermers-agent for me\test-temp\product-creative-rebaseline-dist` 原样通过。

严格 workspace 独立核验：

- Canonical product name：`周十五益生菌蜂蜜露`。
- Canonical selling points：0。
- 高风险表述命中：0。
- 已登记素材：2。
- 合规 proposal：`proposed`。
- Readiness：false；仅由宣称边界与 SKU/包装版本阻断。

本地提交：

- `855da56`：Live Provider、外部数据源、恢复行为与测试。
- 重建知识、M0–M8 历史归档、严格产品基线和 M11 计划：本文件所在的后续提交。
