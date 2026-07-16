# M7 Self-Iteration Evaluation Architecture

## 1. 主线定位

M7 的目标不是继续扩展模型 provider、平台抓取或 UI，而是补齐“真实生成结果如何让系统更懂当前产品”的闭环。

当前产品主线：

1. Product Brain 保存当前产品认知。
2. 素材库保存本地/外部/生成素材及其文字化理解。
3. 文案、图片 brief、视频 brief 从 Product Brain 和素材库生成。
4. 外部模型执行真实图片/视频生成。
5. 用户审阅真实结果。
6. 系统基于审阅结果生成可解释学习建议。
7. 人工确认后才写回 Product Brain，影响下一轮生成。

M7 负责第 5-7 步。

## 2. 关键原则

- 真实结果不自动改 Product Brain。
- 用户反馈不直接改 Product Brain。
- LLM 评估只生成 `review_required` 的候选学习。
- 写回必须经过 `product_evolve --apply` 或 Hermes 对话里的显式确认。
- 原始证据和生成上下文分离：`generation_safe` 用于生成，raw/wiki/source 继续保留追溯。
- 外部灵感、URL、文件名、搜索摘要不能被当成产品事实。

## 3. M7.0-M7.9 范围

### M7.0 Architecture Lock

固定本阶段边界：

- 不新增搜索渠道。
- 不新增模型 provider。
- 不做 UI。
- 聚焦结果评估、反馈、学习沉淀。

### M7.1 Generation-Safe Context

新增 `generation_safe`：

- 从 Product State 中抽取干净的产品名、brief、卖点和确认学习。
- 过滤 URL、来源、文件路径、时间戳、测试描述等非产品事实。
- `generator`、`video_briefing`、`context_pack` 优先读取安全上下文。

### M7.2 Result Review Package

新增 `product_result_review_package`：

- 针对真实图片/视频结果生成可读审阅包。
- 展示产品上下文、结果文件、source prompt、审阅 checklist。
- 不调用外部模型，不写 Product Brain。

### M7.3 Structured Result Feedback

增强 `product_result_feedback`：

- 支持喜欢原因、问题、反感原因。
- 支持图像维度：主体清晰、产品识别、构图、风格、文案、包装一致性、事实性。
- 支持视频维度：运动质量、场景适配、首帧一致性、事实性。
- 反馈仍只入库，不直接写脑。

### M7.4 Result Evaluation

新增 `product_result_evaluate`：

- Hermes runtime 内可使用当前 LLM 评估真实结果和用户反馈。
- CLI/离线环境使用规则 fallback。
- 输出 `result_evaluation`，状态为 `review_required`。

### M7.5 Proposal Integration

`product_evolve` 在基于 result feedback 生成 proposal 时，会读取最近的 `result_evaluation`：

- evaluation 的 proposed_updates 进入 proposal。
- proposal 仍需人工确认。
- apply 后才进入 Product Brain。

### M7.6 Next-Run Learning

apply proposal 后：

- 图片规律进入 `learning.image_generation_preferences`。
- 视频规律进入 `learning.video_script_preferences`。
- 成功规律进入 `learning.successful_patterns`。
- 失败规律进入 `learning.failed_patterns`。

下一轮图片 brief、视频 brief、copy/channel generation 会读取这些学习。

### M7.7 Hermes Conversational Readiness

新增 Agent tool：

- `product_result_review_package`
- `product_result_evaluate`

并加入 workflow action：

- `review_generated_result`
- `evaluate_generated_result`

这样 Hermes 中枢 AI 可以在对话里审结果、评结果，而不是只能脚本触发。

### M7.8 Closeout Checks

验证：

- Python 编译通过。
- 结果评审包可生成。
- 反馈可记录。
- evaluation 可生成。
- evolve proposal 可吸收 evaluation。
- apply 后 Product State 出现新学习。
- 下一轮生成读取新学习。

### M7.9 Full Validation Output

用已有或测试产品跑完整结果自迭代链路，并输出：

- review package JSON/Markdown。
- result feedback JSON/Markdown。
- result evaluation JSON/Markdown。
- evolution proposal JSON。
- apply 后 Product State。
- 下一轮生成产物。

## 4. 用户体验目标

用户不应该理解脚本细节。目标对话形态：

```text
用户：这张图主体清楚，但是包装和真实产品不像，视频节奏也太平。
Hermes：
1. 找到最近生成的图片/视频结果。
2. 生成审阅包。
3. 记录你的反馈。
4. 总结可学习规律。
5. 生成 Product Brain 更新建议。
6. 请求你确认是否写回。
```

用户确认后，下一轮可说：

```text
用户：按刚刚确认的方向再生成一版图和视频脚本。
```

系统应自动读取已确认偏好，而不是让用户重复描述。

## 5. 验收标准

M7 完成时，系统必须证明：

- 它没有把测试产品固定成中心锚点。
- 它能从任意产品的真实结果反馈中产生学习建议。
- 它能解释为什么建议写入 Product Brain。
- 它不会绕过人工确认直接自改。
- 它能让下一轮图/视频生成读取上一轮确认学习。

## 6. M7.0-M7.9 实现记录

状态：M7.0-M7.9 已落地并通过验证。

实现内容：

- 新增 `context_safety.py`，提供 `generation_safe`。
- `store.context_pack`、`generator`、`video_briefing` 已优先使用安全生成上下文。
- 新增 `self_iteration.py`。
- 新增 CLI：
  - `result-review-package`
  - `result-evaluate`
- 新增 Hermes tools：
  - `product_result_review_package`
  - `product_result_evaluate`
- 新增 workflow actions：
  - `review_generated_result`
  - `evaluate_generated_result`
- `product_result_feedback` 支持图/视频结果的细粒度反馈字段。
- `product_evolve` 会吸收最近的 `result_evaluation`，但仍只生成 proposal。
- `product_evolve --apply` 后才写入 Product Brain。

验证结果：

```text
verify_m7_self_iteration_loop: passed
script: .hermes/plugins/product_creative/scripts/verify_m7_self_iteration_loop.ps1
product: m7-self-iteration-test
result_review_package: result-review-package-20260709-115459
result_feedback: result-feedback-20260709-115500
result_evaluation: result-evaluation-20260709-115533
proposal: proposal-20260709-115535
applied_updates: 5

verify_m7_7_hermes_entry: passed
script: .hermes/plugins/product_creative/scripts/verify_m7_7_hermes_result_iteration_entry.ps1 -RunChat -MaxTurns 4
chat_session_id: 20260709_121241_ab94ca
chat_generated_review_package: result-review-package-20260709-121248

verify_m7_9_full_validation: passed
script: .hermes/plugins/product_creative/scripts/verify_m7_9_full_validation.ps1
product: jindouya-jinyinhuayouzi-20260709-demo
image_result: image-result-20260709-105000
image_review_package: result-review-package-20260709-121308
image_evaluation: result-evaluation-20260709-121348
image_proposal: proposal-20260709-121350
video_result: video-result-20260709-111028
video_review_package: result-review-package-20260709-121352
video_evaluation: result-evaluation-20260709-121430
video_proposal: proposal-20260709-121431
validation_report: artifacts/m7_validation/m7-full-validation-20260709-121532.md
external_image_or_video_call_performed: false
```

M7 closeout：

```text
M7_status: closed for current architecture
M8_entry: product UI / Desktop conversation packaging can start after confirming whether current Hermes chat flow is sufficient for user-facing review.
```
