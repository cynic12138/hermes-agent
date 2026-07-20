# Open Questions

## P0

### RESOLVED 2026-07-20：M15 干净机器应如何取得当前 runtime？

- 决议：用户选择方案 A；实现提交 `25e26df` 已推送到 `origin/product-creative-rebaseline-20260716`。
- 剩余：重建 install stamp、执行隔离 fresh-install 和运营人员人工全链。

### RESOLVED 2026-07-20：是否授权 push 重建基线与既有本地提交？

- 为什么：M9.1、M10 和本次重建基线均只在本地 Git/归档中保存，尚未同步到远端。
- 决议：用户授权只推送 pilot 分支；不合并 main、不 tag、不 release。已执行。

## P1

### 哪些 provider/sidecar 是正式支持项？

- 影响：验收、文档承诺、凭据/风控/费用支持。
- 推断：默认 mock/offline；real/sidecar opt-in；置信度高。
- 推荐：逐项标记 supported/experimental/dev-only。

### 历史 workspace 的迁移与保留策略？

- 影响：数据丢失、备份、兼容期、隐私。
- 推断：应无损迁移并保留审计备份；完成度 UNKNOWN。
- 推荐：先只读 inventory + backup/restore drill。

### M11 的首个专业工作流应先覆盖哪一种视频？

- 为什么：剧情短视频、纯产品展示、UGC 口播和动画故事需要不同的 Skill、Production Bible 和 QA。
- 不确认的影响：如果第一版同时覆盖所有类型，会稀释质量门禁并增加测试矩阵。
- 当前推断：先以“周十五产品剧情短视频”为纵向验收，底层契约保持通用；置信度高。
- 推荐：M11 只完成一种完整剧情视频工作流，再用同一契约扩展其他类型。

### 内部试用阶段的可发布质量标准由谁最终签字？

- 为什么：系统需要统一的通过/修改/拒绝标准，不能只学习不同运营人员的个人审美。
- 不确认的影响：Creative Profile 和 QA Rubric 可能出现互相冲突的反馈。
- 当前推断：需要一位产品/内容负责人作为最终规则确认人，普通运营反馈作为证据；置信度中。
- 推荐：在首次 M15 可复现 Desktop 人工试用前确定负责人和最小质量 Rubric。

## P2

- Windows M15 继续复用现有 Hermes Desktop Electron/NSIS 薄安装架构，但当前尚缺可获取 runtime ref/bootstrap；是否在产品稳定后制作独立品牌、预捆绑媒体工具和默认 Product Creative 的 fat installer，留到内部试用证据充分后决策。
- 是否需要 Web UI、多人/云/平台发布？推断：Final 1.0 后另行评估，置信度高。
- 性能、可用性、保留、恢复时间等 NFR 目标是什么？当前 UNKNOWN。
