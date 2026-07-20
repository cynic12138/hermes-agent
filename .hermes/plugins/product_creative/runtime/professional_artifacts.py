"""Persistence helpers for M11 professional creative artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

from ..common import ensure_product, now_iso, read_product_state, write_json
from ..context_safety import apply_generation_safe_state
from ..contracts.creative_artifacts import (
    BusinessSkillExecutionArtifact,
    CreativeTaskBriefArtifact,
    ProfessionalArtifact,
    ProfessionalArtifactType,
    ProductGroundingPackArtifact,
    ResearchInsightPackArtifact,
    SkillArtifactRef,
    professional_artifact_model,
)
from ..contracts.models import CreativeTaskRecord
from ..ports.runtime_repositories import (
    artifact_documents,
    artifacts,
    materials,
    product_brains,
)


ARTIFACT_COLLECTIONS = {
    "product_creative.creative_task_brief.v1": "creative_task_briefs",
    "product_creative.product_grounding_pack.v1": "product_grounding_packs",
    "product_creative.research_insight_pack.v1": "research_insight_packs",
    "product_creative.creative_candidate.v1": "creative_candidates",
    "product_creative.creative_decision.v1": "creative_decisions",
    "product_creative.story_package.v1": "story_packages",
    "product_creative.production_bible.v1": "production_bibles",
    "product_creative.media_dependency_report.v1": "media_dependency_reports",
    "product_creative.product_plate.v1": "product_plates",
    "product_creative.media_execution_plan.v1": "media_execution_plans",
    "product_creative.media_shot_result.v1": "media_shot_results",
    "product_creative.media_composite_manifest.v1": "media_composite_manifests",
    "product_creative.media_qa_report.v1": "media_qa_reports",
    "product_creative.media_repair_decision.v1": "media_repair_decisions",
    "product_creative.media_human_override.v1": "media_human_overrides",
    "product_creative.qa_report.v1": "qa_reports",
    "product_creative.skill_execution.v1": "skill_executions",
}


def professional_revision_suffix(task: CreativeTaskRecord) -> str:
    return f"-r{len(task.revision_messages)}" if task.revision_messages else ""


def save_professional_artifact(artifact: ProfessionalArtifactType) -> str:
    base = ensure_product(artifact.product_id)
    collection = ARTIFACT_COLLECTIONS[artifact.schema_name]
    return artifact_documents(base).save(
        collection,
        artifact.artifact_id,
        artifact.model_dump(mode="json"),
    )


def persist_professional_task_checkpoint(task: CreativeTaskRecord) -> str:
    """Persist professional artifact references after each completed stage."""

    task.updated_at = now_iso()
    path = (
        Path(task.artifact_path)
        if task.artifact_path
        else (
            ensure_product(task.product_id)
            / "artifacts"
            / "creative_tasks"
            / f"{task.task_id}.json"
        )
    )
    task.artifact_path = str(path)
    write_json(path, task.model_dump(mode="json"))
    return str(path)


def load_professional_artifact(
    product_id: str,
    artifact_id: str,
) -> ProfessionalArtifact:
    base = ensure_product(product_id)
    payload = artifacts().get(base.name, artifact_id)
    if not payload:
        raise FileNotFoundError(
            f"professional artifact '{artifact_id}' does not exist for product '{base.name}'"
        )
    model = professional_artifact_model(str(payload.get("schema_name") or ""))
    artifact = model.model_validate(payload)
    if artifact.product_id != base.name:
        raise ValueError("professional artifact belongs to a different product workspace")
    return artifact


def record_business_skill_execution(
    task: CreativeTaskRecord,
    *,
    skill_name: str,
    run_result: Any,
    input_artifacts: list[Any],
    output_artifacts: list[Any],
    actual_actions: list[str] | None = None,
) -> BusinessSkillExecutionArtifact:
    """Persist one completed, tamper-evident business Skill execution."""

    from .business_skills import load_business_skill_catalog

    spec = load_business_skill_catalog()[skill_name]
    suffix = professional_revision_suffix(task)
    same_stage = [
        artifact_id
        for artifact_id in task.professional_artifacts.get("skill_executions", [])
        if f"-{spec.stage}" in str(artifact_id)
    ]
    ordinal = len(same_stage) + 1

    def references(items: list[Any]) -> list[SkillArtifactRef]:
        return [
            SkillArtifactRef(
                artifact_id=str(item.artifact_id),
                content_hash=str(item.content_hash),
            )
            for item in items
        ]

    timestamp = now_iso()
    execution = BusinessSkillExecutionArtifact(
        artifact_id=(
            f"skill-exec-{task.task_id}{suffix}-{spec.stage}-{ordinal}"
        ),
        task_id=task.task_id,
        product_id=task.product_id,
        created_at=timestamp,
        source_refs=[str(item.artifact_id) for item in input_artifacts],
        status="PASS",
        skill_name=spec.name,
        skill_version=spec.version,
        stage=spec.stage,
        execution_mode=str(run_result.execution_mode),
        input_artifacts=references(input_artifacts),
        output_artifacts=references(output_artifacts),
        allowed_tools=list(spec.tool_allowlist),
        actual_actions=list(actual_actions or []),
        model_metadata=dict(run_result.model_metadata),
        started_at=timestamp,
        finished_at=timestamp,
        execution_status="COMPLETED",
    )
    save_professional_artifact(execution)
    recorded = task.professional_artifacts.setdefault("skill_executions", [])
    recorded.append(execution.artifact_id)
    return execution


def record_failed_business_skill_execution(
    task: CreativeTaskRecord,
    *,
    skill_name: str,
    input_artifacts: list[Any],
    actual_actions: list[str] | None,
    error: Exception,
) -> BusinessSkillExecutionArtifact:
    """Persist a failed Skill execution without claiming output artifacts."""

    from .business_skills import load_business_skill_catalog

    spec = load_business_skill_catalog()[skill_name]
    suffix = professional_revision_suffix(task)
    recorded = task.professional_artifacts.setdefault("skill_executions", [])
    ordinal = (
        len(
            [
                artifact_id
                for artifact_id in recorded
                if f"-{spec.stage}" in str(artifact_id)
            ]
        )
        + 1
    )
    timestamp = now_iso()
    execution = BusinessSkillExecutionArtifact(
        artifact_id=(
            f"skill-exec-{task.task_id}{suffix}-{spec.stage}-{ordinal}"
        ),
        task_id=task.task_id,
        product_id=task.product_id,
        created_at=timestamp,
        source_refs=[str(item.artifact_id) for item in input_artifacts],
        status="BLOCKED",
        skill_name=spec.name,
        skill_version=spec.version,
        stage=spec.stage,
        execution_mode="degraded",
        input_artifacts=[
            SkillArtifactRef(
                artifact_id=str(item.artifact_id),
                content_hash=str(item.content_hash),
            )
            for item in input_artifacts
        ],
        output_artifacts=[],
        allowed_tools=list(spec.tool_allowlist),
        actual_actions=list(actual_actions or []),
        model_metadata={},
        started_at=timestamp,
        finished_at=timestamp,
        execution_status="FAILED",
        failure_code="runtime_execution_failed",
        failure_detail=f"{type(error).__name__}: {error}"[:1000],
    )
    save_professional_artifact(execution)
    recorded.append(execution.artifact_id)
    return execution


def _channel(message: str) -> str:
    if "小红书" in message:
        return "xiaohongshu"
    if "抖音" in message:
        return "douyin"
    if any(marker in message for marker in ("天猫", "京东", "拼多多", "电商")):
        return "ecommerce"
    return ""


def _duration_seconds(message: str) -> int | None:
    match = re.search(r"(\d{1,3})\s*秒", message)
    if not match:
        return None
    value = int(match.group(1))
    return value if 1 <= value <= 600 else None


def _aspect_ratio(message: str) -> str:
    explicit = re.search(r"(?<!\d)(9:16|16:9|1:1|4:3|3:4)(?!\d)", message)
    if explicit:
        return explicit.group(1)
    if "竖屏" in message:
        return "9:16"
    if "横屏" in message:
        return "16:9"
    if "方图" in message or "方形" in message:
        return "1:1"
    return ""


def ensure_creative_task_brief(task: CreativeTaskRecord) -> CreativeTaskBriefArtifact:
    from .business_skills import BusinessSkillRunResult

    suffix = professional_revision_suffix(task)
    artifact_id = f"brief-{task.task_id}{suffix}"
    constraints = list(task.request.deliverables)
    if task.request.requires_fresh_inspiration:
        constraints.append("使用带来源与日期的近期灵感；来源不足时明确降级")
    if task.request.preserve_exact_packaging:
        constraints.append("商品主体和包装保持原始像素，不得交给生成式模型重绘")
    artifact = CreativeTaskBriefArtifact(
        artifact_id=artifact_id,
        task_id=task.task_id,
        product_id=task.product_id,
        created_at=task.created_at,
        source_refs=[
            f"user-message:{task.task_id}",
            *(
                [f"task-revision:{len(task.revision_messages)}"]
                if task.revision_messages
                else []
            ),
        ],
        status="READY",
        original_message=task.request.raw_message,
        interpreted_goal=(
            f"{task.request.raw_message}\n本次修订要求：{task.revision_messages[-1]}"
            if task.revision_messages
            else task.request.raw_message
        ),
        deliverables=list(task.request.deliverables),
        channel=_channel(task.request.raw_message),
        duration_seconds=_duration_seconds(task.request.raw_message),
        aspect_ratio=_aspect_ratio(task.request.raw_message),
        constraints=constraints,
        prohibited_requirements=[
            "不得编造产品事实或功效",
            "外部灵感不得自动写入 Canonical Product Brain",
        ],
        unknown_fields=[
            question.field_key
            for question in task.questions
            if question.field_key
        ],
        assumptions=["低风险的场景、人物、镜头和节奏可由系统自主决定"],
        autonomy_mode=task.request.autonomy_mode,
        authorization_scope={
            "external_research_required": task.request.requires_fresh_inspiration,
            "paid_generation_required": bool(
                {"image", "video"} & set(task.request.deliverables)
            ),
            "product_brain_writeback_included": False,
        },
    )
    save_professional_artifact(artifact)
    task.professional_artifacts["creative_task_brief"] = artifact.artifact_id
    record_business_skill_execution(
        task,
        skill_name="task-director",
        run_result=BusinessSkillRunResult(
            payload=artifact.model_dump(mode="json"),
            execution_mode="deterministic",
            model_metadata={
                "engine": "creative_task_request_compiler",
                "rule_version": "m12.1",
            },
        ),
        input_artifacts=[],
        output_artifacts=[artifact],
        actual_actions=["task_state_read"],
    )
    task.professional_artifact_status = "in_progress"
    return artifact


def _current_packaging_material(product_id: str) -> Dict[str, Any]:
    active = [
        item
        for item in materials().list(product_id)
        if item.get("status", "active") == "active"
    ]
    for role in ("current_main_image", "video_first_frame", "product_photo"):
        for item in reversed(active):
            if item.get("role") == role:
                return item
    return {}


def ensure_product_grounding_pack(
    task: CreativeTaskRecord,
) -> ProductGroundingPackArtifact:
    suffix = professional_revision_suffix(task)
    current = product_brains().current(task.product_id)
    state = current.get("state") if isinstance(current.get("state"), dict) else {}
    safe_state = apply_generation_safe_state(state)
    generation_safe = (
        safe_state.get("generation_safe")
        if isinstance(safe_state.get("generation_safe"), dict)
        else {}
    )
    compliance = state.get("compliance") if isinstance(state.get("compliance"), dict) else {}
    basic = state.get("basic") if isinstance(state.get("basic"), dict) else {}
    task_claims = (
        task.task_context.get("claim_boundaries")
        if isinstance(task.task_context.get("claim_boundaries"), dict)
        else {}
    )
    task_sku = str(task.task_context.get("product_sku") or "").strip()
    readiness_fields = {item.key: item for item in task.readiness.fields}
    packaging_material = _current_packaging_material(task.product_id)
    selected_materials = []
    if packaging_material:
        selected_materials.append(
            {
                "material_id": str(packaging_material.get("material_id") or ""),
                "role": str(packaging_material.get("role") or ""),
                "source_id": str(packaging_material.get("source_id") or ""),
                "sha256": str(packaging_material.get("sha256") or ""),
            }
        )
    source_refs = [f"brain:{current.get('brain_version_id', '')}"]
    if packaging_material.get("material_id"):
        source_refs.append(f"material:{packaging_material['material_id']}")
    source_refs.append(f"readiness:{task.readiness.readiness_id}")
    if task.task_context:
        source_refs.append(f"task-context:{task.task_id}")
    readiness_status = "READY" if task.readiness.ready else "NEEDS_INPUT"
    artifact = ProductGroundingPackArtifact(
        artifact_id=f"grounding-{task.task_id}{suffix}",
        task_id=task.task_id,
        product_id=task.product_id,
        created_at=now_iso(),
        source_refs=source_refs,
        status="READY" if task.readiness.ready else "BLOCKED",
        brain_version_id=str(current.get("brain_version_id") or "unversioned"),
        brain_fingerprint=str(current.get("content_hash") or "0" * 64),
        sku={
            "status": readiness_fields.get("product_sku").status
            if readiness_fields.get("product_sku")
            else "UNKNOWN",
            "value": task_sku
            or basic.get("sku")
            or basic.get("sku_name")
            or basic.get("specification")
            or state.get("sku"),
        },
        packaging={
            "status": readiness_fields.get("current_packaging").status
            if readiness_fields.get("current_packaging")
            else "UNKNOWN",
            "material_id": str(packaging_material.get("material_id") or ""),
            "role": str(packaging_material.get("role") or ""),
            "sha256": str(packaging_material.get("sha256") or ""),
            "preserve_exact_packaging": task.request.preserve_exact_packaging,
        },
        confirmed_claims=[
            str(item)
            for item in (
                task_claims.get("allowed")
                or compliance.get("allowed_claims")
                or generation_safe.get("selling_points")
                or []
            )
            if str(item).strip()
        ],
        forbidden_claims=[
            str(item)
            for item in dict.fromkeys(
                [
                    *(compliance.get("forbidden_claims") or []),
                    *(task_claims.get("forbidden") or []),
                ]
            )
            if str(item).strip()
        ],
        selected_materials=selected_materials,
        field_evidence_refs={
            key: list(field.source_ids)
            for key, field in readiness_fields.items()
            if field.source_ids
        },
        blockers=list(task.readiness.blockers),
        readiness_status=readiness_status,
    )
    save_professional_artifact(artifact)
    task.professional_artifacts["product_grounding_pack"] = artifact.artifact_id
    task.professional_artifact_status = "in_progress"
    return artifact


def ensure_initial_professional_artifacts(task: CreativeTaskRecord) -> None:
    if not task.request.deliverables:
        return
    ensure_creative_task_brief(task)
    ensure_product_grounding_pack(task)


def _source_type(snapshot: Dict[str, Any]) -> str:
    channel = str(snapshot.get("channel") or "").lower()
    provider = str(snapshot.get("provider") or "").lower()
    combined = f"{channel} {provider}"
    if "xiaohongshu" in combined or "xhs" in combined:
        return "xiaohongshu"
    if "douyin" in combined:
        return "douyin"
    if "web" in combined:
        return "web"
    return "historical"


def _item_text(item: Dict[str, Any], source_type: str) -> str:
    first5 = item.get("first5_analysis")
    first5_summary = (
        str(first5.get("summary") or "")
        if isinstance(first5, dict)
        else ""
    )
    if source_type == "douyin":
        detail = first5_summary or str(item.get("transcript") or item.get("text") or item.get("title") or "")
        return f"前5秒/口播结构：{detail.strip()}"
    if source_type == "xiaohongshu":
        detail = str(item.get("text") or item.get("content") or item.get("title") or "")
        return f"消费者语言/使用场景：{detail.strip()}"
    detail = str(item.get("text") or item.get("summary") or item.get("title") or "")
    return f"事件/时效背景：{detail.strip()}"


def _clean_text(value: Any, limit: int = 1200) -> str:
    return " ".join(str(value or "").split())[:limit]


def research_insight_from_item(
    *,
    task_id: str,
    snapshot_id: str,
    item_index: int,
    source_type: str,
    item: Dict[str, Any],
) -> Dict[str, Any]:
    title = _clean_text(item.get("title"), 240)
    text = _clean_text(
        item.get("transcript")
        or item.get("text")
        or item.get("content")
        or item.get("summary"),
        1600,
    )
    published_at = _clean_text(
        item.get("published_at")
        or item.get("publish_time")
        or item.get("date"),
        80,
    )
    source_ref = f"snapshot:{snapshot_id}#item:{item_index}"
    if source_type == "web":
        observation = "；".join(part for part in (title, text) if part)
        features = {
            "dated_context": published_at or "time_unknown",
            "event_or_trend": observation,
        }
        payload = {
            "insight_kind": "dated_context",
            "observation": observation or "公开网页条目缺少可读正文。",
            "why_it_matters": (
                "为任务提供带时间边界的事件、节日或公开渠道背景。"
            ),
            "adaptation_rule": (
                "只借用可核验的时间背景和内容机会，产品表达仍以 Grounding Pack 为准。"
            ),
            "creative_use": "可用于设定今日选题、场景时点或开场背景。",
            "avoid_copying": "不得把网页中的产品、销量、功效或竞品承诺复制为本产品事实。",
            "source_features": features,
            "summary": f"事件/时效背景：{observation}",
            "confidence": 0.8 if published_at else 0.65,
        }
    elif source_type == "xiaohongshu":
        stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
        comment_count = stats.get("comments") or stats.get("commentCount") or 0
        features = {
            "title_structure": title or "生活问题/随身准备型标题",
            "consumer_language": text or title or "无可读用户原话",
            "emotion": "从容、被理解、减少尴尬感",
            "life_scene": title or text or "日常生活场景待进一步确认",
            "comment_concern": (
                f"该条目记录 {comment_count} 条评论信号，需在原始评论可用时进一步归纳。"
            ),
        }
        observation = "；".join(part for part in (title, text) if part)
        payload = {
            "insight_kind": "consumer_scene",
            "observation": observation or "小红书条目缺少可读正文。",
            "why_it_matters": "提供用户自然语言、生活场景、情绪和种草叙事入口。",
            "adaptation_rule": "借用用户表达方式和场景结构，重新围绕已确认产品事实创作。",
            "creative_use": "可用于角色处境、标题语气、生活化冲突和情绪收束。",
            "avoid_copying": "不得照抄原帖文案、个人经历或外部产品主张。",
            "source_features": features,
            "summary": f"消费者语言/使用场景：{observation}",
            "confidence": 0.72,
        }
    elif source_type == "douyin":
        first5 = item.get("first5_analysis")
        first5 = first5 if isinstance(first5, dict) else {}
        analysis = first5.get("analysis")
        analysis = analysis if isinstance(analysis, dict) else {}
        copy_analysis = item.get("copy_analysis")
        copy_analysis = copy_analysis if isinstance(copy_analysis, dict) else {}
        summary = _clean_text(first5.get("summary"), 800)
        visual_hook = _clean_text(
            analysis.get("visual_hook")
            or analysis.get("visual_hook_0_5s")
            or summary
            or title,
            500,
        )
        spoken_hook = _clean_text(
            analysis.get("spoken_hook")
            or copy_analysis.get("opening_hook")
            or text,
            500,
        )
        features = {
            "visual_hook_0_5s": visual_hook or "前五秒视觉钩子未解析",
            "spoken_hook": spoken_hook or "首句口播未解析",
            "pacing": _clean_text(analysis.get("pacing") or "节奏信息待补充", 400),
            "conflict": _clean_text(analysis.get("conflict") or "冲突信息待补充", 400),
            "turn": _clean_text(
                analysis.get("turn")
                or copy_analysis.get("replicable_formula")
                or "转折信息待补充",
                400,
            ),
            "audio_or_cta": _clean_text(
                analysis.get("audio")
                or analysis.get("cta")
                or copy_analysis.get("calls_to_action")
                or "音频/CTA 信息待补充",
                400,
            ),
        }
        observation = "；".join(
            part for part in (visual_hook, spoken_hook, text) if part
        )
        payload = {
            "insight_kind": "short_video_hook",
            "observation": observation or "抖音条目缺少可读钩子与转录。",
            "why_it_matters": "提供前五秒停止力、口播入口、节奏、冲突和转折结构。",
            "adaptation_rule": "复用视听结构和叙事节拍，不复制原视频文案或产品承诺。",
            "creative_use": "可用于候选的 stop reason、hook、progression、turn 和 audio。",
            "avoid_copying": "不得复刻原视频角色身份、完整口播、画面或外部产品事实。",
            "source_features": features,
            "summary": f"前5秒/口播结构：{observation}",
            "confidence": 0.82 if analysis or copy_analysis else 0.68,
        }
    elif source_type == "workspace":
        observation = "；".join(part for part in (title, text) if part)
        payload = {
            "insight_kind": "workspace_signal",
            "observation": observation or "Workspace 条目缺少可读描述。",
            "why_it_matters": "提供当前产品已拥有的素材、限制和可复用资产。",
            "adaptation_rule": "把已确认素材作为生产输入，不从文件名推断产品事实。",
            "creative_use": "可用于素材角色、构图和可制作性判断。",
            "avoid_copying": "不得把未分析素材的文件名当作内容证据。",
            "source_features": {"workspace_signal": observation or "material_only"},
            "summary": f"本地素材/工作区信号：{observation}",
            "confidence": 0.75,
        }
    else:
        outcome = _clean_text(
            item.get("result_status")
            or item.get("review_status")
            or item.get("feedback"),
            300,
        )
        observation = "；".join(part for part in (title, text) if part)
        payload = {
            "insight_kind": "historical_pattern",
            "observation": observation or "历史条目缺少可读描述。",
            "why_it_matters": "用于识别重复方向、失败模式和已经验证的资产。",
            "adaptation_rule": "保留可复用资产，同时改变导致重复或失败的叙事结构。",
            "creative_use": "可用于历史相似度、候选差异和风险说明。",
            "avoid_copying": "不得把历史结果自动视为长期偏好或成功规则。",
            "source_features": {
                "repetition_pattern": observation or "pattern_unknown",
                "outcome_signal": outcome or "outcome_unknown",
                "reusable_asset": _clean_text(
                    item.get("reusable_asset") or item.get("asset_id") or "none_identified",
                    300,
                ),
            },
            "summary": f"历史模式/结果信号：{observation}",
            "confidence": 0.7,
        }
    return {
        "insight_id": (
            f"insight-{task_id}-{snapshot_id}-{item_index}"
        ),
        "source_type": source_type,
        "source_ref": source_ref,
        "published_at": published_at,
        **payload,
    }


def ensure_research_insight_pack(
    task: CreativeTaskRecord,
) -> ResearchInsightPackArtifact:
    from .business_skills import BusinessSkillRunResult

    suffix = professional_revision_suffix(task)
    snapshots = [
        item
        for item in artifacts().list(task.product_id, "external_source_snapshots")
        if item.get("not_product_fact") is True
        and str(item.get("created_at") or "") >= task.created_at
    ]
    snapshots.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("snapshot_id") or ""),
        )
    )
    insights = []
    source_refs = []
    data_sources = []
    degradation_notes = []
    for snapshot in snapshots:
        snapshot_id = str(snapshot.get("snapshot_id") or "")
        source_type = _source_type(snapshot)
        if source_type not in data_sources:
            data_sources.append(source_type)
        if snapshot_id:
            source_refs.append(f"snapshot:{snapshot_id}")
        items = [
            item
            for item in snapshot.get("items") or []
            if isinstance(item, dict)
        ]
        if not items:
            degradation_notes.append(
                f"{source_type} source '{snapshot_id or 'unknown'}' returned no usable items"
            )
            continue
        for index, item in enumerate(items, start=1):
            insight = research_insight_from_item(
                task_id=task.task_id,
                snapshot_id=snapshot_id or "unknown",
                item_index=index,
                source_type=source_type,
                item=item,
            )
            if not insight["observation"].strip():
                continue
            insights.append(insight)
    if not insights:
        degradation_notes.append(
            "No task-scoped realtime source was available; continue only with confirmed Product Brain and historical context."
        )
    artifact = ResearchInsightPackArtifact(
        artifact_id=f"research-{task.task_id}{suffix}",
        task_id=task.task_id,
        product_id=task.product_id,
        created_at=now_iso(),
        source_refs=source_refs,
        status="READY",
        research_goal=f"为任务“{task.request.raw_message}”提取可追溯的近期场景、语言和前五秒结构",
        data_sources=data_sources,
        insights=insights,
        degradation_notes=degradation_notes,
        not_product_fact=True,
    )
    save_professional_artifact(artifact)
    task.professional_artifacts["research_insight_pack"] = artifact.artifact_id
    brief = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["creative_task_brief"],
    )
    grounding = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["product_grounding_pack"],
    )
    record_business_skill_execution(
        task,
        skill_name="research-director",
        run_result=BusinessSkillRunResult(
            payload=artifact.model_dump(mode="json"),
            execution_mode="deterministic",
            model_metadata={
                "engine": "source_specific_insight_compiler",
                "rule_version": "m12.1",
            },
        ),
        input_artifacts=[brief, grounding],
        output_artifacts=[artifact],
        actual_actions=[
            "artifact_read",
            "source_snapshot_read",
            "history_search",
        ],
    )
    task.professional_artifact_status = "in_progress"
    return artifact


def build_professional_creative_pack(task: CreativeTaskRecord) -> Dict[str, Any]:
    from .creative_direction import build_professional_creative_pack as build

    return build(task)
