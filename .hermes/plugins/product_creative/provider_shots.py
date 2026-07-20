"""Shot-scoped provider payloads built from an approved media execution plan."""

from __future__ import annotations

import base64
import hashlib
import math
from pathlib import Path
from typing import Any, Dict

from .common import ensure_product, now_iso, read_json, write_json
from .contracts.creative_artifacts import (
    MediaExecutionPlanArtifact,
    MediaShotResultArtifact,
)
from .ports.runtime_repositories import artifacts
from .provider_contracts import PROVIDER_PAYLOAD_SCHEMA_VERSION
from .provider_registry import provider_entry


def _safe_id(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in "-_." else "-"
        for character in value
    ).strip("-_.")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_plan(product_id: str, plan_id: str) -> MediaExecutionPlanArtifact:
    from .runtime.professional_artifacts import load_professional_artifact

    artifact = load_professional_artifact(product_id, plan_id)
    if not isinstance(artifact, MediaExecutionPlanArtifact):
        raise ValueError("media shot payload requires a Media Execution Plan")
    return artifact


_REFERENCE_IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_MAX_REFERENCE_IMAGE_BYTES = 10 * 1024 * 1024


def _continuity_reference(
    product_root: Path,
    plan: MediaExecutionPlanArtifact,
    shot: Any,
) -> dict[str, str]:
    strategy = str(plan.output_requirements.get("continuity_strategy") or "")
    anchor_shot_id = str(
        plan.output_requirements.get("continuity_anchor_shot_id")
        or plan.shots[0].shot_id
    )
    if (
        strategy != "first-shot-reference-chain"
        or shot.ordinal <= 1
        or shot.shot_id == anchor_shot_id
    ):
        return {}

    candidates: list[MediaShotResultArtifact] = []
    for payload in artifacts().list(product_root.name, "media_shot_results"):
        if (
            payload.get("plan_id") != plan.artifact_id
            or payload.get("shot_id") != anchor_shot_id
            or payload.get("execution_status") != "COMPLETED"
        ):
            continue
        try:
            candidate = MediaShotResultArtifact.model_validate(payload)
        except ValueError:
            continue
        if candidate.source_relative_path:
            candidates.append(candidate)
    if not candidates:
        raise ValueError(
            "later image shot requires a completed first-shot continuity reference"
        )
    anchor = max(candidates, key=lambda item: (item.attempt, item.created_at))
    root = product_root.resolve()
    source = (root / anchor.source_relative_path).resolve()
    if root != source and root not in source.parents:
        raise ValueError("continuity reference resolves outside the product workspace")
    if not source.is_file():
        raise FileNotFoundError("continuity reference image is missing")
    mime_type = _REFERENCE_IMAGE_MIME.get(source.suffix.lower(), "")
    if not mime_type:
        raise ValueError("continuity reference must be PNG, JPEG, or WebP")
    size = source.stat().st_size
    if size <= 0 or size > _MAX_REFERENCE_IMAGE_BYTES:
        raise ValueError("continuity reference image exceeds the safe size boundary")
    content_hash = _hash_file(source)
    return {
        "shot_id": anchor_shot_id,
        "content_hash": content_hash,
        "data_url": (
            f"data:{mime_type};base64,"
            + base64.b64encode(source.read_bytes()).decode("ascii")
        ),
    }


def prepare_media_shot(
    product_id: str,
    plan_id: str,
    shot_id: str,
    provider: str,
    media_kind: str,
) -> Dict[str, Any]:
    """Prepare a provider-compatible payload that excludes product/text layers."""

    if media_kind not in {"image", "video"}:
        raise ValueError("media_kind must be image or video")
    product_root = ensure_product(product_id)
    plan = _load_plan(product_root.name, plan_id)
    shot = next((item for item in plan.shots if item.shot_id == shot_id), None)
    if shot is None:
        raise ValueError(f"shot '{shot_id}' is not part of media plan '{plan_id}'")

    if provider == "local-fixture":
        entry: dict[str, Any] = {
            "name": provider,
            "status": "fixture",
            "supported_types": ["image", "video"],
            "execute_supported": False,
            "request_defaults": {},
        }
    else:
        entry = provider_entry(provider)
        if media_kind not in (entry.get("supported_types") or []):
            raise ValueError(f"provider '{provider}' does not support {media_kind}")

    payload_identity = "\0".join(
        (
            plan.artifact_id,
            plan.content_hash,
            shot.shot_id,
            provider,
            media_kind,
        )
    )
    payload_token = hashlib.sha256(
        payload_identity.encode("utf-8")
    ).hexdigest()[:20]
    # Keep the durable id deterministic but short enough for deep Windows
    # workspaces. The full identity remains inside the payload document.
    payload_id = (
        f"media-shot-payload-{payload_token}-"
        f"{_safe_id(shot.shot_id)}-{media_kind}"
    )
    planned_duration_seconds = float(shot.duration_seconds)
    provider_duration_seconds = planned_duration_seconds
    adapted_prompt = shot.prompt
    if media_kind == "video":
        limits = entry.get("limits") or {}
        minimum_duration = float(
            limits.get("min_duration_seconds") or planned_duration_seconds
        )
        maximum_duration = float(
            limits.get("max_duration_seconds") or max(
                planned_duration_seconds,
                minimum_duration,
            )
        )
        if planned_duration_seconds > maximum_duration:
            raise ValueError(
                "planned shot duration exceeds the video provider maximum; "
                "split the shot before submission"
            )
        provider_duration_seconds = min(
            maximum_duration,
            max(minimum_duration, math.ceil(planned_duration_seconds)),
        )
        if provider_duration_seconds > planned_duration_seconds:
            planned_label = f"{planned_duration_seconds:g}"
            adapted_prompt = (
                f"{shot.prompt}"
                f"请确保核心动作在前{planned_label}秒内完成，"
                "后续画面保持自然运动和连续性，禁止变成静态定格。"
            )

    storyboard = [
        {
            "shot": shot.shot_id,
            "duration": f"{provider_duration_seconds:g}s",
            "description": adapted_prompt,
            "caption": "",
            "input_materials": list(shot.input_materials),
        }
    ]
    request: dict[str, Any] = {
        "prompt": adapted_prompt,
        "base_prompt": shot.prompt,
        "aspect_ratio": plan.aspect_ratio,
        "duration_seconds": shot.duration_seconds,
        "planned_duration_seconds": planned_duration_seconds,
        "provider_duration_seconds": provider_duration_seconds,
        "trim_to_seconds": planned_duration_seconds,
        "storyboard": storyboard if media_kind == "video" else [],
        "text_to_render": [],
        "reference_assets": [],
        "prompt_adapter": {
            "source": "media_execution_plan",
            "source_prompt": shot.prompt,
            "adapted_prompt": adapted_prompt,
            "aspect_ratio": plan.aspect_ratio,
            "duration_seconds": provider_duration_seconds,
        },
    }
    if media_kind == "image":
        continuity = _continuity_reference(product_root, plan, shot)
        if continuity:
            request["image"] = continuity["data_url"]
            request["continuity_reference"] = {
                "shot_id": continuity["shot_id"],
                "content_hash": continuity["content_hash"],
            }
            request["reference_assets"] = [
                {
                    "role": "character_continuity_reference",
                    "shot_id": continuity["shot_id"],
                    "content_hash": continuity["content_hash"],
                }
            ]
    if media_kind == "video" and entry.get("adapter") == "async-video-task":
        request["provider_request_draft"] = {
            "api_family": "async-video-task",
            "method": "POST",
            "endpoint": str(entry.get("endpoint") or ""),
            "body": {
                "model": str(entry.get("model") or ""),
                "content": [{"type": "text", "text": adapted_prompt}],
                "generate_audio": bool(
                    (entry.get("request_defaults") or {}).get(
                        "generate_audio",
                        True,
                    )
                ),
                "ratio": plan.aspect_ratio,
                "duration": int(provider_duration_seconds),
                "watermark": bool(
                    (entry.get("request_defaults") or {}).get(
                        "watermark",
                        False,
                    )
                ),
            },
            "unresolved_reference_assets": [],
            "body_ready_for_live": True,
        }

    payload = {
        "schema_version": PROVIDER_PAYLOAD_SCHEMA_VERSION,
        "payload_id": payload_id,
        "product_id": product_root.name,
        "created_at": now_iso(),
        "mode": "dry_run",
        "external_call_performed": False,
        "provider": entry.get("name", provider),
        "brief_type": media_kind,
        "source_brief_id": shot.shot_id,
        "source_brief_path": "",
        "source_media_plan_id": plan.artifact_id,
        "source_media_plan_hash": plan.content_hash,
        "source_shot_id": shot.shot_id,
        "shot_idempotency_key": shot.idempotency_key,
        "target": {
            "media_role": "background_scene_only",
            "canvas": list(plan.canvas),
            "fps": plan.fps,
        },
        "request": request,
        "execution_contract": {
            "execute_supported": bool(entry.get("execute_supported")),
            "requires_human_review_before_execution": True,
            "product_plate_excluded": True,
            "deterministic_text_excluded": True,
            "next_step": "Validate authorization and submit one media shot.",
        },
    }
    path = product_root / "artifacts" / "provider_payloads" / f"{payload_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)
    return {
        "success": True,
        "product_id": product_root.name,
        "payload_id": payload_id,
        "provider": payload["provider"],
        "media_kind": media_kind,
        "external_call_performed": False,
        "files": {"json": str(path)},
        "payload": payload,
    }


def _fixture_image(
    product_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    target = payload.get("target") or {}
    canvas = target.get("canvas") or [1080, 1920]
    width, height = int(canvas[0]), int(canvas[1])
    output_dir = product_root / "artifacts" / "media_shot_sources"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{payload['payload_id']}.png"
    if not output.exists():
        seed = int(
            hashlib.sha256(
                str((payload.get("request") or {}).get("prompt") or "").encode(
                    "utf-8"
                )
            ).hexdigest()[:6],
            16,
        )
        base_color = (
            48 + seed % 80,
            72 + (seed >> 8) % 96,
            96 + (seed >> 16) % 96,
        )
        image = Image.new("RGB", (width, height), base_color)
        draw = ImageDraw.Draw(image)
        draw.ellipse(
            (
                width * 0.08,
                height * 0.12,
                width * 0.62,
                height * 0.48,
            ),
            fill=(min(255, base_color[0] + 45), base_color[1], base_color[2]),
        )
        draw.rectangle(
            (
                width * 0.38,
                height * 0.52,
                width * 0.95,
                height * 0.92,
            ),
            fill=(base_color[0], min(255, base_color[1] + 50), base_color[2]),
        )
        image.save(output, format="PNG")
    return {
        "source_media": str(output.relative_to(product_root)),
        "content_hash": _hash_file(output),
        "duration_seconds": 0,
    }


def submit_media_shot(
    product_id: str,
    payload_id: str,
    provider: str,
    mode: str,
    execution_policy_id: str = "",
) -> Dict[str, Any]:
    """Submit one shot through the existing Provider execution infrastructure."""

    product_root = ensure_product(product_id)
    payload_path = (
        product_root
        / "artifacts"
        / "provider_payloads"
        / f"{payload_id}.json"
    )
    payload = read_json(payload_path, {})
    if not payload:
        raise FileNotFoundError(f"media shot payload '{payload_id}' does not exist")
    if payload.get("provider") != provider:
        raise ValueError("media shot provider does not match its prepared payload")
    if payload.get("source_media_plan_id") == "":
        raise ValueError("payload is not a media shot payload")

    if provider == "local-fixture":
        if mode not in {"fixture", "mock"}:
            raise ValueError("local-fixture supports fixture or mock mode")
        if payload.get("brief_type") != "image":
            raise ValueError("local fixture video is produced by the media compositor")
        result = _fixture_image(product_root, payload)
        record = {
            "schema_version": "product_creative.media_shot_source.v1",
            "payload_id": payload_id,
            "product_id": product_root.name,
            "provider": provider,
            "media_kind": payload.get("brief_type"),
            "created_at": now_iso(),
            "external_call_performed": False,
            "provider_task_id": "",
            "idempotency_key": payload.get("shot_idempotency_key", ""),
            **result,
        }
        record_path = (
            product_root
            / "artifacts"
            / "media_shot_sources"
            / f"{payload_id}.json"
        )
        write_json(record_path, record)
        return {"success": True, **record, "files": {"json": str(record_path)}}

    from .provider_generation import create_generation_job

    return create_generation_job(
        product_root.name,
        payload_id,
        provider,
        mode,
        execution_policy_id,
    )
