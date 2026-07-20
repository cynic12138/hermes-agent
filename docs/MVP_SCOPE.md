# MVP Scope

> 当前 MVP 依据 `docs/PRODUCT_AGENT_DIRECTION.md` 重新定标。M13.1/M14.1 本地实现已达到
> `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED_LIVE_GATE_AND_USER_ACCEPTANCE_PENDING`。

## 当前目标

完成动态 M13.1/M14.1 联合真实 Live Gate 与用户验收：证明真实逐镜头动态 Provider 结果可以进入
可审计 QA、只返修失败镜头，并由用户确认至少一条 PASS 和一条自动返修案例。

## 必须完成

- 保留 Evidence Inbox、Draft Understanding、Canonical Product Brain 和 Task Context 隔离。
- Product Brain 继续提供产品事实、包装、合规和长期偏好，但不承担全部创意判断。
- M12 Skill Execution、Creative Decision、Story、Production Bible 和 Preflight QA 是真实生产硬前置，不建第二套创意系统。
- 复用 M13 Production Bible、Media Execution Plan、Product Plate、Shot Results 和
  Composite Manifest，不建第二套媒体任务。
- 已实现对关键包装区域的 OCR/视觉基线比对；不能证明包装保真时不得标记可发布。
- 已实现人物、场景、镜头连续性、字幕可读性、音画、时长、编码和文件完整性检查。
- 已形成版本化 QA Report、Repair Decision 与 Human Override，明确通过、返修、人工
  审阅或最终失败。
- 已实现返修只重做失败镜头，成功镜头和已付费调用不得重复。
- 用户的通过/修改/拒绝及原因进入现有 learning proposal；未经确认不写 Canonical Brain。
- M13 真实豆包/Seedance Live Gate 保持独立授权，不用 fixture 冒充。
- exact-main 视频的 Seedance 只生成无产品的动态场景/人物/动作，产品 plate 与字幕由
  本地确定性合成；动作不足或高冻结比例必须进入 shot-scoped repair。
- 普通 Web 是默认实时来源；XHS/Douyin 是按需可选来源，不进入每条创作的硬依赖。
- 真实生成前保持任务级授权和 real-provider 双重 opt-in。
- 已通过真实 Hermes chat/agent loop 的自然语言离线 E2E 和隔离 Provider fixture；
  Live Gate 仍必须走同一公开入口，不以底层函数或参数化脚本作为主验收。
- 使用真实豆包 VLM/OCR 和 Seedance 时保持调用次数、异步等待、结果下载和恢复可审计。
- 用户亲自验收一条 QA PASS 和一条自动返修案例。
- 不泄露密钥、Cookie、产品 DB、workspace artifact 或个人数据。

## 可选

- 在不产生费用的情况下对现有 Web/XHS/Douyin fixture 做研究产物回归。
- 在用户单独授权后，用现有豆包 Provider 做一次受控的 M13 Live + M14 QA 验证。

## 不做

- 新 Provider、新抓取平台、向量库或消息队列。
- 完整多 Agent 群、Theme Brain 或大型可视化创作画布。
- GEO、自动发布、自动投流、自动效果分析和矩阵生产。
- 多人/租户/权限/计费或云 SLA。
- 未经确认的 Brain、合规、品牌或正式 Skill 写回。

## 完成后的下一阶段

Live Gate 与用户验收完成后进入 M15 Desktop 内部试用版：让非技术运营人员无需
CLI/Prompt 完成产品 onboarding、创意审阅、生产、QA、返修和反馈。

## 新需求准入

必须直接提升 Product Grounding、Creative Director、Production Engine 或 Evaluator & Learning，并复用现有 capability、Command Bus、durable runtime、repository、provider 和 Desktop SDK。新增平行 Agent、存储、接口或 UI 必须先证明现有边界无法扩展。

修改前使用项目级 `scope-gate` 与 `redundancy-review`；`NEEDS_APPROVAL` 等待用户，`OUT_OF_SCOPE` 写入 `docs/PARKING_LOT.md`。
