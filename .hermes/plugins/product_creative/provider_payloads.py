"""Provider payload artifact construction for Product Creative."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from .common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from .provider_adapters import image_request as _image_request, video_request as _video_request
from .provider_contracts import PROVIDER_PAYLOAD_SCHEMA_VERSION
from .provider_paths import resolve_brief_path as _resolve_brief_path
from .provider_registry import provider_entry as _provider_entry


__all__ = [
    "compile_video_request_from_production_bible",
    "prepare_provider_payload",
]


def compile_video_request_from_production_bible(
    request: Dict[str, Any],
    production_bible: Dict[str, Any],
) -> Dict[str, Any]:
    """Compile a provider-neutral request from approved shot-level production data."""

    compiled = deepcopy(request)
    specification = (
        production_bible.get("specification")
        if isinstance(production_bible.get("specification"), dict)
        else {}
    )
    shots = [
        item
        for item in production_bible.get("shots") or []
        if isinstance(item, dict)
    ]
    if len(shots) < 2:
        raise ValueError("Production Bible must contain at least two executable shots")
    prompt_lines = [
        "严格按以下 Production Bible 制作视频；不得从用户原话自由扩写产品事实。",
        f"整体风格：{specification.get('style') or '按分镜保持统一'}。",
        f"画幅：{specification.get('aspect_ratio') or '9:16'}；"
        f"总时长：{specification.get('duration_seconds') or 10} 秒。",
        f"声音：{specification.get('audio') or '按逐镜头叙事节奏设计'}。",
        f"包装策略：{production_bible.get('packaging_strategy') or '遵守素材角色定义'}。",
    ]
    storyboard = []
    for index, shot in enumerate(shots, start=1):
        characters = "、".join(str(item) for item in shot.get("characters") or []) or "无固定人物"
        caption = str(shot.get("caption") or "")
        prompt_lines.append(
            f"镜头{index}（{shot.get('duration_seconds')}秒，{shot.get('narrative_function')}）："
            f"场景={shot.get('scene')}；构图={shot.get('composition')}；"
            f"动作={shot.get('action')}；角色={characters}；"
            f"字幕={caption or '无'}。"
        )
        storyboard.append(
            {
                "shot": str(shot.get("shot_id") or f"shot-{index:02d}"),
                "duration": f"{shot.get('duration_seconds')}s",
                "description": str(shot.get("action") or ""),
                "caption": caption,
                "composition": str(shot.get("composition") or ""),
                "scene": str(shot.get("scene") or ""),
                "characters": list(shot.get("characters") or []),
                "input_materials": list(shot.get("input_materials") or []),
                "narrative_function": str(shot.get("narrative_function") or ""),
            }
        )
    continuity = [
        str(item)
        for item in production_bible.get("continuity_rules") or []
        if str(item).strip()
    ]
    if continuity:
        prompt_lines.append("连续性与保真规则：" + "；".join(continuity) + "。")
    prompt = "\n".join(prompt_lines)
    compiled.update(
        {
            "prompt": prompt,
            "base_prompt": prompt,
            "aspect_ratio": str(specification.get("aspect_ratio") or "9:16"),
            "estimated_duration": f"{specification.get('duration_seconds') or 10} seconds",
            "duration_seconds": int(specification.get("duration_seconds") or 10),
            "audio_plan": [str(specification.get("audio") or "")],
            "storyboard": storyboard,
            "must_preserve": continuity,
            "compiled_from": "production_bible",
            "source_production_bible_id": str(
                production_bible.get("artifact_id") or ""
            ),
            "source_production_bible_hash": str(
                production_bible.get("content_hash") or ""
            ),
        }
    )
    adapter = (
        deepcopy(compiled.get("prompt_adapter"))
        if isinstance(compiled.get("prompt_adapter"), dict)
        else {}
    )
    adapter.update(
        {
            "source": "production_bible",
            "source_prompt": prompt,
            "adapted_prompt": prompt,
            "aspect_ratio": compiled["aspect_ratio"],
            "duration_seconds": compiled["duration_seconds"],
        }
    )
    compiled["prompt_adapter"] = adapter
    draft = (
        deepcopy(compiled.get("provider_request_draft"))
        if isinstance(compiled.get("provider_request_draft"), dict)
        else {}
    )
    if draft:
        body = (
            deepcopy(draft.get("body"))
            if isinstance(draft.get("body"), dict)
            else {}
        )
        content = [
            deepcopy(item)
            for item in body.get("content") or []
            if isinstance(item, dict) and item.get("type") != "text"
        ]
        body["content"] = [{"type": "text", "text": prompt}, *content]
        body["ratio"] = compiled["aspect_ratio"]
        body["duration"] = compiled["duration_seconds"]
        draft["body"] = body
        compiled["provider_request_draft"] = draft
    return compiled


def _payload_markdown(payload: Dict[str, Any]) -> str:
    request = payload["request"]
    lines = [
        f"# {payload['payload_id']}",
        "",
        f"Provider: {payload['provider']}",
        f"Mode: {payload['mode']}",
        f"External call performed: {payload['external_call_performed']}",
        f"Brief: {payload['source_brief_id']}",
        f"Type: {payload['brief_type']}",
        f"Aspect ratio: {request.get('aspect_ratio')}",
        "",
        "## Prompt",
        "",
        request.get("prompt") or "",
        "",
    ]
    if payload["brief_type"] == "image":
        lines.extend(["## Text To Render", ""])
        for item in request.get("text_to_render") or []:
            lines.append(f"- {item}")
        lines.append("")
    else:
        lines.extend(["## Storyboard", "", "| Shot | Duration | Description | Caption |", "| --- | --- | --- | --- |"])
        for shot in request.get("storyboard") or []:
            lines.append(
                f"| {shot.get('shot')} | {shot.get('duration')} | {shot.get('description')} | {shot.get('caption')} |"
            )
        lines.append("")

    assets = request.get("reference_assets") or []
    if assets:
        lines.extend(["## Reference Assets", ""])
        for item in assets:
            marker = "missing" if item.get("missing") else "ready"
            lines.append(f"- {item.get('asset_id')}: {item.get('role')} ({marker}) {item.get('source')}")
        lines.append("")
    draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
    if draft:
        body = draft.get("body") if isinstance(draft.get("body"), dict) else {}
        lines.extend(
            [
                "## Provider Request Draft",
                "",
                f"- API family: {draft.get('api_family', '')}",
                f"- Method: {draft.get('method', '')}",
                f"- Endpoint: {draft.get('endpoint', '')}",
                f"- Model: {body.get('model', '')}",
                f"- Ratio: {body.get('ratio', '')}",
                f"- Duration: {body.get('duration', '')}",
                f"- Generate audio: {body.get('generate_audio', False)}",
                f"- Body ready for live: {draft.get('body_ready_for_live', False)}",
                "",
                "### Unresolved Reference Assets",
                "",
            ]
        )
        unresolved = draft.get("unresolved_reference_assets") or []
        lines.extend([f"- {item.get('asset_id')}: {item.get('local_reference')}" for item in unresolved] or ["- None"])
        lines.append("")
    return "\n".join(lines)


def prepare_provider_payload(
    product_id: str,
    brief: str,
    provider: str = "generic",
    brief_type: str = "image",
    production_bible: str = "",
) -> Dict[str, Any]:
    if brief_type not in {"image", "video"}:
        raise ValueError("brief_type must be image or video")

    base = ensure_product(product_id)
    brief_path = _resolve_brief_path(base, brief)
    brief_payload = read_json(brief_path, {})
    actual_type = brief_payload.get("brief_type")
    if actual_type != brief_type:
        raise ValueError(f"expected {brief_type} brief, got {actual_type or 'unknown'}")
    entry = _provider_entry(provider)
    product_state = read_product_state(base)

    payload_id = f"provider-payload-{timestamp()}-{brief_type}"
    request = _image_request(brief_payload, entry, product_state) if brief_type == "image" else _video_request(brief_payload, entry, product_state)
    bible_payload: Dict[str, Any] = {}
    if brief_type == "video" and production_bible:
        from .runtime.professional_artifacts import load_professional_artifact

        bible = load_professional_artifact(base.name, production_bible)
        if bible.schema_name != "product_creative.production_bible.v1":
            raise ValueError("video provider payload requires a Production Bible artifact")
        bible_payload = bible.model_dump(mode="json")
        request = compile_video_request_from_production_bible(request, bible_payload)
    payload = {
        "schema_version": PROVIDER_PAYLOAD_SCHEMA_VERSION,
        "payload_id": payload_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "mode": "dry_run",
        "external_call_performed": False,
        "provider": entry.get("name", provider or "generic"),
        "brief_type": brief_type,
        "source_brief_id": brief_payload.get("brief_id", brief_path.stem),
        "source_brief_path": str(brief_path.relative_to(base)),
        "source_production_bible_id": str(bible_payload.get("artifact_id") or ""),
        "source_production_bible_hash": str(bible_payload.get("content_hash") or ""),
        "compiled_from": "production_bible" if bible_payload else "legacy_brief",
        "target": brief_payload.get("target", {}),
        "request": request,
        "execution_contract": {
            "execute_supported": bool(entry.get("execute_supported")),
            "requires_human_review_before_execution": True,
            "adapter_status": entry.get("adapter_contract", {}).get("execute", "boundary_defined"),
            "next_step": "Validate readiness before external execution.",
        },
    }

    out_dir = base / "artifacts" / "provider_payloads"
    json_path = out_dir / f"{payload_id}.json"
    md_path = out_dir / f"{payload_id}.md"
    write_json(json_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_payload_markdown(payload), encoding="utf-8")
    append_jsonl(
        base / "structured" / "provider_payload_index.jsonl",
        {
            "payload_id": payload_id,
            "created_at": payload["created_at"],
            "provider": payload["provider"],
            "brief_type": brief_type,
            "source_brief_id": payload["source_brief_id"],
            "mode": payload["mode"],
        },
    )
    update_index_and_log(
        base,
        "provider-payload",
        payload_id,
        [
            f"Provider: {payload['provider']}",
            f"Mode: {payload['mode']}",
            f"Source brief: {brief_path.relative_to(base)}",
        ],
    )
    return {
        "success": True,
        "product_id": base.name,
        "payload_id": payload_id,
        "provider": payload["provider"],
        "mode": payload["mode"],
        "external_call_performed": False,
        "brief_type": brief_type,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "payload": payload,
    }


