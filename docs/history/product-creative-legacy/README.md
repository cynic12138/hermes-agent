# Product Creative M0–M8 历史开发索引

- 归档日期：2026-07-16
- 基线提交：`d7d6ec0bf5a4ae9a1bc2377db668ed07a8a87c0b`
- 用途：保存 M0–M8 的开发过程、架构演变和历史验证脚本
- 状态：`HISTORICAL_EVIDENCE`

本目录用于回顾项目如何从 Product Brain 原型逐步形成素材、图片、视频、灵感、学习和恢复能力。它不是当前运行手册，也不代表其中每项未来设想仍然有效。当前产品方向、架构和状态分别以 `docs/PRODUCT_AGENT_DIRECTION.md`、`docs/ARCHITECTURE_CURRENT.md` 和 `docs/PROJECT_STATE.md` 为准。

## 为什么移出插件分发目录

历史文档和阶段性 PowerShell 验证脚本原来位于 `.hermes/plugins/product_creative/docs/` 与 `.hermes/plugins/product_creative/scripts/`。它们对恢复开发过程很重要，但不应随每个插件发行包一起安装，也不应被误认为当前发布门禁。

本次使用 `git mv` 移动文件，保留文件级 Git 历史：

- 原始文档：`original/plugin-docs/`
- 原始验证脚本：`original/verification-scripts/`

历史文档中的旧路径按原文保留，目的是维持证据原貌；执行时必须改用本目录下的新路径，并先确认脚本不会修改 workspace、调用外部 API 或产生费用。

## 里程碑索引

| 阶段 | 当时主要目标 | 代表证据 |
|---|---|---|
| M0 | 插件骨架、产品 workspace、内容与 Provider 基础能力 | `M0_2_5_RUNBOOK.md`、`verify_m0_*` |
| M1 | Canonical Product Brain 与写入边界加固 | `verify_m1_canonical_brain.ps1`、`verify_m1_hardening.ps1` |
| M2 | 渠道、对话、workflow、视觉理解与视频 brief | `PRODUCT_CREATIVE_CONVERSATION_PROTOCOL.md`、`verify_m2_*` |
| M3 | 素材登记、分析、检索与任务素材包 | `M3_ASSET_RETRIEVAL_ARCHITECTURE.md`、`verify_m3_*` |
| M4 | 图片生成产品化与 Hermes 对话入口 | `M4_IMAGE_GENERATION_PRODUCTIZATION_ARCHITECTURE.md`、`verify_m4_*` |
| M5 | 视频生成、异步 Provider 和执行闭环 | `M5_VIDEO_GENERATION_EXECUTION_ARCHITECTURE.md`、`verify_m5_*` |
| M6 | 外部灵感、XHS/Douyin sidecar、素材托管 | `M6_ASSET_HOSTING_AND_EXTERNAL_INSPIRATION_ARCHITECTURE.md`、`verify_m6_*` |
| M7 | 结果审阅、反馈、学习提案与自我迭代 | `M7_SELF_ITERATION_EVALUATION_ARCHITECTURE.md`、`verify_m7_*` |
| M8 | 产品审阅与 exact-main 包装保真视频路线 | `M8_PRODUCT_REVIEW_AND_EXACT_VIDEO_ARCHITECTURE.md`、`verify_m8_*` |

## 事实使用规则

1. 脚本存在只证明当时设计过或验证过某条路径，不证明当前仍投入使用。
2. 示例产品、示例卖点和示例文案均不得写入真实 Product Brain。
3. “通过历史脚本”不等于当前架构通过；当前代码必须运行当前门禁。
4. 与当前代码冲突时，先查 Git diff、现行测试和状态文档，再记录为 `CONFLICTED`。
5. M0–M8 不是需要重新逐阶段开发的待办，而是现有能力的历史来源。

## 外部恢复包

完整恢复材料保存在项目目录外的：

`C:\data\work file\hermers-agent for me\recovery-archives\20260716-163504`

关键文件：

- `product-creative-git-history.bundle`：可恢复相关 Git 提交与 tag。
- `product-creative-m0-m8-development-history.zip`：M0–M8 文档与脚本独立快照。
- `product-creative-legacy-runtime.zip`：旧运行 workspace 的一致性备份。
- `product-creative-pcbak-20260711.zip`：早期项目副本归档。
- `product-creative-runtime-worktree.patch`：原脏工作区 tracked 修改。
- `SHA256SUMS.txt`：权威完整性校验。

恢复前先校验 SHA-256；不要直接覆盖当前 workspace。优先在新的临时目录或 Git worktree 中恢复并比较。
