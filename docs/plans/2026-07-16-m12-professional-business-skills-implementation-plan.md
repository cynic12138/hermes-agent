# M12 专业业务 Skills 与创意导演实施计划

> 本计划依据
> `docs/plans/2026-07-16-m12-professional-business-skills-design.md` 执行。
> 使用 TDD；每一阶段先证明测试失败，再写最小实现，再运行回归。

## 完成定义

M12 只有在以下全部成立时才标记完成：

- 八个专业业务 Skill 已注册、可加载、可校验。
- Skill execution 可追溯到所有 M12 专业工件。
- 来源专属研究、历史相似度、独立评审和卡审真正进入工作流。
- M11 固定三套剧情字典被 Skill 驱动实现替代。
- 自然语言离线 E2E 和 M0–M11 回归通过。
- 文档、Desktop 投影和长期状态同步。
- 保持未提交、未推送、未发布，除非用户另行授权。

## Task 1：业务 Skill 契约与 Catalog

### 测试

新增 `tests/hermes_cli/test_product_creative_m12_skills.py`：

- 八个 Skill 目录存在。
- frontmatter 可解析。
- 必需章节齐全。
- 输入/输出 Schema 已知。
- Tool allowlist 不越界。
- 同名重复和未知 stage fail closed。
- 插件注册八个业务 Skill 和 operator Skill。

### 实现

- 新增 `.hermes/plugins/product_creative/runtime/business_skills.py`。
- 新增八个 `skills/<name>/SKILL.md`。
- 修改插件 `__init__.py` 批量注册。
- 保留 `product-copy-pack` 作为兼容 Skill，但标记为 legacy composition
  helper，不作为 M12 Creative Director。

## Task 2：Skill Execution Artifact

### 测试

- 工件不可变且 content hash 可验证。
- 输入输出哈希和 Skill 版本被记录。
- 不允许记录密钥、Cookie 或完整敏感环境变量。
- workspace 隔离。
- 失败执行不能伪造成功输出。

### 实现

- 扩展 `contracts/creative_artifacts.py`。
- 扩展 `runtime/professional_artifacts.py` 的 collection 和读写。
- 增加 execution begin/complete/fail helper。

## Task 3：来源专属 Research Insight

### 测试

- Web 必须含时效/事件类洞察。
- XHS 必须含消费者语言/场景/情绪类洞察。
- Douyin 必须含前五秒/口播/节奏类洞察。
- Historical 必须含重复模式或失败经验。
- 外部来源保持 `not_product_fact=true`。
- 来源引用完整进入候选。

### 实现

- 扩展 ResearchInsightItem 契约。
- 改造 `ensure_research_insight_pack`。
- 复用现有 snapshot、transcript、copy_analysis 和 first5_analysis。
- 不重新抓取网络。

## Task 4：历史相似度

### 测试

- 与历史候选完全相同得到高相似度。
- 只有形容词变化仍被视为高相似。
- 结构、冲突和产品角色变化能降低相似度。
- 高相似但无具体差异触发 `NEEDS_REVISION`。

### 实现

- 新增轻量、确定性结构相似度。
- 读取同 product 的历史 Creative Candidate/Story。
- 在候选工件中保存分数、相似 artifact 和差异策略。
- 不引入向量数据库。

## Task 5：受控 Skill Runtime

### 测试

- 使用宿主 `PluginLlm.complete_structured`。
- 传入当前 Skill 正文、输入 Schema、输出 Schema 和允许工具。
- 结构错误不落专业工件。
- fixture executor 支持无网络离线 E2E。
- LLM 不可用时不回退成伪专业固定剧情。

### 实现

- 在 `business_skills.py` 增加可注入 executor。
- 插件注册时注入 `ctx.llm`。
- 每次执行写 Skill Execution Artifact。
- 不新增 Hermes 公共工具。

## Task 6：创意策略与独立评审

### 测试

- `creative-strategy` 生成 stable/variation/exploration。
- 三个候选在钩子、冲突、产品角色或表现机制上实质不同。
- 每个候选引用 Research/ Grounding/历史证据。
- `creative-review` 独立执行并输出三项评分。
- 硬规则失败覆盖 LLM 高分。
- preview-first 停在候选审阅。

### 实现

- 替换 `ensure_creative_candidates` 的固定中文候选。
- 替换静态 `direction_scores`。
- 保留确定性包装/合规/Schema Gate。
- 保持 M11 公共 artifact schema 兼容，必要字段只做向后兼容扩展。

## Task 7：编剧与分镜

### 测试

- Story Package 来自 `script-writer` 结构化输出。
- Production Bible 来自 `storyboard-director`。
- 用户指定“第 4 秒出现产品”反映到镜头边界。
- exact-main 路线保持 immutable product plate。
- 字幕仍由后期确定性渲染。
- 不存在 M11 固定三套 profile 字典。

### 实现

- 把固定 profile 替换为 Skill executor。
- 保留 `_requested_product_reveal_seconds` 等确定约束编译逻辑。
- Skill 负责创意内容；Capability 负责时长、素材、包装和 Provider 无关
  规格编译。

## Task 8：卡审与学习分析

### 测试

- 禁用表述触发确定性失败。
- 暗示性高风险表述由语义审查返回。
- LLM PASS 不能覆盖硬失败。
- 反馈被分类为当前修改、一次性、长期偏好、事实修正、渠道、生产经验、
  合规或样本不足。
- 未确认 proposal 不改变 Brain fingerprint。

### 实现

- 在 Preflight QA 中加入 `compliance-guard` execution。
- 现有 learning result evaluator 读取 `learning-analyst` Skill。
- 不修改 Product Brain 写回确认流程。

## Task 9：Desktop 投影

### 测试

- Tasks 显示当前 Skill 阶段。
- Review 显示 Skill/version/source/history similarity。
- Skill 加载失败显示诊断，不静默隐藏。
- workspace/locale 切换仍隔离并 cleanup。

### 实现

- 只扩展 plugin-owned `desktop_ui/index.js`。
- 不增加宿主 Product Creative 专属代码。

## Task 10：自然语言 E2E

### 离线 fixture

通过真实 Hermes agent loop 输入：

> 帮我做一条今天能发的周十五产品短视频，包装不能改，先给我看三个方向。

保存并断言：

- 原始用户消息。
- `product_workspace_resolve` 和 `product_workflow_run` 选择。
- 八个 Skill 的可加载状态。
- 本次实际执行的 Skill records。
- 来源专属研究。
- 三个候选及历史相似度。
- preview-first 停止位置。

继续输入：

> 选择 B，产品在第 4 秒左右出现。

断言：

- 创建新 revision，不覆盖初始工件。
- Script、Storyboard、Compliance Skill execution 完整。
- Production Bible 的产品首次出现时间为约 4 秒。
- 未调用 Provider。

## Task 11：回归与文档

### 验证

- M12 定向 Python 测试。
- M11 artifact/revision/public review 回归。
- M10 natural-language task 回归。
- M9 review/recovery。
- Desktop bundle/UI/typecheck/build。
- public-surface golden。
- `git diff --check`。
- 敏感信息扫描。

### 文档

- 新增 `docs/M12_PROFESSIONAL_BUSINESS_SKILLS_IMPLEMENTATION.md`。
- 更新 `AGENTS.md`、`PROJECT_STATE.md`、`ROADMAP.md`、
  `AI_HANDOFF.md`、`ARCHITECTURE_CURRENT.md`、`DECISION_LOG.md`。
- M13 设为完成 M12 后的唯一推荐任务。
