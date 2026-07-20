# M13 Reliable Media Production Implementation Plan

> **执行方式：** 当前会话内联执行，禁止子智能体。每项任务使用 TDD。
> 用户未授权 Git commit/push/tag/release，因此每个阶段只记录 diff 和测试 checkpoint。
>
> **实施结果（2026-07-16）：**
> `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED_LIVE_GATE_PENDING`。下方 checkbox 保留为
> 原始实施规格，不再作为实时状态；实际文件、偏差、验证结果和恢复顺序以
> `docs/M13_RELIABLE_MEDIA_PRODUCTION_IMPLEMENTATION.md` 为准。

**Goal:** 将 M12 Production Bible 转换为逐镜头、包装保真、确定性字幕、可局部重试和可恢复的真实本地 MP4 生产链。

**Architecture:** 扩展现有 `compose_exact_main_video` 兼容入口，引入内部混合 Shot Graph。Provider 只负责背景/场景/人物媒体；产品 plate、字幕、镜头标准化、拼接和最终输出由本地确定性 Production Engine 完成。

**Tech Stack:** Python 3.11–3.13、Pydantic、Pillow、ffmpeg/ffprobe、现有 artifact repository、Creative Task、Generation Provider Gateway、Electron plugin UI。

## Global Constraints

- `.hermes/plugins/product_creative/` 继续是唯一源码真源。
- 不新增第二套聊天工具、任务数据库或 Provider 网关。
- 不修改 Canonical Product Brain。
- 产品 plate 只允许原始像素复制、alpha mask、等比缩放和平移。
- 中文字幕和品牌文字只允许确定性后期渲染。
- 真实 Provider 必须同时满足 task authorization 与
  `PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1`。
- `DOUBAO_API_KEY` 是豆包 Provider 最高优先级。
- 最大真实图片调用和视频调用分别为 5。
- 不删除 `.test-tmp/`，不提交、不推送。

---

## Task 1：M13 媒体工件契约

**Files:**

- Modify: `.hermes/plugins/product_creative/contracts/creative_artifacts.py`
- Modify: `.hermes/plugins/product_creative/runtime/professional_artifacts.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**

- Produces:
  - `MediaDependencyReportArtifact`
  - `ProductPlateArtifact`
  - `MediaExecutionPlanArtifact`
  - `MediaShotResultArtifact`
  - `MediaCompositeManifestArtifact`

- [ ] 写失败测试：五类 schema 可注册、hash 可验证、extra field 拒绝、workspace
  串库拒绝、失败 shot 不允许声明成功输出。
- [ ] 运行：
  `python scripts/run_tests_parallel.py tests/hermes_cli/test_product_creative_m13_media_production.py -j 1 -q`
  预期：模型未定义或 schema registry 未注册。
- [ ] 在 `creative_artifacts.py` 增加：

```python
class MediaDependencyCheck(BaseModel):
    name: NonEmptyStr
    status: Literal["READY", "DEGRADED", "BLOCKED"]
    detail: NonEmptyStr
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MediaDependencyReportArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_dependency_report.v1"]
    overall_status: Literal["READY", "DEGRADED", "BLOCKED"]
    checks: List[MediaDependencyCheck]
    blockers: List[NonEmptyStr] = Field(default_factory=list)
    warnings: List[NonEmptyStr] = Field(default_factory=list)

class ProductPlateArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.product_plate.v1"]
    source_material_id: NonEmptyStr
    source_content_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    plate_relative_path: NonEmptyStr
    plate_content_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    mask_mode: Literal["source_alpha", "edge_connected_background", "full_rect"]
    source_size: List[int]
    plate_size: List[int]
    allowed_transforms: List[NonEmptyStr]
    forbidden_transforms: List[NonEmptyStr]

class MediaShotPlan(BaseModel):
    shot_id: NonEmptyStr
    ordinal: int = Field(ge=1)
    duration_seconds: float = Field(gt=0, le=60)
    execution_mode: Literal[
        "image_background", "video_background", "local_motion"
    ]
    product_plate_required: bool
    prompt: NonEmptyStr
    caption: str = ""
    input_materials: List[str] = Field(default_factory=list)
    max_attempts: int = Field(default=2, ge=1, le=5)
    idempotency_key: NonEmptyStr

class MediaExecutionPlanArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_execution_plan.v1"]
    production_bible_id: NonEmptyStr
    production_bible_hash: NonEmptyStr
    dependency_report_id: NonEmptyStr
    product_plate_id: str = ""
    aspect_ratio: NonEmptyStr
    canvas: List[int]
    fps: int = Field(ge=6, le=60)
    shots: List[MediaShotPlan] = Field(min_length=2)
    output_requirements: Dict[str, Any]
    call_budget: Dict[str, int]

class MediaShotResultArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_shot_result.v1"]
    plan_id: NonEmptyStr
    shot_id: NonEmptyStr
    attempt: int = Field(ge=1, le=5)
    execution_status: Literal["COMPLETED", "FAILED_RETRYABLE", "FAILED_FINAL"]
    provider: NonEmptyStr
    external_call_performed: bool
    provider_task_id: str = ""
    input_hashes: Dict[str, str]
    output_relative_path: str = ""
    output_content_hash: str = ""
    duration_seconds: float = Field(ge=0)
    error_code: str = ""
    error_detail: str = ""

class MediaCompositeManifestArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_composite_manifest.v1"]
    plan_id: NonEmptyStr
    shot_result_ids: List[NonEmptyStr] = Field(min_length=2)
    output_relative_path: NonEmptyStr
    output_content_hash: NonEmptyStr
    duration_seconds: float = Field(gt=0)
    codec: NonEmptyStr
    audio_codec: NonEmptyStr
    subtitle_mode: Literal["deterministic_ass"]
    command_summary: List[NonEmptyStr]
```

- [ ] 将五类模型加入 `ProfessionalArtifactType`、`_MODELS` 和
  `ARTIFACT_COLLECTIONS`。
- [ ] 运行 M13 契约测试，预期全部通过。
- [ ] 运行 `git diff --check` 并记录 checkpoint。

## Task 2：依赖诊断

**Files:**

- Create: `.hermes/plugins/product_creative/runtime/media_dependencies.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**

- Consumes: product id、material id、Production Bible。
- Produces:

```python
def inspect_media_dependencies(
    product_id: str,
    *,
    task_id: str,
    material_id: str,
    production_bible_id: str,
    required_free_bytes: int = 268_435_456,
) -> MediaDependencyReportArtifact:
    ...
```

- [ ] 写失败测试：ffmpeg/ffprobe、libx264、AAC、Pillow、中文字体、磁盘、素材、
  Bible 和 provider readiness 分别产生 READY/DEGRADED/BLOCKED。
- [ ] 使用 monkeypatch 模拟缺 ffmpeg、缺字体和磁盘不足，验证不会执行 subprocess
  生成或调用网络。
- [ ] 实现工具发现：

```python
ffmpeg = shutil.which("ffmpeg")
ffprobe = shutil.which("ffprobe")
font = first_existing(
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
)
free_bytes = shutil.disk_usage(product_root).free
```

- [ ] 用参数数组运行 `ffmpeg -hide_banner -encoders`，只保存版本和 capability
  布尔值，不保存环境变量或完整机器信息。
- [ ] 保存 `media_dependency_reports` 工件。
- [ ] 运行定向测试并记录 checkpoint。

## Task 3：产品 Plate 构建

**Files:**

- Create: `.hermes/plugins/product_creative/runtime/product_plate.py`
- Refactor: `.hermes/plugins/product_creative/capabilities/video/exact_video_service.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**

```python
def resolve_product_material(
    product_id: str,
    material_id: str = "",
) -> tuple[dict[str, Any], Path]:
    ...

def ensure_product_plate(
    product_id: str,
    *,
    task_id: str,
    material_id: str,
) -> ProductPlateArtifact:
    ...
```

- [ ] 写失败测试：
  - 有 alpha 的 PNG 使用 `source_alpha`。
  - 白色边缘背景图片使用 `edge_connected_background`。
  - 复杂背景降级 `full_rect` 并产生 warning。
  - RGB 产品区域像素值不被重绘。
  - 输出路径必须留在当前 product workspace。
- [ ] 将 `exact_video_service._resolve_material` 的职责提取为公共内部 helper，旧调用继续
  复用。
- [ ] 实现边缘连通抠图：只从画布边缘开始，对与边缘背景颜色距离低于阈值的像素
  设置 alpha=0；不使用生成模型，不修改前景 RGB。
- [ ] 计算源文件和 plate SHA-256，保存 `product_plates` 工件。
- [ ] 运行测试，确认输入文件不被修改。

## Task 4：Production Bible → Media Execution Plan

**Files:**

- Create: `.hermes/plugins/product_creative/runtime/media_plan.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**

```python
def compile_media_execution_plan(
    task: CreativeTaskRecord,
    *,
    dependency_report: MediaDependencyReportArtifact,
    product_plate: ProductPlateArtifact | None,
    provider: str,
    fps: int = 24,
) -> MediaExecutionPlanArtifact:
    ...
```

- [ ] 写失败测试：
  - 镜头顺序和总时长等于 Bible。
  - product plate 只进入指定产品镜头。
  - caption 不进入 Provider prompt 中的“生成文字”要求。
  - `shot_id + bible hash + provider + mode` 形成稳定 idempotency key。
  - retry policy 映射到 `max_attempts`，上限 5。
  - exact packaging 时没有 plate 必须 BLOCKED。
- [ ] 编译策略：
  - 无产品镜头优先 `video_background`。
  - 产品镜头使用 `image_background` 或 `video_background` 加 plate。
  - Provider 不可用的离线 fixture 使用 `local_motion`。
  - Prompt 明确“不要生成产品包装、产品文字或品牌标志”。
- [ ] 保存 `media_execution_plans` 工件，并写入
  `task.professional_artifacts["media_execution_plan"]`。
- [ ] 运行测试并记录 checkpoint。

## Task 5：镜头 Provider 兼容边界

**Files:**

- Create: `.hermes/plugins/product_creative/provider_shots.py`
- Modify: `.hermes/plugins/product_creative/provider_ports.py`
- Modify: `.hermes/plugins/product_creative/provider_gateway.py`
- Modify: `.hermes/plugins/product_creative/runtime/authorization.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**

扩展现有 `GenerationProviderGateway`，不创建第二个 gateway：

```python
def prepare_media_shot(
    self,
    product_id: str,
    plan_id: str,
    shot_id: str,
    provider: str,
    media_kind: str,
) -> Dict[str, Any]: ...

def submit_media_shot(
    self,
    product_id: str,
    payload_id: str,
    provider: str,
    mode: str,
    execution_policy_id: str = "",
) -> Dict[str, Any]: ...
```

- [ ] 写失败测试：shot payload 只包含背景/场景要求，不包含产品 plate 或字幕生成请求。
- [ ] 写 fixture gateway：生成真实 PNG/MP4 测试媒体，记录调用次数和 idempotency key。
- [ ] `provider_shots.py` 复用 Provider registry、payload schema、validation 和
  `create_generation_job`；不复制 HTTP client。
- [ ] 图片 shot 复用现有 image generation；视频 shot 复用现有 async video task。
- [ ] 将任务授权默认 `max_image_calls` 和 `max_video_calls` 更新为 5；每次真实 shot
  submit 消耗对应一次，状态轮询不消耗。
- [ ] 兼容旧 Fake Gateway：M10/M11 未调用新方法时不受影响。
- [ ] 运行 M10、M11 和 M13 gateway 测试。

## Task 6：镜头标准化与确定性字幕

**Files:**

- Create: `.hermes/plugins/product_creative/runtime/media_compositor.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**

```python
def render_shot(
    product_id: str,
    *,
    plan: MediaExecutionPlanArtifact,
    shot: MediaShotPlan,
    source_media: Path,
    product_plate: ProductPlateArtifact | None,
    attempt: int,
) -> MediaShotResultArtifact:
    ...

def compose_final_video(
    product_id: str,
    *,
    plan: MediaExecutionPlanArtifact,
    shot_results: list[MediaShotResultArtifact],
) -> MediaCompositeManifestArtifact:
    ...
```

- [ ] 写失败测试：
  - 图片和视频背景都能输出标准 MP4。
  - 输出为指定 canvas、fps、H.264、yuv420p、AAC。
  - 产品 plate 只做 scale/translate/overlay。
  - 中文字幕通过生成的 `.ass` 文件渲染。
  - 同一输入生成稳定 command summary 和 output hash。
  - concat 顺序严格等于 plan。
- [ ] ffmpeg 使用参数数组，不拼接 shell 字符串。
- [ ] 每个镜头补静音 AAC，避免 concat 因音轨结构不同失败。
- [ ] 使用 ffprobe 验证分辨率、时长、codec 和音频流。
- [ ] 失败写 `MediaShotResultArtifact`，不伪造 output path/hash。
- [ ] 最终 MP4 使用 `+faststart`，保存 manifest。

## Task 7：Reliable Media Production Engine 与恢复

**Files:**

- Create: `.hermes/plugins/product_creative/runtime/media_production.py`
- Modify: `.hermes/plugins/product_creative/runtime/creative_tasks.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`

**Interfaces:**

```python
def prepare_reliable_media_production(
    task: CreativeTaskRecord,
    *,
    provider: str,
    mode: Literal["fixture", "mock", "live"],
) -> Dict[str, Any]:
    ...

def execute_reliable_media_production(
    task: CreativeTaskRecord,
    *,
    provider: str,
    mode: Literal["fixture", "mock", "live"],
    authorization: TaskAuthorizationRecord | None,
) -> Dict[str, Any]:
    ...

def resume_reliable_media_production(
    task: CreativeTaskRecord,
    *,
    provider: str,
    mode: Literal["fixture", "mock", "live"],
    authorization: TaskAuthorizationRecord | None,
) -> Dict[str, Any]:
    ...
```

- [ ] 写失败测试：
  - prepare 只写依赖/plate/plan，不调用 Provider。
  - execute 跳过已完成 shot。
  - 第三个 shot 注入失败后只重试第三个。
  - 重启重新加载 task 后继续。
  - 超过 max attempts 进入 FAILED_FINAL。
  - 相同 idempotency key 不重复真实调用。
  - workspace A/B 的 plan、plate 和输出完全隔离。
- [ ] 每次执行前从 repository 重读 plan 和最新 shot results。
- [ ] 以 `shot_id + attempt` 保存不可变结果。
- [ ] 所有 shot 完成后才 compose。
- [ ] 将 manifest 和最终 result descriptor 写回 Creative Task。
- [ ] 生成结果复用现有 `generated_videos`、review 和 feedback。

## Task 8：兼容入口、授权与自然语言任务

**Files:**

- Modify: `.hermes/plugins/product_creative/capabilities/video/exact_video_service.py`
- Modify: `.hermes/plugins/product_creative/capabilities/video/executor.py`
- Modify: `.hermes/plugins/product_creative/application/planner.py`
- Modify: `.hermes/plugins/product_creative/runtime/creative_tasks.py`
- Modify: `.hermes/plugins/product_creative/contracts/models.py`
- Test: `tests/hermes_cli/test_product_creative_m13_media_production.py`
- Test: `tests/hermes_cli/test_product_creative_m11_artifacts.py`

**Interfaces:**

- `compose_exact_main_video` 在同时存在 Story Package 和 Production Bible 时进入
  M13 engine；无专业工件的直接旧调用保留 legacy compositor。
- Creative Task `professional_artifacts` 增加：
  - `media_dependency_report`
  - `product_plate`
  - `media_execution_plan`
  - `media_shot_results`
  - `media_composite_manifest`

- [ ] 写自然语言失败测试：
  - 创建包装保真视频任务时，授权前已形成 dependency/plate/plan。
  - 授权前 Provider 调用数为 0。
  - fixture 授权后形成真实 MP4。
  - “继续这个视频”恢复未完成镜头。
- [ ] exact packaging 计划将 `compose_exact_main_video` 标为
  `task_authorization`，但 prepare 阶段仍可在授权前执行。
- [ ] 将 M13 preparation 放入 `advance_offline_preparation` 的 Provider 边界之前。
- [ ] 将 M13 execute/resume 放入 `execute_authorized_mock_generation` 和
  `execute_authorized_live_generation`。
- [ ] 保持公开 tool 数量不变，继续由 `product_workflow_run` 驱动。
- [ ] 运行 M13、M11、M10 自然语言回归。

## Task 9：Desktop 投影

**Files:**

- Modify: `.hermes/plugins/product_creative/application/console_queries.py`
- Modify: `.hermes/plugins/product_creative/desktop_ui/index.js`
- Modify: `apps/desktop/src/app/desktop-plugins/product-creative-bundle.test.ts`
- Generate: `.hermes/plugins/product_creative/dashboard/dist/desktop.js`

**Interfaces:**

- `professional_summary.media`：

```json
{
  "dependency_status": "READY",
  "plan_id": "media-plan-...",
  "shots_completed": 5,
  "shots_total": 5,
  "current_failure": "",
  "composite_manifest_id": "media-composite-..."
}
```

- [ ] 写失败 UI 测试：Tasks、Assets、Review 和 Overview 显示媒体执行状态。
- [ ] Tasks 显示完成镜头数和失败/重试。
- [ ] Assets 显示 plate、shot outputs 和最终视频。
- [ ] Review 显示 Bible → plan → manifest provenance。
- [ ] Overview 显示 dependency blockers/warnings。
- [ ] 重建 bundle 并校验 source/bundle 都包含 M13 字段。
- [ ] 运行四个 Desktop plugin Vitest、bundle test 和 typecheck。

## Task 10：M13 离线真实媒体 E2E

**Files:**

- Extend: `tests/hermes_cli/test_product_creative_m13_media_production.py`
- Add fixture helpers under the same test file;不创建可误用的生产 fallback。

**Scenario:**

```text
用户：使用当前主图，包装和文字不能改变，按照已选创意生成一条竖版产品视频。
系统：建立 M12 专业工件、M13 dependency/plate/plan，停在任务授权。
用户：确认当前任务 fixture 生成。
系统：生成 5 个真实 fixture 背景镜头，叠加产品 plate 和确定性字幕，输出 MP4。
```

- [ ] 使用真实 Hermes agent loop，而不是直接调用底层函数作为主验收。
- [ ] 保存原始消息、工具选择、task id、plan、五个 shot result、manifest 和最终路径。
- [ ] 用 ffprobe 断言视频可播放、分辨率 1080×1920、时长与 Bible 容差小于 0.5 秒。
- [ ] 对产品 plate 的源 RGB hash/抽样像素做保真断言。
- [ ] 注入一次失败后输入“继续这个视频”，断言成功镜头调用计数不增加。
- [ ] 证明无网络、无环境凭据、无 Product Brain 指纹变化。

## Task 11：全量 Gate 与知识沉淀

**Files:**

- Create: `docs/M13_RELIABLE_MEDIA_PRODUCTION_IMPLEMENTATION.md`
- Modify: `AGENTS.md`
- Modify: `docs/AI_HANDOFF.md`
- Modify: `docs/PROJECT_STATE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/MVP_SCOPE.md`
- Modify: `docs/ARCHITECTURE_CURRENT.md`
- Modify: `docs/DECISION_LOG.md`
- Modify: `docs/PRODUCT_AGENT_DIRECTION.md`

- [ ] 运行 M13、M12、M11、M10 Python 回归。
- [ ] 运行 Desktop API/distribution/live adapter 离线回归。
- [ ] 运行 M9 review/recovery、contract invariants 和 public surface golden。
- [ ] 运行 Desktop plugin UI、bundle、typecheck 和 production build。
- [ ] 运行 `git diff --check`、版本一致性、必读文档、bundle hash 和敏感扫描。
- [ ] 文档记录：
  - 架构和工件。
  - fixture 与真实 Provider 边界。
  - ffmpeg/字体/磁盘诊断。
  - plate 算法和保真限制。
  - 恢复顺序。
  - 完整修改文件。
  - 测试命令和结果。
  - 未提交/未发布状态。
- [ ] 全部离线 Gate 通过后标记：
  `DONE_IN_WORKTREE_UNCOMMITTED_UNPUBLISHED_LIVE_GATE_PENDING`。
- [ ] 真实 Provider 只有在用户看到调用计划并再次确认后执行；成功后才能移除
  `LIVE_GATE_PENDING`。
- [ ] M14 设为唯一下一任务，但未经授权不开始编码。

## 建议提交分组

仅供用户后续授权，不在本轮自动执行：

1. `feat(product-creative): add M13 media execution contracts`
2. `feat(product-creative): add reliable shot production engine`
3. `feat(product-creative): expose M13 production state in desktop`
4. `test(product-creative): verify recoverable hybrid media production`
5. `docs(product-creative): record M13 implementation and recovery`
