# MVP Scope

> 当前 MVP 依据 `docs/PRODUCT_AGENT_DIRECTION.md` 重新定标。M0–M10 已提供技术底座，但真实样片证明“链路可运行”不等于“创作可用”。

## 当前目标

完成 M11“专业创意工作流与质量门禁”：用户用自然语言提出产品内容目标后，系统必须形成可追溯的 Product Grounding、研究洞察、素材选择、创意候选、创意决策、剧情/分镜和 Production Bible；缺少关键产物时禁止调用真实图片/视频 Provider。

## 必须完成

- 保留 Evidence Inbox、Draft Understanding、Canonical Product Brain 和 Task Context 隔离。
- Product Brain 继续提供产品事实、包装、合规和长期偏好，但不承担全部创意判断。
- 新增或固化 Creative Task Brief、Creative Candidates、Creative Decision、Production Bible 和 QA Report。
- Goal Planner 按阶段产物和 Gate 推进，不再只按静态动作列表推进。
- `selected_idea` 为空、剧情没有钩子/推进/结尾、包装路线冲突或卡审失败时阻断生成。
- 灵感来源必须能追溯到 Web/XHS/Douyin/历史素材，并保持 `not_product_fact`。
- 停止把固定主图、通用字幕和装饰动画标记为合格剧情视频。
- 真实生成前保持任务级授权和 real-provider 双重 opt-in。
- 结果进入 QA 和人工通过/修改/拒绝；未反馈不得自动记为成功经验。
- 通过真实 Hermes chat/agent loop 的自然语言离线 E2E，不以底层函数或参数化脚本作为主验收。
- 不泄露密钥、Cookie、产品 DB、workspace artifact 或个人数据。

## 可选

- 在不产生费用的情况下对现有 Web/XHS/Douyin fixture 做研究产物回归。
- 在用户单独授权后，用现有豆包 Provider 做一次小调用上限的质量验证。

## 不做

- 新 Provider、新抓取平台、向量库或消息队列。
- 完整多 Agent 群、Theme Brain 或大型可视化创作画布。
- GEO、自动发布、自动投流、自动效果分析和矩阵生产。
- 多人/租户/权限/计费或云 SLA。
- 未经确认的 Brain、合规、品牌或正式 Skill 写回。

## 完成后的下一阶段

M12 专业业务 Skills 与创意导演：任务导演、研究、创意策略、独立评审、编剧、分镜、卡审和学习分析。

## 新需求准入

必须直接提升 Product Grounding、Creative Director、Production Engine 或 Evaluator & Learning，并复用现有 capability、Command Bus、durable runtime、repository、provider 和 Desktop SDK。新增平行 Agent、存储、接口或 UI 必须先证明现有边界无法扩展。

修改前使用项目级 `scope-gate` 与 `redundancy-review`；`NEEDS_APPROVAL` 等待用户，`OUT_OF_SCOPE` 写入 `docs/PARKING_LOT.md`。
