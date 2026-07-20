"""Compile an approved Production Bible into a bounded shot execution graph."""

from __future__ import annotations

import hashlib
from typing import Any

from ..common import now_iso
from ..contracts.creative_artifacts import (
    MediaDependencyReportArtifact,
    MediaExecutionPlanArtifact,
    MediaShotPlan,
    ProductPlateArtifact,
    ProductionBibleArtifact,
)
from .professional_artifacts import (
    load_professional_artifact,
    save_professional_artifact,
)


_CANVAS_BY_RATIO = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "3:4": (1080, 1440),
    "4:3": (1440, 1080),
}


def _execution_mode(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized in {"local-fixture", "fixture", "offline-fixture"}:
        return "local_motion"
    if "image" in normalized and "video" not in normalized:
        return "image_background"
    return "video_background"


def _continuity_directive(bible: ProductionBibleArtifact) -> str:
    characters: list[str] = []
    for shot in bible.shots:
        for value in shot.characters:
            name = str(value).strip()
            if name and name not in characters:
                characters.append(name)
    named_anchor = (
        f"主角标识为{'、'.join(characters)}；"
        if characters
        else "主角使用首镜头确立的人物身份；"
    )
    return (
        "连续性要求："
        f"{named_anchor}"
        "若镜头中出现人物，必须保持同一主角身份、面部特征、"
        "发型发色、服装与随身配饰稳定；"
        "后续镜头以首镜头参考图为人物和视觉风格的权威锚点。"
    )


def _shot_prompt(shot: Any, *, continuity_directive: str) -> str:
    characters = "、".join(str(item) for item in shot.characters if str(item).strip())
    character_line = f"角色：{characters}。" if characters else ""
    return (
        f"生成竖屏短视频的背景、场景与人物动作素材。"
        f"场景：{shot.scene}。构图：{shot.composition}。"
        f"动作：{shot.action}。{character_line}"
        f"{continuity_directive}"
        "仅生成背景、场景、人物和装饰元素；"
        "不得生成产品包装、产品主体、品牌标志或包装文字；"
        "不得生成字幕、标题、角标或任何可读文字。"
    )


def _idempotency_key(
    task_id: str,
    shot_id: str,
    bible_hash: str,
    provider: str,
    mode: str,
) -> str:
    payload = "\0".join((shot_id, bible_hash, provider, mode))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{task_id}:{shot_id}:{digest}"


def compile_media_execution_plan(
    task: Any,
    *,
    dependency_report: MediaDependencyReportArtifact,
    product_plate: ProductPlateArtifact | None,
    provider: str,
    fps: int = 24,
) -> MediaExecutionPlanArtifact:
    """Create a deterministic, recoverable shot graph from the current Bible."""

    if dependency_report.product_id != task.product_id:
        raise ValueError("dependency report belongs to a different product workspace")
    if dependency_report.overall_status == "BLOCKED":
        raise ValueError("media dependencies are blocked")
    bible_id = str(task.professional_artifacts.get("production_bible") or "")
    if not bible_id:
        raise ValueError("creative task has no Production Bible")
    loaded = load_professional_artifact(task.product_id, bible_id)
    if not isinstance(loaded, ProductionBibleArtifact):
        raise ValueError("creative task production artifact is not a Production Bible")
    bible = loaded

    exact_packaging = (
        bool(getattr(task.request, "preserve_exact_packaging", False))
        or bible.packaging_strategy == "exact-main-composite"
    )
    if exact_packaging and product_plate is None:
        raise ValueError("exact packaging media plan requires a product plate")
    if product_plate is not None and product_plate.product_id != task.product_id:
        raise ValueError("product plate belongs to a different product workspace")

    immutable_materials = {
        material_id
        for material_id, role in bible.asset_roles.items()
        if role == "immutable_product_plate"
    }
    mode = _execution_mode(provider)
    retry_count = int(bible.retry_policy.get("max_retries_per_shot") or 0)
    max_attempts = min(5, max(1, retry_count + 1))
    continuity_directive = _continuity_directive(bible)
    shots: list[MediaShotPlan] = []
    for ordinal, shot in enumerate(bible.shots, start=1):
        plate_required = bool(
            immutable_materials.intersection(
                str(item) for item in shot.input_materials
            )
        )
        motion_description = str(shot.action).strip()
        motion_required = mode == "video_background" and bool(motion_description)
        shots.append(
            MediaShotPlan(
                shot_id=shot.shot_id,
                ordinal=ordinal,
                duration_seconds=shot.duration_seconds,
                execution_mode=mode,
                product_plate_required=plate_required,
                prompt=_shot_prompt(
                    shot,
                    continuity_directive=continuity_directive,
                ),
                motion_required=motion_required,
                motion_description=motion_description,
                maximum_freeze_ratio=0.65,
                product_plate_motion=(
                    "subtle_entrance" if plate_required else "none"
                ),
                caption=shot.caption,
                input_materials=[
                    str(item)
                    for item in shot.input_materials
                    if str(item) not in immutable_materials
                ],
                max_attempts=max_attempts,
                idempotency_key=_idempotency_key(
                    task.task_id,
                    shot.shot_id,
                    bible.content_hash,
                    provider,
                    mode,
                ),
            )
        )

    if exact_packaging and not any(shot.product_plate_required for shot in shots):
        raise ValueError(
            "exact packaging Production Bible does not assign the product plate to a shot"
        )

    aspect_ratio = str(bible.specification.get("aspect_ratio") or "9:16")
    specified_canvas = bible.specification.get("canvas")
    canvas = (
        tuple(int(value) for value in specified_canvas)
        if isinstance(specified_canvas, list)
        and len(specified_canvas) == 2
        and all(int(value) > 0 for value in specified_canvas)
        else _CANVAS_BY_RATIO.get(aspect_ratio)
    )
    if canvas is None:
        raise ValueError(f"unsupported media aspect ratio '{aspect_ratio}'")
    effective_fps = (
        int(bible.specification.get("fps") or fps)
        if fps == 24
        else fps
    )
    image_calls = sum(shot.execution_mode == "image_background" for shot in shots)
    video_calls = sum(shot.execution_mode == "video_background" for shot in shots)
    provider_token = hashlib.sha256(provider.encode("utf-8")).hexdigest()[:8]
    artifact = MediaExecutionPlanArtifact(
        artifact_id=f"media-plan-{task.task_id}-{provider_token}",
        task_id=task.task_id,
        product_id=task.product_id,
        created_at=now_iso(),
        source_refs=[
            bible.artifact_id,
            dependency_report.artifact_id,
            *([product_plate.artifact_id] if product_plate else []),
        ],
        status="READY",
        production_bible_id=bible.artifact_id,
        production_bible_hash=bible.content_hash,
        dependency_report_id=dependency_report.artifact_id,
        product_plate_id=product_plate.artifact_id if product_plate else "",
        aspect_ratio=aspect_ratio,
        canvas=canvas,
        fps=effective_fps,
        shots=shots,
        output_requirements={
            "codec": "h264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "subtitle_mode": "deterministic_ass",
            "packaging_strategy": bible.packaging_strategy,
            "delivery_requirements": list(bible.delivery_requirements),
            "provider": provider,
            "continuity_strategy": (
                "first-shot-reference-chain"
                if mode == "image_background"
                else "prompt-only"
            ),
            "continuity_anchor_shot_id": shots[0].shot_id,
            "continuity_directive": continuity_directive,
        },
        call_budget={
            "image": min(5, image_calls),
            "video": min(5, video_calls),
        },
    )
    save_professional_artifact(artifact)
    task.professional_artifacts["media_execution_plan"] = artifact.artifact_id
    return artifact
