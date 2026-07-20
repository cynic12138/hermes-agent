# M13.1/M14.1 动态镜头生产与动作质量门禁设计

## 状态

- 日期：2026-07-17
- 用户决定：开始下一阶段开发
- Scope Gate：`IN_SCOPE`
- Redundancy Review：`EXTEND`
- 源码策略：方案 1，继续在 `.hermes/plugins/product_creative` 内开发
- Git：未提交、未推送、未发布
- Live Provider：Codex 租户策略阻塞；本阶段只做离线和隔离 Provider 验证

## 问题定义

当前 exact-main 样片虽然是 MP4，但每个镜头来自一张 Seedream 静态图片。compositor 使用
`-loop 1` 把图片延长到 2 秒，只执行缩放、裁切、字幕和 Product Plate 叠加。Production
Bible 中的眨眼、翻包、开门等动作没有时间维度的实现，因此文件可播放但不是合格动态视频。

当前 M14 freeze check 对高冻结比例只产生 WARN，没有把“计划要求动作、结果却是静态循环”
视为硬失败。系统缺少从动作要求到 Provider 路由、最终 QA 的贯通契约。

## 目标

建立最小、可恢复、包装安全的动态生产闭环：

```text
Production Bible action
→ MediaShotPlan 动态契约
→ Seedance 无产品动态背景
→ 原始 Product Plate 确定性受控合成
→ 计划时长裁切
→ 动态充分性 + 动作完成度 + 包装 + 连续性 QA
→ 只返修失败镜头
```

完成后，系统不得把静态图片循环描述为动态剧情视频。

## 非目标

- 不实现人物复杂手持、旋转、遮挡真实产品包装。
- 不新增 Provider、数据库、公共 Hermes Tool 或平行媒体任务。
- 不实现完整时间线编辑器、光流补帧或 3D 产品模型。
- 不让 XHS/Douyin 成为固定研究步骤。
- 不在本阶段调用真实豆包、DeepSeek、XHS 或 Douyin。

## 复用决策

继续复用：

- `ProductionBibleArtifact`
- `MediaShotPlan` / `MediaExecutionPlanArtifact`
- `volcengine-ark-video` 与现有异步 video task
- `MediaShotResultArtifact` 与 pending shot 恢复
- `ProductPlateArtifact`
- `media_compositor.render_shot`
- `media_technical_qa`、`story_continuity_qa`、`media_qa`
- Task Authorization、Receipt/Event 和局部 Repair Workflow

不创建 `DynamicVideoTask`、第二套 compositor 或第二套 QA 表。

## 动态镜头契约

`MediaShotPlan` 增加带默认值的兼容字段：

```python
motion_required: bool = False
motion_description: str = ""
maximum_freeze_ratio: float = 0.65
product_plate_motion: Literal["none", "static", "subtle_entrance"] = "none"
```

规则：

- 正式视频 Production Bible 中有非空 action 的镜头设为 `motion_required=True`。
- `motion_description` 直接来自已审阅的 Bible action，不由 Provider 自行发散。
- 无 Product Plate 的镜头使用 `none`。
- exact-main 产品镜头使用 `subtle_entrance`：只做统一缩放、平移和 alpha composite，
  不重绘、不非均匀变形、不修改包装文字。
- 旧 artifact 缺少字段时使用默认值，保持可读取。

## Provider 路由

- 视频交付默认选择 `volcengine-ark-video`，即使包装策略是 `exact-main-composite`。
- 视频 Provider 只生成背景、人物、动作、场景和装饰，不生成产品、品牌或字幕。
- Product Plate 继续由本地 compositor 添加。
- 图片 Provider 只用于图片交付，或用户明确接受“静态/轻动效降级”时的后续方案；本阶段
  不新增该用户开关。
- exact-main 视频授权需要视频调用预算；不再因为 exact-main 自动变成 image-only 授权。

## Seedance 时长适配

当前官方公开范围为 4–15 秒。Provider Registry 保存：

```json
{
  "min_duration_seconds": 4,
  "max_duration_seconds": 15
}
```

`MediaShotPlan.duration_seconds` 仍表示最终交付镜头时长。Provider payload 另存：

- `planned_duration_seconds`
- `provider_duration_seconds`
- `trim_to_seconds`

2 秒镜头请求 4 秒 Provider 视频，Prompt 明确要求目标动作在前 2 秒完成；compositor 下载后
裁切到 2 秒。Provider 时长不能静默改变最终故事节奏。

## Product Plate 动效

产品镜头前 0.30 秒执行小幅向上平移进入，随后固定在现有中心下方安全位置。中点抽帧时
Product Plate 已位于现有 packaging QA 的确定性几何位置，因此现有像素比对仍成立。

不做旋转、透视、手部遮挡或跟踪。若剧情要求人物手持并旋转产品，Readiness/Preflight
应进入人工审阅或要求真实拍摄/3D 素材，不能用平面 Plate 假装完成。

## 动态 QA

### 确定性动态充分性

复用 FFmpeg `freezedetect`：

- `motion_required=False`：高冻结比例保持 WARN。
- `motion_required=True` 且 freeze ratio 超过 `maximum_freeze_ratio`：FAIL/high，允许镜头级返修。
- image source + motion required 不因文件封装成 MP4而豁免。

### 语义动作完成度

VLM observation 增加：

- `observed_action`
- `action_completed`

`story_continuity_qa` 为每个 `motion_required` 镜头生成 action-fulfillment check：

- 无 visual adapter：UNKNOWN/high，进入 HUMAN_REVIEW。
- 置信度不足：UNKNOWN/high。
- `action_completed=false`：FAIL/high，镜头级返修。
- 完成：PASS。

确定性 freeze FAIL 不能被 VLM PASS 覆盖。

## 研究来源策略

默认研究顺序：

1. Product Brain / Creative Profile / Production Knowledge。
2. 本地素材和历史创意。
3. 普通 Web 搜索（任务需要新鲜题材时）。
4. Research Sufficiency 不足或用户明确要求平台专项时，才考虑 XHS/Douyin。

XHS 用于消费者语言、生活场景和内容审美；Douyin 用于前 5 秒、口播结构、节奏和镜头钩子。
两者失败不得阻塞普通创作，且永远是 `not_product_fact`。

## 验收

- exact-main 视频计划默认包含 `video_background`，不再生成 5 张静态图冒充动态视频。
- 2 秒镜头编译为 4 秒 Seedance 请求并在本地裁切为 2 秒。
- Product Plate 动效只使用允许的确定性变换，中点包装 QA 仍通过。
- motion-required 静态循环产生 FAIL，而不是 WARN/PASS。
- VLM 无法确认动作时进入 HUMAN_REVIEW。
- 真实异步 Provider fixture 能提交、等待、恢复、下载和合成，不重复调用。
- XHS/Douyin 不出现在普通创作的必需授权和硬阻塞中。
- M10–M14、Desktop、M9 recovery、public surface 与分发回归通过。

## 已知限制

- Codex 当前租户策略不允许真实外部调用，本阶段不能取得新的 QA PASS Live 成片。
- 每个 2 秒镜头生成 4 秒视频会增加 Provider 成本；后续可以设计多 beat clip 合并，但不在
  本阶段提前增加 clip graph。
- Prompt-only 或单参考图不能保证人物完全连续，M14 仍可能要求局部返修。
- 平面 Product Plate 不适合复杂手持交互。
