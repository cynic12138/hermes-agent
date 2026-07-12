"""Image capability service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ..content.brief_export_service import export_briefs
from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ..content.generation_service import generate_product
from ...providers import check_live_readiness, create_generation_job, prepare_provider_payload, validate_provider_payload

from .shared import _list, _rel, _resolve_json_artifact, _text
from .intent_service import IMAGE_INTENT_SCHEMA_VERSION

IMAGE_BRIEF_REVIEW_SCHEMA_VERSION = "product_creative.image_brief_review.v4.2"

IMAGE_BRIEF_PATCH_SCHEMA_VERSION = "product_creative.image_brief_patch.v4.2"

def _resolve_image_intent(base: Path, intent: str) -> Dict[str, Any]:
    path = _resolve_json_artifact(base, intent, "image_intents", "intent_id")
    payload = read_json(path, {})
    if payload.get("schema_version") != IMAGE_INTENT_SCHEMA_VERSION:
        raise ValueError("image intent schema is not supported")
    payload["_path"] = _rel(base, path)
    return payload

def _intent_scene(message: str, variant: int) -> str:
    matches = re.findall(r"(?:^|[；;])\s*([1-5])(?:[.、：:]|\s)+([^；;]+)", message)
    scenes = {int(index): scene.strip().rstrip("。") for index, scene in matches}
    return scenes.get(variant, "")

def _apply_image_intent_to_brief(brief: Dict[str, Any], image_intent: Dict[str, Any]) -> Dict[str, Any]:
    message = _text(image_intent.get("message"))
    variant = int(brief.get("source_variant") or 1)
    scene = _intent_scene(message, variant)
    style = _text((brief.get("visual") or {}).get("style")) or _text(image_intent.get("style_direction"))
    prompt = (
        f"为{_text((brief.get('product') or {}).get('name')) or image_intent.get('product_id')}创作妇女节商业摄影视觉。"
        f"本次用户创意要求：{message} "
        f"第{variant}张重点场景：{scene or '在完整创意要求内做有区别的构图'}。"
        f"风格：{style or '现代、真实、克制、温暖'}。"
        "必须以已登记产品参考图为包装依据，保留黄色半透明云朵/花朵外形与品牌识别；"
        "产品仅作为未打开的桌面礼物或场景元素，不展示使用。"
        "成年孕妇必须被尊重地呈现为有主体性的成年女性，不病态化、不幼态化。"
        "画面不要生成广告文案或新增包装文字；不得暗示医疗、通便、营养、孕期适用或安全功效。"
    )
    target = dict(brief.get("target") or {})
    if any(marker in message for marker in ("竖版", "竖屏", "9:16")):
        target.update({
            "default_aspect_ratio": "9:16",
            "canvas_hint": "vertical social image",
            "text_policy": "no added overlay text; preserve only reference packaging identity",
        })
    copy = dict(brief.get("copy") or {})
    copy.update({
        "headline": "每一种女性身份，都值得被看见",
        "subheadline": "妇女节主题视觉候选",
        "supporting_labels": [],
        "text_to_render": [],
    })
    visual = dict(brief.get("visual") or {})
    visual.update({
        "style": style or "现代、真实、克制、温暖",
        "composition": scene or "妇女节女性群像与产品礼物静物的竖版商业摄影构图",
        "prompt": prompt,
        "negative_constraints": [
            "no product use or opened applicator",
            "no medical, bowel, nutrition, pregnancy suitability or safety claims",
            "no invented packaging text, certification or ingredients",
            "no infantilized or distressed depiction of the adult pregnant woman",
        ],
    })
    contract = dict(brief.get("generation_contract") or {})
    contract.update({
        "prompt": prompt,
        "must_preserve": [
            "registered yellow translucent cloud/flower product packaging identity",
            "adult pregnant woman portrayed respectfully",
            "Women’s Day theme: every female identity deserves to be seen",
        ],
        "must_not_invent": [
            "product use",
            "medical or functional claims",
            "pregnancy suitability or safety claims",
            "ingredients, certification or packaging text not visible in the reference",
        ],
        "requires_human_review": True,
    })
    brief["target"] = target
    brief["copy"] = copy
    brief["visual"] = visual
    brief["generation_contract"] = contract
    brief["creative_brief"] = {
        "source": "image_intent",
        "message": message,
        "variant_direction": scene,
        "not_product_fact": True,
    }
    return brief

def create_image_brief_from_intent(product_id: str, intent: str, artifact: str = "", variant: int | None = None) -> Dict[str, Any]:
    base = ensure_product(product_id)
    image_intent = _resolve_image_intent(base, intent)
    count = max(1, min(int(image_intent.get("count_limit") or 1), 5))
    artifact_id = _text(artifact)
    generated = {}
    if not artifact_id:
        generated = generate_product(base.name, "product-copy-pack", count)
        artifact_id = _text(generated.get("artifact_id") or generated.get("artifact_json"))
    selected_variant = variant
    if selected_variant is None and count == 1:
        selected_variant = 1
    brief_result = export_briefs(base.name, artifact_id, selected_variant, "image", _text(image_intent.get("preset")) or "taobao-main-image", [])
    brief_files = [item for item in brief_result.get("files", []) if item.get("brief_type") == "image"]
    updated_briefs: List[Dict[str, Any]] = []
    for item in brief_files:
        path = Path(item["json"])
        brief = read_json(path, {})
        brief = _apply_image_intent_to_brief(brief, image_intent)
        brief["status"] = "draft"
        brief["source_image_intent_id"] = image_intent.get("intent_id")
        brief["source_image_intent_path"] = image_intent.get("_path", "")
        brief["m4_contract"] = {
            "version": "M4.1-M4.3",
            "requires_human_review_before_live": True,
            "batch_policy_allowed": True,
        }
        write_json(path, brief)
        md_path = path.with_suffix(".md")
        md_path.write_text(
            _brief_markdown(brief) + f"\n## M4 Status\n\n- Status: draft\n- Image intent: {image_intent.get('intent_id')}\n",
            encoding="utf-8",
        )
        updated_briefs.append(brief)
    append_jsonl(
        base / "structured" / "image_brief_index.jsonl",
        {
            "created_at": now_iso(),
            "source_image_intent_id": image_intent.get("intent_id"),
            "artifact_id": artifact_id,
            "brief_ids": [item.get("brief_id") for item in updated_briefs],
        },
    )
    update_index_and_log(base, "image-brief", image_intent.get("intent_id", ""), [f"Briefs: {len(updated_briefs)}"])
    return {
        "success": True,
        "schema_version": "product_creative.image_brief_from_intent.v4.1",
        "product_id": base.name,
        "intent_id": image_intent.get("intent_id"),
        "artifact_id": artifact_id,
        "generated_artifact": generated,
        "count": len(updated_briefs),
        "files": brief_files,
        "briefs": updated_briefs,
    }

def _resolve_image_brief(base: Path, brief: str) -> tuple[Path, Dict[str, Any]]:
    path = _resolve_json_artifact(base, brief, "image_briefs", "brief_id")
    payload = read_json(path, {})
    if payload.get("brief_type") != "image":
        raise ValueError("expected an image brief")
    return path, payload

def _brief_review_markdown(review: Dict[str, Any]) -> str:
    summary = review.get("brief_summary") or {}
    lines = [
        f"# {review['review_id']}",
        "",
        f"Product: {review['product_id']}",
        f"Brief: {review['source_brief_id']}",
        f"Status: {review['status']}",
        "",
        "## Copy",
        "",
        f"- Headline: {summary.get('headline', '')}",
        f"- Subheadline: {summary.get('subheadline', '')}",
        "",
        "## Prompt",
        "",
        summary.get("prompt", ""),
        "",
        "## Review Checklist",
        "",
    ]
    lines.extend([f"- [ ] {item}" for item in review.get("review_checklist", [])])
    lines.append("")
    return "\n".join(lines)

def create_image_brief_review_package(product_id: str, brief: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    brief_path, brief_payload = _resolve_image_brief(base, brief)
    review_id = f"image-brief-review-{timestamp()}"
    patch_id = f"image-brief-patch-{timestamp()}"
    review = {
        "schema_version": IMAGE_BRIEF_REVIEW_SCHEMA_VERSION,
        "review_id": review_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_human_review",
        "source_brief_id": brief_payload.get("brief_id"),
        "source_brief_path": _rel(base, brief_path),
        "source_image_intent_id": _text(brief_payload.get("source_image_intent_id")),
        "brief_summary": {
            "headline": _text((brief_payload.get("copy") or {}).get("headline")),
            "subheadline": _text((brief_payload.get("copy") or {}).get("subheadline")),
            "text_to_render": _list((brief_payload.get("copy") or {}).get("text_to_render")),
            "prompt": _text((brief_payload.get("generation_contract") or {}).get("prompt")),
            "source_material_pack": brief_payload.get("source_material_pack") or {},
        },
        "patch_id": patch_id,
        "review_checklist": [
            "Confirm product facts and no unverified claims.",
            "Confirm source material grounding is acceptable.",
            "Confirm text overlay is short enough for the image.",
            "Confirm live generation can use this brief or a batch generation policy.",
        ],
        "requires_human_confirmation": True,
        "mutates_product_brain": False,
    }
    patch = {
        "schema_version": IMAGE_BRIEF_PATCH_SCHEMA_VERSION,
        "patch_id": patch_id,
        "product_id": base.name,
        "created_at": review["created_at"],
        "status": "draft_patch",
        "source_brief_id": brief_payload.get("brief_id"),
        "source_brief_path": _rel(base, brief_path),
        "copy": brief_payload.get("copy") or {},
        "visual": brief_payload.get("visual") or {},
        "generation_contract": brief_payload.get("generation_contract") or {},
        "note": "",
        "confirmed": False,
    }
    brief_payload["status"] = "ready_for_human_review"
    brief_payload["latest_image_brief_review_id"] = review_id
    brief_payload["latest_image_brief_patch_id"] = patch_id
    write_json(brief_path, brief_payload)

    review_dir = base / "artifacts" / "image_brief_reviews"
    patch_dir = base / "artifacts" / "image_brief_patches"
    review_json = review_dir / f"{review_id}.json"
    review_md = review_dir / f"{review_id}.md"
    patch_json = patch_dir / f"{patch_id}.json"
    patch_md = patch_dir / f"{patch_id}.md"
    write_json(review_json, review)
    review_md.parent.mkdir(parents=True, exist_ok=True)
    review_md.write_text(_brief_review_markdown(review), encoding="utf-8")
    write_json(patch_json, patch)
    patch_md.parent.mkdir(parents=True, exist_ok=True)
    patch_md.write_text(f"# {patch_id}\n\nEdit the JSON patch, then confirm it with image-brief-revise.\n", encoding="utf-8")
    append_jsonl(
        base / "structured" / "image_brief_review_index.jsonl",
        {
            "review_id": review_id,
            "created_at": review["created_at"],
            "source_brief_id": brief_payload.get("brief_id"),
            "patch_id": patch_id,
            "path": _rel(base, review_json),
        },
    )
    update_index_and_log(base, "image-brief-review", review_id, [f"Brief: {brief_payload.get('brief_id')}"])
    return {
        "success": True,
        "schema_version": IMAGE_BRIEF_REVIEW_SCHEMA_VERSION,
        "product_id": base.name,
        "review_id": review_id,
        "patch_id": patch_id,
        "files": {"json": str(review_json), "markdown": str(review_md), "patch_json": str(patch_json), "patch_markdown": str(patch_md)},
        "review": review,
        "patch": patch,
    }

def _resolve_image_brief_patch(base: Path, patch: str) -> tuple[Path, Dict[str, Any]]:
    path = _resolve_json_artifact(base, patch, "image_brief_patches", "patch_id")
    payload = read_json(path, {})
    if payload.get("schema_version") != IMAGE_BRIEF_PATCH_SCHEMA_VERSION:
        raise ValueError("image brief patch schema is not supported")
    return path, payload

def _brief_markdown(brief: Dict[str, Any]) -> str:
    lines = [
        f"# {brief['brief_id']}",
        "",
        f"Status: {brief.get('status', '')}",
        f"Product: {brief['product_id']}",
        f"Source brief: {brief.get('source_brief_id', '')}",
        "",
        "## Copy",
        "",
        f"- Headline: {(brief.get('copy') or {}).get('headline', '')}",
        f"- Subheadline: {(brief.get('copy') or {}).get('subheadline', '')}",
        "",
        "## Prompt",
        "",
        (brief.get("generation_contract") or {}).get("prompt", ""),
        "",
    ]
    return "\n".join(lines)

def revise_image_brief(product_id: str, brief: str, patch: str = "", note: str = "", confirmed: bool = False) -> Dict[str, Any]:
    base = ensure_product(product_id)
    brief_path, source_brief = _resolve_image_brief(base, brief)
    patch_payload: Dict[str, Any] = {}
    patch_path: Path | None = None
    if _text(patch):
        patch_path, patch_payload = _resolve_image_brief_patch(base, patch)
    revised = dict(source_brief)
    revised["brief_id"] = f"image-brief-{timestamp()}-confirmed"
    revised["created_at"] = now_iso()
    revised["source_brief_id"] = source_brief.get("brief_id")
    revised["source_brief_path"] = _rel(base, brief_path)
    revised["source_patch_id"] = patch_payload.get("patch_id", "")
    revised["source_patch_path"] = _rel(base, patch_path) if patch_path else ""
    revised["review_note"] = _text(note) or _text(patch_payload.get("note"))
    revised["status"] = "confirmed_for_provider_payload" if confirmed else "revision_requested"
    revised["confirmed_at"] = now_iso() if confirmed else ""
    if patch_payload:
        for field in ["copy", "visual", "generation_contract"]:
            if isinstance(patch_payload.get(field), dict):
                revised[field] = patch_payload[field]
        patch_payload["status"] = "confirmed" if confirmed else "revision_requested"
        patch_payload["confirmed"] = bool(confirmed)
        patch_payload["confirmed_at"] = revised["confirmed_at"]
        write_json(patch_path, patch_payload)
    out_dir = base / "artifacts" / "image_briefs"
    json_path = out_dir / f"{revised['brief_id']}.json"
    md_path = out_dir / f"{revised['brief_id']}.md"
    write_json(json_path, revised)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_brief_markdown(revised), encoding="utf-8")
    append_jsonl(
        base / "structured" / "image_brief_revision_index.jsonl",
        {
            "brief_id": revised["brief_id"],
            "created_at": revised["created_at"],
            "source_brief_id": source_brief.get("brief_id"),
            "source_patch_id": revised["source_patch_id"],
            "status": revised["status"],
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "image-brief-revise", revised["brief_id"], [f"Status: {revised['status']}"])
    return {
        "success": True,
        "schema_version": "product_creative.image_brief_revise.v4.2",
        "product_id": base.name,
        "brief_id": revised["brief_id"],
        "status": revised["status"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "brief": revised,
    }
