"""Material visual analysis and alignment service."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...brain.provenance import register_source as _register_source
from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, slug, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import artifacts

from .shared import _list, _rel, _text
from .asset_service import _mime_type, _orientation, _read_image_size, _resolve_material

IMAGE_ANALYSIS_SCHEMA_VERSION = "product_creative.image_analysis.v2.15"

VISUAL_ALIGNMENT_SCHEMA_VERSION = "product_creative.visual_alignment.v2.16"

def _registry_path() -> Path:
    return Path(__file__).with_name("provider_registry.json")

def _load_provider(name: str) -> Dict[str, Any]:
    clean_name = _text(name) or "mock-vision"
    registry = read_json(_registry_path(), {})
    for item in _list(registry.get("providers")):
        if isinstance(item, dict) and item.get("name") == clean_name:
            return item
    if clean_name == "mock-vision":
        return {"name": "mock-vision", "status": "mock"}
    raise ValueError(f"provider '{clean_name}' is not registered")

def _provider_value(provider: Dict[str, Any], key: str, env_key: str) -> str:
    value = _text(provider.get(key))
    if value:
        return value
    env_name = _text(provider.get(env_key))
    return os.environ.get(env_name, "").strip() if env_name else ""

def _post_json(endpoint: str, body: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"VLM provider HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"VLM provider request failed: {exc.reason}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"VLM provider returned non-JSON response: {raw[:500]}") from exc

def _first_remote_image_url(material: Dict[str, Any]) -> str:
    remote_url = _text(material.get("remote_url"))
    if _is_http_url(remote_url):
        return remote_url
    for item in _list(material.get("remote_urls")):
        if isinstance(item, dict) and _is_http_url(_text(item.get("url"))):
            return _text(item.get("url"))
    return ""

def _image_input_url(stored: Path, material: Dict[str, Any]) -> Tuple[str, str]:
    remote_url = _first_remote_image_url(material)
    if remote_url:
        return remote_url, "remote_url"
    mime_type = _text(material.get("media", {}).get("mime_type")) or _mime_type(stored)
    data = base64.b64encode(stored.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}", "data_url"

def _default_vlm_prompt(product_name: str) -> str:
    return (
        "请分析这张产品主图，重点服务于后续电商主图文案、图片生成 prompt、图生视频分镜。"
        f"已知产品名或产品空间名称：{product_name}。"
        "请只输出 JSON，不要输出 Markdown。字段："
        "visual_description, product_subject, packaging_text_candidates, visible_text, "
        "dominant_colors, composition, style_tags, scene, usage_recommendation, "
        "generation_grounding, risk_flags, confidence, image_text_matches_product。"
        "不要把看不清的文字或功效当成确定事实；不确定请写入 risk_flags。"
    )

def _extract_response_text(value: Any) -> str:
    if isinstance(value, dict):
        output_text = _text(value.get("output_text"))
        if output_text:
            return output_text
        chunks: List[str] = []
        output = value.get("output")
        if isinstance(output, list):
            for item in output:
                text = _extract_response_text(item)
                if text:
                    chunks.append(text)
        content = value.get("content")
        if isinstance(content, list):
            for item in content:
                item_type = _text(item.get("type")) if isinstance(item, dict) else ""
                if item_type in {"output_text", "text"}:
                    text = _text(item.get("text")) if isinstance(item, dict) else ""
                    if text:
                        chunks.append(text)
                else:
                    text = _extract_response_text(item)
                    if text:
                        chunks.append(text)
        choices = value.get("choices")
        if isinstance(choices, list):
            for item in choices:
                text = _extract_response_text(item)
                if text:
                    chunks.append(text)
        message = value.get("message")
        if isinstance(message, dict):
            text = _extract_response_text(message)
            if text:
                chunks.append(text)
        if chunks:
            return "\n".join(chunks)
        return _text(value.get("text"))
    if isinstance(value, list):
        return "\n".join(item for item in (_extract_response_text(item) for item in value) if item)
    return ""

def _parse_json_text(text: str) -> Dict[str, Any]:
    clean = _text(text)
    if clean.startswith("```"):
        clean = clean.strip("`").strip()
        if clean.lower().startswith("json"):
            clean = clean[4:].strip()
    try:
        payload = json.loads(clean)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(clean[start : end + 1])
                return payload if isinstance(payload, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}

def _string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []

def _run_vlm_analysis(
    provider_name: str,
    provider: Dict[str, Any],
    stored: Path,
    material: Dict[str, Any],
    product_name: str,
) -> Dict[str, Any]:
    endpoint = _provider_value(provider, "endpoint", "endpoint_env")
    model = _provider_value(provider, "model", "model_env")
    api_key = _provider_value(provider, "api_key", "auth_env")
    if not endpoint:
        raise RuntimeError(f"VLM provider endpoint is not configured: {provider_name}")
    if provider.get("auth_env") and not api_key:
        raise RuntimeError(f"VLM provider auth env is missing: {provider.get('auth_env')}")
    if not model:
        raise RuntimeError(f"VLM provider model is not configured: {provider_name}")

    image_url, image_source = _image_input_url(stored, material)
    defaults = provider.get("request_defaults") or {}
    prompt = _text(defaults.get("prompt")) or _default_vlm_prompt(product_name)
    body = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": image_url},
                    {"type": "input_text", "text": prompt},
                ],
            }
        ],
    }
    if defaults.get("max_output_tokens"):
        body["max_output_tokens"] = int(defaults.get("max_output_tokens"))
    response_payload = _post_json(endpoint, body, api_key)
    output_text = _extract_response_text(response_payload)
    parsed = _parse_json_text(output_text)
    top_level_keys = sorted(response_payload.keys()) if isinstance(response_payload, dict) else []
    image_url_for_record = image_url if image_source == "remote_url" else f"data:{_mime_type(stored)};base64,<redacted>"
    return {
        "provider": provider_name,
        "provider_status": provider.get("status", ""),
        "model": model,
        "endpoint": endpoint,
        "image_source": image_source,
        "image_url_for_record": image_url_for_record,
        "prompt": prompt,
        "response_top_level_keys": top_level_keys,
        "response_usage": response_payload.get("usage", {}) if isinstance(response_payload, dict) else {},
        "raw_text": output_text,
        "parsed": parsed,
    }

def _analysis_from_vlm(vlm: Dict[str, Any], product_name: str) -> Dict[str, Any]:
    parsed = vlm.get("parsed") if isinstance(vlm.get("parsed"), dict) else {}
    raw_text = _text(vlm.get("raw_text"))
    summary = _text(parsed.get("visual_description")) or raw_text[:500]
    subject = _text(parsed.get("product_subject")) or product_name
    visible_text = _string_list(parsed.get("visible_text") or parsed.get("packaging_text_candidates"))
    risk_flags = _string_list(parsed.get("risk_flags"))
    if not parsed:
        risk_flags.append("VLM response was not valid JSON; raw text is preserved for human review.")
    return {
        "summary": summary,
        "confidence": _text(parsed.get("confidence")) or ("medium" if raw_text else "low"),
        "visual_observations": {
            "subject": subject,
            "packaging": "; ".join(_string_list(parsed.get("packaging_text_candidates"))) or "not_confirmed_by_human",
            "dominant_colors": _string_list(parsed.get("dominant_colors")),
            "visible_text": visible_text,
            "composition": _text(parsed.get("composition")) or "not_specified_by_provider",
            "style": ", ".join(_string_list(parsed.get("style_tags"))) or _text(parsed.get("style")) or "not_specified_by_provider",
            "scene": _text(parsed.get("scene")) or "not_specified_by_provider",
        },
        "generation_grounding": {
            "usage_recommendation": _text(parsed.get("usage_recommendation")),
            "prompt_grounding": _text(parsed.get("generation_grounding")),
        },
        "image_text_matches_product": parsed.get("image_text_matches_product", "unknown"),
        "risk_flags": risk_flags,
        "provider_output": {
            "raw_text": raw_text,
            "parsed_json": parsed,
            "response_top_level_keys": vlm.get("response_top_level_keys", []),
            "usage": vlm.get("response_usage", {}),
        },
    }

def _has_visual_product_mismatch(image_analysis: Dict[str, Any]) -> bool:
    alignment = image_analysis.get("product_alignment") if isinstance(image_analysis.get("product_alignment"), dict) else {}
    match_value = alignment.get("image_text_matches_product")
    if match_value is False:
        return True
    visual = image_analysis.get("visual_observations") if isinstance(image_analysis.get("visual_observations"), dict) else {}
    haystack = " ".join(
        str(item)
        for item in [
            image_analysis.get("summary", ""),
            visual.get("subject", ""),
            match_value,
            *(_list(image_analysis.get("risks_or_missing_understanding"))),
        ]
        if item is not None
    ).lower()
    mismatch_patterns = [
        "并非电商产品主图",
        "无实体商品",
        "无实体电商商品",
        "无实物商品",
        "不存在实体商品",
        "无法支撑",
        "非商品",
        "not a product",
        "not product",
        "does not show product",
        "does not depict product",
        "not match the product",
    ]
    return any(pattern in haystack for pattern in mismatch_patterns)

def _analysis_markdown(analysis: Dict[str, Any]) -> str:
    visual = analysis.get("visual_observations") or {}
    lines = [
        f"# {analysis['analysis_id']}",
        "",
        f"Material: {analysis['material_id']}",
        f"Provider: {analysis['provider']}",
        f"Status: {analysis['status']}",
        f"Confidence: {analysis['confidence']}",
        f"External call: {analysis['external_call_performed']}",
        "",
        "## Summary",
        "",
        analysis.get("summary") or "",
        "",
        "## Visual Observations",
        "",
        f"- Subject: {visual.get('subject')}",
        f"- Packaging: {visual.get('packaging')}",
        f"- Composition: {visual.get('composition')}",
        f"- Style: {visual.get('style')}",
        "",
        "## Quality Flags",
        "",
    ]
    lines.extend([f"- {item}" for item in analysis.get("quality_flags", [])] or ["- None"])
    lines.extend(["", "## Risks Or Missing Understanding", ""])
    lines.extend([f"- {item}" for item in analysis.get("risks_or_missing_understanding", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def _visual_alignment_markdown(alignment: Dict[str, Any]) -> str:
    lines = [
        f"# {alignment['alignment_id']}",
        "",
        f"Analysis: {alignment['source_analysis_id']}",
        f"Material: {alignment['material_id']}",
        f"Status: {alignment['status']}",
        f"Eligible for evolution: {alignment['eligible_for_evolution_proposal']}",
        "",
        "## Summary",
        "",
        alignment.get("summary") or "",
        "",
        "## Checks",
        "",
    ]
    for key, value in (alignment.get("checks") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Proposed Learning", ""])
    for item in alignment.get("proposed_learning", []):
        lines.append(f"- {item.get('path')}: {item.get('value')}")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- {item}" for item in alignment.get("blockers", [])] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in alignment.get("warnings", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def _json_records(base: Path, folder: str) -> List[Dict[str, Any]]:
    records = artifacts().list(base.name, folder)
    records.sort(key=lambda value: (_text(value.get("created_at")), _text(value.get("analysis_id") or value.get("alignment_id"))))
    return records

def _resolve_image_analysis(base: Path, value: str) -> Dict[str, Any]:
    if not value:
        raise ValueError("image analysis id or path is required")
    for item in _json_records(base, "image_analysis"):
        if value in {item.get("analysis_id"), item.get("source_material_path")}:
            return item
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("image analysis path must stay inside the product workspace")
        payload = read_json(resolved, {})
        if isinstance(payload, dict):
            return payload
    name = value if value.endswith(".json") else f"{value}.json"
    path = base / "artifacts" / "image_analysis" / name
    if path.exists():
        payload = read_json(path, {})
        if isinstance(payload, dict):
            return payload
    raise FileNotFoundError(f"image analysis '{value}' does not exist")

def analyze_image_asset(product_id: str, asset: str, provider: str = "mock-vision") -> Dict[str, Any]:
    base = ensure_product(product_id)
    material = _resolve_material(base, asset)
    stored = (base / _text(material.get("stored_path"))).resolve()
    if not stored.exists():
        raise FileNotFoundError(f"stored material file is missing: {material.get('stored_path')}")
    width, height = _read_image_size(stored)
    state = read_product_state(base)
    product_name = _text(state.get("name")) or base.name
    role = _text(material.get("role"))
    suitable_first_frame = bool(width and height and role in {"current_main_image", "video_first_frame", "product_photo"})
    provider_name = provider or "mock-vision"
    is_mock = provider_name == "mock-vision"
    if not is_mock and os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") != "1":
        raise PermissionError(
            "Real VLM provider execution is disabled; set PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1 only after explicit approval."
        )
    provider_entry = _load_provider(provider_name)
    vlm_analysis: Dict[str, Any] = {}
    vlm_call: Dict[str, Any] = {}
    if not is_mock:
        if provider_entry.get("adapter") != "responses-vlm":
            raise ValueError(f"provider '{provider_name}' is not an image-analysis VLM provider")
        vlm_call = _run_vlm_analysis(provider_name, provider_entry, stored, material, product_name)
        vlm_analysis = _analysis_from_vlm(vlm_call, product_name)
    analysis_id = f"image-analysis-{timestamp()}-{_text(material.get('material_id'))[-8:]}"
    visual_observations = vlm_analysis.get("visual_observations") or {
        "subject": product_name,
        "packaging": "not_extracted_by_mock_provider",
        "dominant_colors": [],
        "visible_text": [],
        "composition": "not_extracted_by_mock_provider",
        "style": "not_extracted_by_mock_provider",
        "scene": "not_extracted_by_mock_provider",
    }
    quality_flags = [
        item
        for item in [
            "dimensions_readable" if width and height else "",
            "usable_as_reference_image" if width and height else "",
            "suitable_as_video_first_frame" if suitable_first_frame else "",
            "real_multimodal_analysis" if not is_mock else "",
        ]
        if item
    ]
    risks = list(vlm_analysis.get("risk_flags") or [])
    if is_mock:
        risks.extend(
            [
                "No OCR has been performed yet.",
                "No real multimodal visual recognition has been performed yet.",
                "Do not write this analysis into Product Brain without a user-reviewed visual proposal.",
            ]
        )
    else:
        risks.append("Do not write VLM visual conclusions into Product Brain without human confirmation.")
    analysis = {
        "schema_version": IMAGE_ANALYSIS_SCHEMA_VERSION,
        "analysis_id": analysis_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_review",
        "provider": provider_name,
        "provider_status": provider_entry.get("status", "mock"),
        "model": _text(vlm_call.get("model")),
        "external_call_performed": not is_mock,
        "material_id": material.get("material_id", ""),
        "material_role": role,
        "source_material_path": material.get("stored_path", ""),
        "confidence": vlm_analysis.get("confidence") or ("low" if is_mock else "medium"),
        "summary": vlm_analysis.get("summary") or (
            f"Mock visual analysis contract for {product_name}. "
            "No multimodal model was called; use this artifact as the stable schema for future VLM/OCR integration."
        ),
        "image": {
            "path": material.get("stored_path", ""),
            "mime_type": material.get("media", {}).get("mime_type", _mime_type(stored)),
            "width": width,
            "height": height,
            "orientation": _orientation(width, height),
            "sha256": material.get("sha256", ""),
        },
        "visual_observations": visual_observations,
        "generation_grounding": vlm_analysis.get("generation_grounding", {}),
        "product_alignment": {
            "uses_existing_product_brain": True,
            "product_name_from_brain": product_name,
            "image_text_matches_product": vlm_analysis.get("image_text_matches_product", "unknown_without_ocr"),
            "requires_human_review": True,
        },
        "quality_flags": quality_flags,
        "risks_or_missing_understanding": risks,
        "provider_request": {
            "endpoint": _provider_value(provider_entry, "endpoint", "endpoint_env") if not is_mock else "",
            "model": _provider_value(provider_entry, "model", "model_env") if not is_mock else "",
            "image_source": vlm_call.get("image_source", ""),
            "image_url": vlm_call.get("image_url_for_record", ""),
            "prompt": vlm_call.get("prompt", ""),
            "auth": "bearer_env" if provider_entry.get("auth_env") else "none",
        },
        "provider_output": vlm_analysis.get("provider_output", {}),
        "brain_write_policy": {
            "direct_write_to_product_brain": False,
            "requires_visual_alignment": True,
            "requires_human_confirmation_for_learning": True,
        },
    }
    out_dir = base / "artifacts" / "image_analysis"
    json_path = out_dir / f"{analysis_id}.json"
    md_path = out_dir / f"{analysis_id}.md"
    write_json(json_path, analysis)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_analysis_markdown(analysis), encoding="utf-8")
    append_jsonl(base / "structured" / "image_analysis_index.jsonl", {
        "analysis_id": analysis_id,
        "created_at": analysis["created_at"],
        "material_id": material.get("material_id", ""),
        "provider": analysis["provider"],
        "status": analysis["status"],
    })
    update_index_and_log(base, "image-analysis", analysis_id, [f"Material: {material.get('material_id', '')}"])
    return {
        "success": True,
        "product_id": base.name,
        "analysis_id": analysis_id,
        "material_id": material.get("material_id", ""),
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "analysis": analysis,
    }

def align_visual_analysis(product_id: str, analysis: str, note: str = "") -> Dict[str, Any]:
    base = ensure_product(product_id)
    image_analysis = _resolve_image_analysis(base, analysis)
    state = read_product_state(base)
    product_name = _text(state.get("name")) or base.name
    material_id = _text(image_analysis.get("material_id"))
    material_role = _text(image_analysis.get("material_role"))
    quality_flags = [str(item) for item in _list(image_analysis.get("quality_flags"))]
    warnings: List[str] = []
    blockers: List[str] = []

    if not material_id:
        blockers.append("image analysis is not linked to a registered material asset")
    if "dimensions_readable" not in quality_flags:
        blockers.append("image dimensions are not readable")
    if image_analysis.get("external_call_performed") is False:
        warnings.append("image analysis is based on mock/local metadata, not real OCR or multimodal recognition")
    if image_analysis.get("confidence") == "low":
        warnings.append("image analysis confidence is low and requires human review")
    if material_role not in {"current_main_image", "video_first_frame", "product_photo", "style_reference"}:
        warnings.append(f"material role '{material_role}' may be weak for image/video generation")
    provider_output = image_analysis.get("provider_output") if isinstance(image_analysis.get("provider_output"), dict) else {}
    if image_analysis.get("external_call_performed") and not provider_output.get("parsed_json"):
        blockers.append("VLM response could not be normalized into structured JSON")
    if image_analysis.get("external_call_performed") and _has_visual_product_mismatch(image_analysis):
        blockers.append("VLM analysis indicates this image may not depict the target product or may be unsuitable as a product visual reference")

    can_reference = "usable_as_reference_image" in quality_flags
    can_first_frame = "suitable_as_video_first_frame" in quality_flags
    status = "ready_for_proposal" if not blockers else "blocked"
    eligible = bool(status == "ready_for_proposal" and can_reference)
    alignment_id = f"visual-align-{timestamp()}-{material_id[-8:] if material_id else 'unknown'}"
    proposed_learning = []
    if eligible:
        if image_analysis.get("external_call_performed"):
            reference_note = (
                f"用户确认素材 {material_id}（role={material_role}）可作为 {product_name} 的视觉参考；"
                f"可参考已审阅主图理解：{_text(image_analysis.get('summary'))}。"
                "包装文字、成分、认证或功效仍以人工确认后的 Product Brain 为准。"
            )
        else:
            reference_note = (
                f"用户确认素材 {material_id}（role={material_role}）可作为 {product_name} 的视觉参考；"
                "在未接入真实 OCR/VLM 前，不从该图推断包装文字、成分、认证或功效。"
            )
        if note:
            reference_note = f"{reference_note} 用户补充：{note}"
        proposed_learning.append(
            {
                "path": "learning.image_generation_preferences",
                "value": reference_note,
                "reason": "Use reviewed material asset as a stable visual reference for image/video generation.",
            }
        )
        if can_first_frame:
            proposed_learning.append(
                {
                    "path": "learning.successful_patterns",
                    "value": f"{product_name} 可优先使用素材 {material_id} 作为图生视频首帧/参考图，但需保持包装与画面主体一致。",
                    "reason": "Material is suitable as a first-frame reference according to local checks.",
                }
            )

    alignment = {
        "schema_version": VISUAL_ALIGNMENT_SCHEMA_VERSION,
        "alignment_id": alignment_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": status,
        "source_analysis_id": image_analysis.get("analysis_id", ""),
        "source_analysis_path": f"artifacts/image_analysis/{image_analysis.get('analysis_id', '')}.json"
        if image_analysis.get("analysis_id")
        else "",
        "material_id": material_id,
        "material_role": material_role,
        "source_material_path": image_analysis.get("source_material_path", ""),
        "summary": (
            f"Visual alignment for {product_name}: material {material_id or 'unknown'} is "
            f"{'eligible' if eligible else 'not eligible'} for reviewable visual learning."
        ),
        "checks": {
            "uses_existing_product_brain": bool(image_analysis.get("product_alignment", {}).get("uses_existing_product_brain")),
            "product_name_from_brain": product_name,
            "image_text_matches_product": image_analysis.get("product_alignment", {}).get("image_text_matches_product", "unknown"),
            "usable_as_reference_image": can_reference,
            "suitable_as_video_first_frame": can_first_frame,
            "requires_real_ocr_or_vlm_for_packaging_claims": not bool(image_analysis.get("external_call_performed")),
        },
        "warnings": warnings,
        "blockers": blockers,
        "eligible_for_evolution_proposal": eligible,
        "proposed_learning": proposed_learning,
        "brain_write_policy": {
            "direct_write_to_product_brain": False,
            "requires_human_confirmation_for_learning": True,
        },
    }
    out_dir = base / "artifacts" / "visual_alignments"
    json_path = out_dir / f"{alignment_id}.json"
    md_path = out_dir / f"{alignment_id}.md"
    alignment["source_alignment_path"] = _rel(base, json_path)
    write_json(json_path, alignment)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_visual_alignment_markdown(alignment), encoding="utf-8")
    append_jsonl(base / "structured" / "visual_alignment_index.jsonl", {
        "alignment_id": alignment_id,
        "created_at": alignment["created_at"],
        "material_id": material_id,
        "source_analysis_id": image_analysis.get("analysis_id", ""),
        "eligible_for_evolution_proposal": eligible,
        "status": status,
        "path": alignment["source_alignment_path"],
    })
    update_index_and_log(base, "visual-align", alignment_id, [f"Material: {material_id}", f"Eligible: {eligible}"])
    return {
        "success": status != "blocked",
        "product_id": base.name,
        "alignment_id": alignment_id,
        "eligible_for_evolution_proposal": eligible,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "alignment": alignment,
    }
