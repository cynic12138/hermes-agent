# M12 专业业务 Skills 与创意导演实施记录

## 1. 基线与状态

- 日期：2026-07-16
- 分支：`product-creative-rebaseline-20260716`
- HEAD：`0aa95637213f02eca2ef8f619daaf771150a7e11`
- 源码真源：`.hermes/plugins/product_creative/`
- 当前状态：`DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED`
- Git 状态：未提交、未推送、未 tag、未 release
- 方案：产品稳定前继续采用方案 1；独立
  `hermes-product-creative` 仓库仍只承接发布流程生成的分发物。

本文记录 M12 在当前 worktree 中的真实实现。未来恢复时不得只根据里程碑名称
推断功能，必须同时核对本文、当前代码、测试和 Git 状态。

## 2. 目标与非目标

M12 的目标不是再增加一个自由 Agent，而是把优秀运营人员和创意团队的工作方法
沉淀为版本化、可测试、可审计的业务 Skill，并让这些 Skill 驱动 M11 已建立的
专业工件链。

本阶段完成：

- 任务导演、研究导演、创意策略、独立评审、编剧、分镜导演、卡审和学习分析
  八个业务 Skill。
- 来源专属研究洞察。
- 稳定、变化、探索三个候选的受控生成。
- 独立创意评审、历史结构相似度和新颖性策略。
- Story、Production Bible 和 Preflight QA 的 Skill 驱动生成。
- Skill 执行的输入、输出、版本、哈希、允许工具和失败记录。
- Desktop 中的 Skill 执行与来源投影。

本阶段不完成：

- 不升级真实图片或视频 Provider。
- 不执行真实联网抓取、Cookie、付费模型或真实媒体生成。
- 不实现逐镜头媒体生产、后期合成升级和局部重试；这些属于 M13。
- 不实现生成后视频自动 QA 和返修；这些属于 M14。
- 不让 Agent 自动修改正式 Skill 文件。
- 不建立自由互聊的多 Agent 群。

## 3. 八个业务 Skill

| Skill | 职责 | 主要输出 |
|---|---|---|
| `task-director` | 把自然语言目标整理成可执行创作任务 | Creative Task Brief |
| `research-director` | 将 Web、XHS、Douyin 和历史素材变成来源专属洞察 | Research Insight Pack |
| `creative-strategy` | 生成 stable、variation、exploration 三个实质不同的方向 | Creative Candidates |
| `creative-review` | 独立评估候选，不复用策略阶段的自评 | Creative Decision |
| `script-writer` | 把选中方向发展成钩子、冲突、推进、结尾和文案 | Story/Copy Package |
| `storyboard-director` | 把 Story 转换为镜头、角色、场景、素材和连续性要求 | Production Bible 草案 |
| `compliance-guard` | 语义检查健康、合规、品牌和暗示性风险 | Semantic Compliance Review |
| `learning-analyst` | 对反馈分类，形成安全的当前修改或长期学习提案 | Learning Evaluation |

Skill 文件位于
`.hermes/plugins/product_creative/skills/<skill-name>/SKILL.md`，机器契约位于同目录
`contract.json`。`SKILL.md` frontmatter 只使用 Hermes 支持的 `name` 和
`description`；阶段、Schema、工具白名单和必需章节由 `contract.json` 与
Catalog 校验。

## 4. 运行时与信任边界

### 4.1 Catalog

`.hermes/plugins/product_creative/runtime/business_skills.py` 负责：

- 发现并校验八个 Skill。
- 拒绝重复名称、未知 stage、未知 Schema、未知工具和缺失章节。
- 将 Hermes `PluginLlm.complete_structured` 注入受控执行器。
- 为离线测试提供显式 fixture executor。
- 校验 Skill 输出必须是 JSON object。

生产环境没有可用 LLM executor 时采用 fail closed：任务不得回退为伪装成专业
创意的固定剧情。测试 fixture 必须显式注入，不能成为生产 fallback。

### 4.2 Skill 与确定性 Capability 的边界

Skill 负责需要专业判断的内容：

- 洞察提炼。
- 创意方向。
- 独立评审。
- 剧情、文案和镜头创意。
- 语义卡审和反馈分类。

Capability、Gate 和 Compiler 继续负责确定性约束：

- Schema 和哈希。
- 产品、workspace 和素材隔离。
- 包装保真路线。
- 用户指定的产品出现时间。
- 时长、比例和镜头边界。
- immutable product plate。
- 字幕必须后期确定性合成。
- 禁用表述和硬合规规则。
- Provider readiness、授权和真实调用开关。

LLM 的 PASS 不能覆盖确定性硬失败。

## 5. Skill Execution Artifact

`product_creative.skill_execution.v1` 记录：

- Skill 名称、版本和 stage。
- 输入与输出 artifact 引用及 content hash。
- 允许工具与实际动作。
- 执行模式、模型安全元数据和状态。
- 失败代码与诊断。

实现位于：

- `contracts/creative_artifacts.py`
- `runtime/professional_artifacts.py`

失败执行不能声明成功输出。敏感字段、凭据、Cookie、Token 和完整环境变量禁止
进入执行记录。

当前已知限制：executor 调用失败会留下失败执行记录；如果 executor 已返回内容，
但后续业务 Schema 校验失败，现阶段错误会阻断落正式工件，但并非所有此类错误都
拥有独立失败 execution artifact。该增强可在不改变公开契约的后续质量任务中完成。

## 6. 专业工件调用链

```mermaid
flowchart LR
  U["用户自然语言目标"] --> T["task-director"]
  T --> B["Creative Task Brief"]
  B --> R["research-director"]
  R --> RI["Research Insight Pack"]
  RI --> S["creative-strategy"]
  S --> C["Stable / Variation / Exploration"]
  C --> V["creative-review"]
  V --> D["Creative Decision"]
  D --> W["script-writer"]
  W --> SP["Story / Copy Package"]
  SP --> SD["storyboard-director"]
  SD --> PB["Production Bible"]
  PB --> CG["compliance-guard"]
  CG --> QA["Preflight QA"]
  QA --> G["Provider / Composer Gate"]
  G --> F["M13 媒体生产"]
  F --> L["learning-analyst"]
  L --> P["Learning Proposal / 当前修改"]
```

所有阶段继续复用 M11 的 artifact repository、Creative Task、Command Bus、
workflow/event/receipt、workspace 文件和恢复机制，没有新增平行任务数据库。

## 7. 来源专属研究

M12 不把所有来源压成同一种“摘要”：

- Web：日期、事件、趋势和可验证公开信息。
- XHS：标题语言、用户表达、情绪、生活场景和评论线索。
- Douyin：前 5 秒视觉钩子、口播钩子、节奏、冲突/反转、音频和 CTA。
- Historical：历史重复模式、结果、失败原因和可复用资产。

外部来源继续保持 `not_product_fact=true`。它们可以进入 inspiration、当前任务
和 learning proposal，但不能自动成为 Canonical Product Brain。

## 8. 创意策略、评审与历史相似度

`creative-strategy` 必须返回且只返回三种模式：

- `stable`：贴近已确认产品与渠道方法。
- `variation`：保留可用结构，但改变钩子、冲突、产品角色或表现机制。
- `exploration`：主动探索更远的题材和叙事方式。

历史相似度使用轻量确定性结构比较，不引入向量数据库。比较维度包括：

- hook
- conflict
- progression
- product role
- ending

每个候选保存相似分数、相似工件 ID 和 novelty strategy。高相似但没有具体差异
策略会触发 `NEEDS_REVISION`。

`creative-review` 是独立执行阶段。用户显式选择候选时保留用户决策；系统不能用
评审分数覆盖用户明确选择。

## 9. Story、Production Bible 与卡审

`script-writer` 负责创意内容；`storyboard-director` 负责镜头设计。随后确定性
Compiler 将结果收敛为 M12 第一条 10–30 秒产品短视频路线：

- 五镜头结构。
- 用户指定的产品首次出现时间。
- 任务时长和画幅。
- 包装不变时使用 immutable product plate。
- 中文产品文字和字幕不交给生成模型重绘。
- 关键素材角色、Provider mapping 和连续性规则。

Preflight QA 同时运行：

- Grounding、包装路线、素材和禁用表述硬规则。
- 历史相似度与新颖性 Gate。
- `compliance-guard` 语义审查。

硬规则失败始终优先于语义 PASS；语义风险可以要求创意修订。

## 10. 学习边界

`learning-analyst` 的版本化方法被现有结果评估服务读取。反馈仍进入原有安全流程：

1. 区分当前结果修改、一次性偏好、长期偏好、事实修正、渠道策略、制作经验、
   合规风险和样本不足。
2. 当前修改可以生成任务 revision。
3. 长期候选形成 proposal。
4. 未确认 proposal 不改变 Canonical Product Brain 指纹。
5. 确认后才创建新 Brain 版本、receipt 和 event。

M12 没有让 Skill 自动写 Product Brain，也没有让 Skill 自动修改自身代码。

## 11. Desktop 投影

现有 plugin-owned 五视图继续复用：

- Tasks：显示最新 Skill、执行列表、版本、模式和状态。
- Review：显示候选历史相似度、novelty strategy 和 Skill provenance。
- Overview/Assets/Learning：继续展示 readiness、素材、结果和反馈学习。

没有向 Hermes core 新增 Product Creative 专属路由或组件。

## 12. 测试边界

M12 测试分为：

- Catalog、契约、执行 artifact 和失败关闭单元测试。
- 来源专属研究、相似度、策略、评审、剧情、分镜和卡审测试。
- 真实 Hermes agent loop 的自然语言离线 E2E。
- M10/M11、M9 recovery、public surface 和 Desktop 回归。
- TypeScript typecheck、Desktop production build 和插件 bundle 测试。

离线 fixture 可以模拟专业 Skill 输出，但必须经过与生产相同的 Schema、artifact、
Gate 和持久化路径。它不能证明真实模型创意质量，也不能替代后续 M13/M14 的真实
媒体生产和媒体 QA。

本机 Desktop build 使用 Node `24.15.0` 作为补充证据；Node 22 仍是 CI 和发布
权威环境。

### 12.1 2026-07-16 最终结果

- M12 Skill Catalog/runtime/artifact：26/26 passed。
- M11/M12 专业工件、revision、Gate 和真实 Hermes 自然语言离线 E2E：
  34/34 passed。
- M10 自然语言任务兼容回归：35/35 passed。
- Desktop backend API、分发和 Live adapter 离线回归：25/25 passed。
- Desktop registry/page/distribution/Product Creative UI：14/14 passed。
- Desktop bundle 安全与身份：2/2 passed。
- M9 review/recovery：25/25 passed。
- Product Creative contract invariants：51 actions、84 tools、84 CLI，0 failure。
- Public surface golden：84 tools / 84 CLI，SHA-256 与基线一致。
- TypeScript typecheck：passed。
- Desktop production build：passed；只有 dirty build stamp、既有 CSS token、
  大 barrel 和大 chunk warning。
- `git diff --check`：exit 0；只有 Git 的 LF→CRLF 提示。
- 10 个必读/恢复文件：全部存在。
- 本次修改/新增的 53 个文件敏感字面量扫描：0 finding。
- Desktop plugin bundle SHA-256：
  `7770a636e5357306a15f5f5fe9a8ff04c22a1a8c82d1e120cfdcef418ab5ed3f`。

曾尝试的
`.hermes/plugins/product_creative/scripts/verify_contract_invariants.ps1`
并不存在；定位后使用仓库实际入口
`verify_product_creative_contracts.ps1` 补跑并通过。这是命令名纠正，不是代码失败。

未执行 Node 22 本地构建、真实联网、XHS/Douyin Cookie、真实图片/视频 Provider、
付费调用、Product Brain 写回、独立仓库导出安装、Git commit/push/tag/release。
Node 22 和 tracked-only 独立分发必须在提交后发布门禁中继续验证。

## 13. 修改文件分类

### Skill Catalog 与定义

- `.hermes/plugins/product_creative/runtime/business_skills.py`
- `.hermes/plugins/product_creative/skills/*/SKILL.md`
- `.hermes/plugins/product_creative/skills/*/contract.json`
- `.hermes/plugins/product_creative/__init__.py`

### 契约、持久化与编排

- `.hermes/plugins/product_creative/contracts/creative_artifacts.py`
- `.hermes/plugins/product_creative/contracts/__init__.py`
- `.hermes/plugins/product_creative/runtime/professional_artifacts.py`
- `.hermes/plugins/product_creative/runtime/creative_direction.py`
- `.hermes/plugins/product_creative/runtime/creative_tasks.py`
- `.hermes/plugins/product_creative/application/planner.py`

### Provider、视频与学习边界

- `.hermes/plugins/product_creative/provider_payloads.py`
- `.hermes/plugins/product_creative/provider_gateway.py`
- `.hermes/plugins/product_creative/provider_ports.py`
- `.hermes/plugins/product_creative/capabilities/video/exact_video_service.py`
- `.hermes/plugins/product_creative/capabilities/video/executor.py`
- `.hermes/plugins/product_creative/capabilities/learning/result_evaluation_service.py`

### Desktop 与查询

- `.hermes/plugins/product_creative/application/console_queries.py`
- `.hermes/plugins/product_creative/desktop_ui/index.js`
- `.hermes/plugins/product_creative/dashboard/dist/desktop.js`
- `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`

### 测试与文档

- `tests/hermes_cli/test_product_creative_m12_skills.py`
- `tests/hermes_cli/test_product_creative_m11_artifacts.py`
- `tests/hermes_cli/test_product_creative_m10.py`
- `docs/plans/2026-07-16-m12-professional-business-skills-design.md`
- `docs/plans/2026-07-16-m12-professional-business-skills-implementation-plan.md`
- 本文及长期状态文档。

完整工作区清单必须以 `git status --short` 和 `git diff --name-only` 为准，因为
当前 worktree 同时包含受保护的 M11 未提交改动。

## 14. 恢复顺序

工作区或本地 Codex 状态丢失后：

1. 读取 `AGENTS.md`。
2. 读取 `docs/PRODUCT_AGENT_DIRECTION.md`。
3. 读取 `docs/AI_HANDOFF.md`、`docs/PROJECT_STATE.md` 和
   `docs/ARCHITECTURE_CURRENT.md`。
4. 读取 M11 实施/审阅记录和本文。
5. 核对分支、HEAD、`git status --short` 和未跟踪文件。
6. 校验八个 Skill 的 SKILL.md/contract.json。
7. 运行 M12、M11 和 M10 Python 回归。
8. 重建 `dashboard/dist/desktop.js` 并校验 SHA-256。
9. 运行 Desktop bundle/UI、typecheck、build、M9 recovery 和 public surface。
10. 在没有独立授权时停止，不执行真实 Provider、联网抓取、Git 提交或发布。

## 15. M13 入口

M12 完成后唯一推荐任务是 M13“Production Bible 与可靠媒体生产”。M13 要把
当前高质量创意工件转换为逐镜头、可合成、可局部重试的真实媒体生产链，并重点解决：

- 产品 plate/抠图与生成背景的混合路线。
- 确定性中文字幕和品牌文字。
- 逐镜头 Provider 任务及异步恢复。
- 单镜头重试，避免整条重复费用。
- ffmpeg 和本机媒体依赖的发现、诊断与可复现性。

M13 不得绕过 M12 的 Skill execution、Production Bible 和 Preflight QA。
