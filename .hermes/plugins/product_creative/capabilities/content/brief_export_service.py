"""M0.4 provider-agnostic image/video brief export."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import (
    append_jsonl,
    ensure_product,
    now_iso,
    product_state_path,
    read_json,
    read_product_state,
    timestamp,
    today,
    update_index_and_log,
    write_json,
)
from ..material.pack_service import material_source_assets_from_pack, prepare_task_material_pack, record_material_usage


IMAGE_SCHEMA_VERSION = "product_creative.image_brief.v0.4.1"
VIDEO_SCHEMA_VERSION = "product_creative.video_brief.v0.4.1"

PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "default": {
        "image": {
            "channel": "ecommerce",
            "asset_type": "main_image",
            "default_aspect_ratio": "1:1",
            "canvas_hint": "square commerce image",
            "text_policy": "short headline, subheadline, and compact selling-point labels",
        },
        "video": {
            "channel": "short_video",
            "asset_type": "storyboard",
            "default_aspect_ratio": "9:16",
            "canvas_hint": "vertical short video",
            "text_policy": "one caption per shot",
        },
    },
    "taobao-main-image": {
        "image": {
            "channel": "taobao",
            "asset_type": "main_image",
            "default_aspect_ratio": "1:1",
            "canvas_hint": "square ecommerce main image",
            "text_policy": "large product-first headline plus 2-3 short labels",
        },
        "video": {
            "channel": "taobao",
            "asset_type": "product_video_storyboard",
            "default_aspect_ratio": "9:16",
            "canvas_hint": "vertical commerce product video",
            "text_policy": "clear caption per shot, no unverified claims",
        },
    },
    "douyin-9x16": {
        "image": {
            "channel": "douyin",
            "asset_type": "cover",
            "default_aspect_ratio": "9:16",
            "canvas_hint": "vertical short-video cover",
            "text_policy": "strong hook headline with minimal support text",
        },
        "video": {
            "channel": "douyin",
            "asset_type": "short_video_storyboard",
            "default_aspect_ratio": "9:16",
            "canvas_hint": "vertical short video",
            "text_policy": "hook-first captions, one key message per shot",
        },
    },
    "xiaohongshu-cover": {
        "image": {
            "channel": "xiaohongshu",
            "asset_type": "cover",
            "default_aspect_ratio": "3:4",
            "canvas_hint": "portrait note cover",
            "text_policy": "natural recommendation headline with concise labels",
        },
        "video": {
            "channel": "xiaohongshu",
            "asset_type": "video_note_storyboard",
            "default_aspect_ratio": "9:16",
            "canvas_hint": "vertical video note",
            "text_policy": "experience-led captions, no hard-sell tone",
        },
    },
}


def _resolve_copy_artifact_path(base: Path, artifact: str) -> Path:
    if not artifact:
        raise ValueError("artifact id or path is required")
    candidate = Path(artifact)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("artifact path must stay inside the product workspace")
        return resolved

    name = artifact if artifact.endswith(".json") else f"{artifact}.json"
    path = base / "artifacts" / "copy" / name
    if path.exists():
        return path.resolve()
    raise FileNotFoundError(f"artifact '{artifact}' does not exist")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _preset_target(preset: str, brief_type: str) -> Dict[str, Any]:
    presets = PRESETS.get(preset)
    if not presets:
        raise ValueError(f"preset must be one of: {', '.join(sorted(PRESETS))}")
    target = dict(presets[brief_type])
    target["preset"] = preset
    target["provider_agnostic"] = True
    return target


def _source_assets(state: Dict[str, Any], assets: List[str] | None) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for item in _list(state.get("assets", {}).get("materials")):
        if not isinstance(item, dict):
            continue
        entries.append(
            {
                "asset_id": _text(item.get("material_id")) or f"material-{len(entries) + 1}",
                "role": _text(item.get("role")) or "product_image",
                "source": _text(item.get("source")),
                "stored": _text(item.get("stored")),
                "missing": False,
                "description": _text(item.get("description")) or "Registered material asset from Product Material Library.",
            }
        )

    for idx, item in enumerate(_list(state.get("assets", {}).get("images")), 1):
        if not isinstance(item, dict):
            continue
        entries.append(
            {
                "asset_id": f"state-image-{idx}",
                "role": "product_image",
                "source": _text(item.get("source")),
                "stored": _text(item.get("stored")),
                "missing": bool(item.get("missing")),
                "description": "Product image captured during ingest.",
            }
        )

    for idx, item in enumerate(assets or [], 1):
        value = _text(item)
        if not value:
            continue
        path = Path(value)
        exists = path.exists()
        entries.append(
            {
                "asset_id": f"manual-reference-{idx}",
                "role": "reference_asset",
                "source": str(path.resolve()) if exists else value,
                "stored": "",
                "missing": not exists,
                "description": "Manual reference asset supplied for this brief export.",
            }
        )
    return entries


def _variant_filter(variants: List[Dict[str, Any]], variant: int | None) -> List[Dict[str, Any]]:
    if variant is None:
        return variants
    selected = [item for item in variants if int(item.get("variant") or 0) == int(variant)]
    if not selected:
        raise ValueError(f"variant {variant} does not exist in artifact")
    return selected


def _negative_constraints(prompt: str, visual_direction: str) -> List[str]:
    text = f"{prompt}。{visual_direction}"
    constraints: List[str] = []
    for chunk in re.split(r"[。；;\n]+", text):
        item = chunk.strip()
        if not item:
            continue
        if any(marker in item for marker in ["无", "不要", "禁止", "避免", "不出现"]):
            if item not in constraints:
                constraints.append(item)
    return constraints


def _estimated_duration(storyboard: List[Dict[str, Any]]) -> str:
    if not storyboard:
        return ""
    last = _text(storyboard[-1].get("duration"))
    match = re.search(r"(\d+)\s*s?$", last)
    if match:
        return f"0-{match.group(1)}s"
    return last


def _state_hash(state: Dict[str, Any]) -> str:
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _source_snapshot(state: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "product_state_hash": _state_hash(state),
        "product_state_status": state.get("status", ""),
        "sources": state.get("sources", []),
        "grounding_audit": artifact.get("grounding_audit", {}),
        "generation_method": artifact.get("generation_method", ""),
        "llm": artifact.get("llm", {}),
    }


def _brief_task(kind: str) -> str:
    return "video_brief" if kind == "video" else "image_brief"


def _brief_preset_key(kind: str) -> str:
    return "video" if kind == "video" else "image"


def _source_material_pack_summary(pack: Dict[str, Any]) -> Dict[str, Any]:
    if not pack:
        return {}
    return {
        "task_material_pack_id": _text(pack.get("task_material_pack_id")),
        "task": _text(pack.get("task")),
        "channel": _text(pack.get("channel")),
        "selected_material_ids": [
            _text(item.get("material_id"))
            for item in _list(pack.get("selected_materials"))
            if isinstance(item, dict) and _text(item.get("material_id"))
        ],
        "missing_requirements": _list(pack.get("missing_requirements")),
    }


def _video_prompt(product_name: str, style: str, storyboard: List[Dict[str, Any]]) -> str:
    lines = [
        "请基于以下分镜生成一条短视频，画面真实自然，信息清晰，不新增未经确认的产品信息。",
        f"产品：{product_name}",
        f"风格：{style or '真实、清晰、克制'}",
        "画幅：9:16",
        "分镜：",
    ]
    for shot in storyboard:
        lines.append(
            f"{shot['shot']}. {shot['duration']}｜{shot['description']}｜字幕：{shot['caption']}"
        )
    lines.append("限制：不得新增包装、认证、功效、产地细节或医学化表达。")
    return "\n".join(lines)


def _image_brief(
    base: Path,
    state: Dict[str, Any],
    artifact: Dict[str, Any],
    pack: Dict[str, Any],
    preset: str,
    source_assets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    main_copy = pack.get("ecommerce_main_image_copy") or {}
    prompt = _text(pack.get("image_generation_prompt"))
    visual_direction = _text(main_copy.get("visual_direction"))
    variant = int(pack.get("variant") or 0)
    product_name = _text(state.get("name")) or base.name
    headline = _text(main_copy.get("headline"))
    subheadline = _text(main_copy.get("subheadline"))
    labels = [str(item) for item in _list(main_copy.get("supporting_labels")) if str(item).strip()]

    return {
        "schema_version": IMAGE_SCHEMA_VERSION,
        "brief_type": "image",
        "brief_id": f"image-brief-{timestamp()}-v{variant}",
        "product_id": base.name,
        "source_artifact_id": artifact.get("artifact_id", ""),
        "source_variant": variant,
        "created_at": now_iso(),
        "target": _preset_target(preset, "image"),
        "product": {
            "name": product_name,
            "one_liner": _text(pack.get("product_one_liner")),
            "selling_points": [str(item) for item in _list(pack.get("core_selling_points")) if str(item).strip()],
        },
        "copy": {
            "headline": headline,
            "subheadline": subheadline,
            "supporting_labels": labels,
            "text_to_render": [item for item in [headline, subheadline, *labels] if item],
        },
        "visual": {
            "subject": product_name,
            "style": _text(pack.get("style")),
            "composition": visual_direction,
            "prompt": prompt,
            "negative_constraints": _negative_constraints(prompt, visual_direction),
        },
        "source_assets": source_assets,
        "generation_contract": {
            "prompt": prompt,
            "must_preserve": [product_name, *labels],
            "must_not_invent": [
                "unverified ingredients",
                "certifications",
                "packaging format",
                "medical or functional claims",
            ],
            "requires_human_review": True,
        },
        "source_snapshot": _source_snapshot(state, artifact),
    }


def _video_brief(
    base: Path,
    state: Dict[str, Any],
    artifact: Dict[str, Any],
    pack: Dict[str, Any],
    preset: str,
    source_assets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    variant = int(pack.get("variant") or 0)
    product_name = _text(state.get("name")) or base.name
    style = _text(pack.get("style"))
    storyboard = []
    for raw in _list(pack.get("short_video_storyboard")):
        shot = {
            "shot": int(raw.get("shot") or len(storyboard) + 1),
            "duration": _text(raw.get("duration")),
            "description": _text(raw.get("description")),
            "caption": _text(raw.get("caption")),
            "visual_prompt": f"{product_name}，{_text(raw.get('description'))}",
            "key_message": _text(raw.get("caption")),
        }
        storyboard.append(shot)

    return {
        "schema_version": VIDEO_SCHEMA_VERSION,
        "brief_type": "video",
        "brief_id": f"video-brief-{timestamp()}-v{variant}",
        "product_id": base.name,
        "source_artifact_id": artifact.get("artifact_id", ""),
        "source_variant": variant,
        "created_at": now_iso(),
        "target": _preset_target(preset, "video"),
        "product": {
            "name": product_name,
            "one_liner": _text(pack.get("product_one_liner")),
            "selling_points": [str(item) for item in _list(pack.get("core_selling_points")) if str(item).strip()],
        },
        "story": {
            "style": style,
            "estimated_duration": _estimated_duration(storyboard),
            "storyboard": storyboard,
        },
        "source_assets": source_assets,
        "generation_contract": {
            "prompt": _video_prompt(product_name, style, storyboard),
            "must_preserve": [product_name],
            "must_not_invent": [
                "unverified ingredients",
                "certifications",
                "packaging format",
                "medical or functional claims",
            ],
            "requires_human_review": True,
        },
        "source_snapshot": _source_snapshot(state, artifact),
    }


def _brief_markdown(brief: Dict[str, Any]) -> str:
    lines = [
        f"# {brief['brief_id']}",
        "",
        f"Type: {brief['brief_type']}",
        f"Product: {brief['product_id']}",
        f"Source artifact: {brief['source_artifact_id']}",
        f"Variant: {brief['source_variant']}",
        f"Preset: {brief['target']['preset']}",
        f"Channel: {brief['target']['channel']}",
        f"Aspect ratio: {brief['target']['default_aspect_ratio']}",
        "",
    ]
    assets = brief.get("source_assets") or []
    if assets:
        lines.extend(["## Source Assets", ""])
        for item in assets:
            marker = "missing" if item.get("missing") else "ready"
            lines.append(f"- {item.get('asset_id')}: {item.get('role')} ({marker}) {item.get('source')}")
        lines.append("")
    if brief["brief_type"] == "image":
        lines.extend(
            [
                "## Copy",
                "",
                f"- Headline: {brief['copy']['headline']}",
                f"- Subheadline: {brief['copy']['subheadline']}",
                "",
                "## Prompt",
                "",
                brief["generation_contract"]["prompt"],
                "",
            ]
        )
    else:
        lines.extend(["## Prompt", "", brief["generation_contract"]["prompt"], "", "## Storyboard", ""])
        lines.append("| Shot | Duration | Description | Caption |")
        lines.append("| --- | --- | --- | --- |")
        for shot in brief["story"]["storyboard"]:
            lines.append(
                f"| {shot['shot']} | {shot['duration']} | {shot['description']} | {shot['caption']} |"
            )
        lines.append("")
    return "\n".join(lines)


def _write_brief(base: Path, brief: Dict[str, Any]) -> Dict[str, str]:
    if brief["brief_type"] == "image":
        out_dir = base / "artifacts" / "image_briefs"
    else:
        out_dir = base / "artifacts" / "video_scripts"
    json_path = out_dir / f"{brief['brief_id']}.json"
    md_path = out_dir / f"{brief['brief_id']}.md"
    write_json(json_path, brief)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_brief_markdown(brief), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _create_brief_page(base: Path, export_id: str, outputs: List[Dict[str, Any]]) -> None:
    date = today()
    page = base / "wiki" / "experiments" / f"{date}-{export_id}.md"
    lines = "\n".join(
        f"- {item['brief_type']} v{item['source_variant']}: {item['brief_id']}" for item in outputs
    )
    page.write_text(
        f"""---
title: {export_id}
type: experiment
product_id: {base.name}
created: {date}
updated: {date}
confidence: medium
status: briefed
sources: []
---

# {export_id}

## Brief Outputs

{lines}
""",
        encoding="utf-8",
    )


def export_briefs(
    product_id: str,
    artifact: str,
    variant: int | None = None,
    kind: str = "all",
    preset: str = "default",
    assets: List[str] | None = None,
) -> Dict[str, Any]:
    if kind not in {"all", "image", "video"}:
        raise ValueError("kind must be one of: all, image, video")
    if preset not in PRESETS:
        raise ValueError(f"preset must be one of: {', '.join(sorted(PRESETS))}")
    base = ensure_product(product_id)
    artifact_path = _resolve_copy_artifact_path(base, artifact)
    artifact_payload = read_json(artifact_path, {})
    if artifact_payload.get("target") != "product-copy-pack":
        raise ValueError("M0.4 only exports briefs from product-copy-pack artifacts")

    state = read_product_state(base)
    source_assets = _source_assets(state, assets)
    task_pack: Dict[str, Any] = {}
    if not assets:
        preset_target = PRESETS.get(preset, PRESETS["default"])[_brief_preset_key(kind)]
        pack_result = prepare_task_material_pack(
            base.name,
            _brief_task(kind),
            _text(preset_target.get("channel")),
            3,
        )
        task_pack = pack_result.get("task_material_pack") if isinstance(pack_result.get("task_material_pack"), dict) else {}
        pack_assets = material_source_assets_from_pack(task_pack)
        if pack_assets:
            source_assets = pack_assets
    pack_summary = _source_material_pack_summary(task_pack)
    selected = _variant_filter(artifact_payload.get("variants", []), variant)
    export_id = f"brief-export-{timestamp()}"
    outputs: List[Dict[str, Any]] = []
    files: List[Dict[str, str]] = []

    for pack in selected:
        if kind in {"all", "image"}:
            brief = _image_brief(base, state, artifact_payload, pack, preset, source_assets)
            if pack_summary:
                brief["source_material_pack"] = pack_summary
            paths = _write_brief(base, brief)
            if pack_summary:
                record_material_usage(base.name, "image_brief", (brief.get("target") or {}).get("channel", ""), pack_summary["task_material_pack_id"], brief["brief_id"])
            outputs.append(brief)
            files.append({"brief_id": brief["brief_id"], "brief_type": "image", **paths})
        if kind in {"all", "video"}:
            brief = _video_brief(base, state, artifact_payload, pack, preset, source_assets)
            if pack_summary:
                brief["source_material_pack"] = pack_summary
            paths = _write_brief(base, brief)
            if pack_summary:
                record_material_usage(base.name, "video_brief", (brief.get("target") or {}).get("channel", ""), pack_summary["task_material_pack_id"], brief["brief_id"])
            outputs.append(brief)
            files.append({"brief_id": brief["brief_id"], "brief_type": "video", **paths})

    append_jsonl(
        base / "structured" / "brief_index.jsonl",
        {
            "export_id": export_id,
            "artifact_id": artifact_payload.get("artifact_id") or artifact_path.stem,
            "created_at": now_iso(),
            "kind": kind,
            "variant": variant,
            "preset": preset,
            "asset_count": len(source_assets),
            "task_material_pack_id": pack_summary.get("task_material_pack_id", ""),
            "outputs": [
                {
                    "brief_id": item["brief_id"],
                    "brief_type": item["brief_type"],
                    "source_variant": item["source_variant"],
                }
                for item in outputs
            ],
        },
    )
    _create_brief_page(base, export_id, outputs)
    update_index_and_log(
        base,
        "brief",
        export_id,
        [f"{len(outputs)} standardized brief(s)", f"Source: {artifact_path.relative_to(base)}"],
    )

    return {
        "success": True,
        "product_id": base.name,
        "artifact_id": artifact_payload.get("artifact_id") or artifact_path.stem,
        "export_id": export_id,
        "kind": kind,
        "variant": variant,
        "preset": preset,
        "asset_count": len(source_assets),
        "task_material_pack_id": pack_summary.get("task_material_pack_id", ""),
        "count": len(outputs),
        "files": files,
        "briefs": outputs,
    }
