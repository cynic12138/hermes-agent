"""M3 material cards built from M2 visual material artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import artifacts


MATERIAL_CARD_SCHEMA_VERSION = "product_creative.material_card.v3.2"
MATERIAL_LIBRARY_MAP_SCHEMA_VERSION = "product_creative.material_library_map.v3.3"
MATERIAL_COMPAT_SCHEMA_VERSION = "product_creative.material_m2_compat.v3.1"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def _json_records(base: Path, folder: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for stored in artifacts().list(base.name, folder):
        payload = dict(stored)
        artifact_id = _text(payload.get("material_id") or payload.get("analysis_id") or payload.get("alignment_id"))
        payload["_artifact_path"] = str(Path("artifacts") / folder / f"{artifact_id}.json")
        records.append(payload)
    records.sort(
        key=lambda item: (
            _text(item.get("created_at")),
            _text(item.get("material_id") or item.get("analysis_id") or item.get("alignment_id")),
        )
    )
    return records


def _latest_for_material(records: List[Dict[str, Any]], material_id: str, id_field: str) -> Dict[str, Any]:
    matches = [item for item in records if item.get("material_id") == material_id]
    matches.sort(key=lambda item: (_text(item.get("created_at")), _text(item.get(id_field))))
    return matches[-1] if matches else {}


def _material_records(base: Path) -> List[Dict[str, Any]]:
    return _json_records(base, "material_assets")


def _analysis_records(base: Path) -> List[Dict[str, Any]]:
    return _json_records(base, "image_analysis")


def _alignment_records(base: Path) -> List[Dict[str, Any]]:
    return _json_records(base, "visual_alignments")


def check_m2_material_compatibility(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    materials = _material_records(base)
    analyses = _analysis_records(base)
    alignments = _alignment_records(base)
    rows: List[Dict[str, Any]] = []
    for material in materials:
        material_id = _text(material.get("material_id"))
        analysis = _latest_for_material(analyses, material_id, "analysis_id")
        alignment = _latest_for_material(alignments, material_id, "alignment_id")
        rows.append(
            {
                "material_id": material_id,
                "role": _text(material.get("role")),
                "status": _text(material.get("status")),
                "stored_path": _text(material.get("stored_path")),
                "has_image_analysis": bool(analysis),
                "image_analysis_id": _text(analysis.get("analysis_id")),
                "image_analysis_confidence": _text(analysis.get("confidence")),
                "has_visual_alignment": bool(alignment),
                "visual_alignment_id": _text(alignment.get("alignment_id")),
                "visual_alignment_status": _text(alignment.get("status")),
                "blocked_as_primary_reference": _text(alignment.get("status")) == "blocked",
            }
        )
    return {
        "success": True,
        "schema_version": MATERIAL_COMPAT_SCHEMA_VERSION,
        "product_id": base.name,
        "material_count": len(materials),
        "image_analysis_count": len(analyses),
        "visual_alignment_count": len(alignments),
        "materials": rows,
        "mutates_product_brain": False,
        "external_call_performed": False,
    }


def _split_style_tags(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = _text(value)
    if not text:
        return []
    separators = [",", "，", "、", ";", "；"]
    chunks = [text]
    for sep in separators:
        next_chunks: List[str] = []
        for chunk in chunks:
            next_chunks.extend(chunk.split(sep))
        chunks = next_chunks
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _remote_url(material: Dict[str, Any]) -> str:
    value = _text(material.get("remote_url"))
    if value:
        return value
    for item in _list(material.get("remote_urls")):
        if isinstance(item, dict) and _text(item.get("url")):
            return _text(item.get("url"))
    return ""


def _recommended_use(material: Dict[str, Any], analysis: Dict[str, Any], alignment: Dict[str, Any]) -> Dict[str, str]:
    role = _text(material.get("role"))
    usage = {str(item) for item in _list(material.get("usage"))}
    status = _text(alignment.get("status"))
    blocked = status == "blocked"
    can_reference = bool((material.get("generation_policy") or {}).get("can_be_reference_image"))
    can_first_frame = bool((material.get("generation_policy") or {}).get("can_be_video_first_frame"))
    if alignment:
        checks = alignment.get("checks") if isinstance(alignment.get("checks"), dict) else {}
        can_reference = can_reference and bool(checks.get("usable_as_reference_image", True))
        can_first_frame = can_first_frame and bool(checks.get("suitable_as_video_first_frame", can_first_frame))
    if blocked:
        return {
            "image_brief": "not_recommended",
            "video_first_frame": "not_recommended",
            "channel_content": "possible_with_warning",
            "style_reference": "possible_with_warning" if role == "style_reference" else "not_recommended",
        }
    return {
        "image_brief": "suitable" if can_reference and role in {"current_main_image", "product_photo", "detail_image", "generated_candidate"} else "possible",
        "video_first_frame": "suitable" if can_first_frame and ("video_first_frame" in usage or role in {"video_first_frame", "current_main_image", "product_photo"}) else "possible",
        "channel_content": "suitable" if can_reference else "possible",
        "style_reference": "suitable" if role == "style_reference" else "possible",
    }


def _build_card(base: Path, material: Dict[str, Any], analysis: Dict[str, Any], alignment: Dict[str, Any]) -> Dict[str, Any]:
    material_id = _text(material.get("material_id"))
    visual = analysis.get("visual_observations") if isinstance(analysis.get("visual_observations"), dict) else {}
    checks = alignment.get("checks") if isinstance(alignment.get("checks"), dict) else {}
    risks = [str(item) for item in _list(analysis.get("risks_or_missing_understanding")) if str(item).strip()]
    risks.extend(str(item) for item in _list(alignment.get("warnings")) if str(item).strip())
    blockers = [str(item) for item in _list(alignment.get("blockers")) if str(item).strip()]
    if blockers:
        risks.extend(f"blocker: {item}" for item in blockers)
    card_id = f"material-card-{material_id}"
    stored_path = _text(material.get("stored_path"))
    image_exists = bool(stored_path and (base / stored_path).exists())
    return {
        "schema_version": MATERIAL_CARD_SCHEMA_VERSION,
        "material_card_id": card_id,
        "material_id": material_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": _text(material.get("status")) or "active",
        "role": _text(material.get("role")),
        "usage": [str(item) for item in _list(material.get("usage")) if str(item).strip()],
        "source_files": {
            "material_asset": _text(material.get("_artifact_path")),
            "image_analysis": _text(analysis.get("_artifact_path")),
            "visual_alignment": _text(alignment.get("_artifact_path")),
        },
        "image_file": stored_path,
        "image_exists": image_exists,
        "remote_url": _remote_url(material),
        "remote_urls": _list(material.get("remote_urls")),
        "media": material.get("media", {}),
        "ai_readable_summary": {
            "manual_description": _text(material.get("description")),
            "visual_summary": _text(analysis.get("summary")) or "No image analysis is available yet.",
            "subject": _text(visual.get("subject")),
            "composition": _text(visual.get("composition")),
            "scene": _text(visual.get("scene")),
            "style_tags": _split_style_tags(visual.get("style")),
            "dominant_colors": [str(item) for item in _list(visual.get("dominant_colors")) if str(item).strip()],
            "visible_text": [str(item) for item in _list(visual.get("visible_text")) if str(item).strip()],
            "risk_flags": risks,
        },
        "readiness": {
            "can_reference_image": bool((material.get("generation_policy") or {}).get("can_be_reference_image")),
            "can_video_first_frame": bool((material.get("generation_policy") or {}).get("can_be_video_first_frame")),
            "has_remote_url": bool(_remote_url(material)),
            "has_image_analysis": bool(analysis),
            "image_analysis_id": _text(analysis.get("analysis_id")),
            "image_analysis_confidence": _text(analysis.get("confidence")),
            "image_analysis_external_call": bool(analysis.get("external_call_performed")),
            "has_visual_alignment": bool(alignment),
            "visual_alignment_id": _text(alignment.get("alignment_id")),
            "visual_alignment_status": _text(alignment.get("status")),
            "eligible_for_learning": bool(alignment.get("eligible_for_evolution_proposal")),
            "blocked_as_primary_reference": _text(alignment.get("status")) == "blocked" or bool(blockers),
            "usable_as_reference_image": bool(checks.get("usable_as_reference_image", False)),
            "suitable_as_video_first_frame": bool(checks.get("suitable_as_video_first_frame", False)),
        },
        "recommended_use": _recommended_use(material, analysis, alignment),
        "brain_write_policy": {
            "direct_write_to_product_brain": False,
            "requires_human_confirmation_for_learning": True,
        },
    }


def _card_markdown(card: Dict[str, Any]) -> str:
    summary = card.get("ai_readable_summary") if isinstance(card.get("ai_readable_summary"), dict) else {}
    readiness = card.get("readiness") if isinstance(card.get("readiness"), dict) else {}
    source_files = card.get("source_files") if isinstance(card.get("source_files"), dict) else {}
    recommended = card.get("recommended_use") if isinstance(card.get("recommended_use"), dict) else {}
    lines = [
        f"# Material Card: {card['material_id']}",
        "",
        f"Role: {card.get('role', '')}",
        f"Status: {card.get('status', '')}",
        f"Usage: {', '.join(str(item) for item in _list(card.get('usage'))) or 'none'}",
        f"Image file: {card.get('image_file', '')}",
        f"Image exists: {card.get('image_exists')}",
        f"Remote URL: {card.get('remote_url') or 'none'}",
        "",
        "## AI-readable Summary",
        "",
        summary.get("manual_description") or "",
        "",
        summary.get("visual_summary") or "",
        "",
        "## Visual Understanding",
        "",
        f"Source: {source_files.get('image_analysis') or 'none'}",
        f"Confidence: {readiness.get('image_analysis_confidence') or 'none'}",
        f"Subject: {summary.get('subject') or ''}",
        f"Composition: {summary.get('composition') or ''}",
        f"Scene: {summary.get('scene') or ''}",
        f"Style tags: {', '.join(str(item) for item in _list(summary.get('style_tags')))}",
        "",
        "## Product Alignment",
        "",
        f"Source: {source_files.get('visual_alignment') or 'none'}",
        f"Status: {readiness.get('visual_alignment_status') or 'missing'}",
        f"Can be primary reference: {not bool(readiness.get('blocked_as_primary_reference'))}",
        f"Can video first frame: {readiness.get('can_video_first_frame')}",
        "",
        "## Recommended Use",
        "",
    ]
    for key in ["image_brief", "video_first_frame", "channel_content", "style_reference"]:
        lines.append(f"- {key}: {recommended.get(key, 'unknown')}")
    lines.extend(["", "## Warnings", ""])
    risks = _list(summary.get("risk_flags"))
    lines.extend([f"- {item}" for item in risks] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def rebuild_material_cards(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    materials = _material_records(base)
    analyses = _analysis_records(base)
    alignments = _alignment_records(base)
    out_dir = base / "artifacts" / "material_cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    cards: List[Dict[str, Any]] = []
    index_rows: List[Dict[str, Any]] = []
    for material in materials:
        material_id = _text(material.get("material_id"))
        if not material_id:
            continue
        analysis = _latest_for_material(analyses, material_id, "analysis_id")
        alignment = _latest_for_material(alignments, material_id, "alignment_id")
        card = _build_card(base, material, analysis, alignment)
        json_path = out_dir / f"{card['material_card_id']}.json"
        md_path = out_dir / f"{card['material_card_id']}.md"
        write_json(json_path, card)
        md_path.write_text(_card_markdown(card), encoding="utf-8")
        cards.append(card)
        index_rows.append(
            {
                "material_card_id": card["material_card_id"],
                "material_id": material_id,
                "created_at": card["created_at"],
                "role": card.get("role", ""),
                "status": card.get("status", ""),
                "path": _rel(base, json_path),
                "markdown": _rel(base, md_path),
                "has_image_analysis": card["readiness"]["has_image_analysis"],
                "has_visual_alignment": card["readiness"]["has_visual_alignment"],
                "blocked_as_primary_reference": card["readiness"]["blocked_as_primary_reference"],
            }
        )
    index_path = base / "structured" / "material_card_index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in index_rows) + ("\n" if index_rows else ""),
        encoding="utf-8",
    )
    update_index_and_log(base, "material-cards", "rebuild", [f"{len(cards)} material card(s) rebuilt"])
    return {
        "success": True,
        "schema_version": MATERIAL_CARD_SCHEMA_VERSION,
        "product_id": base.name,
        "card_count": len(cards),
        "files": {"index": str(index_path)},
        "cards": cards,
        "mutates_product_brain": False,
        "external_call_performed": False,
    }


def _card_records(base: Path) -> List[Dict[str, Any]]:
    records = _json_records(base, "material_cards")
    if not records and _material_records(base):
        rebuild_material_cards(base.name)
        records = _json_records(base, "material_cards")
    return records


def _library_markdown(library: Dict[str, Any]) -> str:
    lines = [
        "# Material Library Map",
        "",
        f"Product: {library['product_id']}",
        f"Material cards: {library['card_count']}",
        "",
        "## By Role",
        "",
    ]
    by_role = library.get("by_role") if isinstance(library.get("by_role"), dict) else {}
    for role in sorted(by_role):
        lines.append(f"### {role}")
        for item in by_role[role]:
            marker = "blocked" if item.get("blocked_as_primary_reference") else "ready"
            lines.append(f"- {item.get('material_id')} ({marker}) {item.get('markdown_path')}")
        lines.append("")
    lines.extend(["## Missing Readiness", ""])
    missing = library.get("missing_readiness") if isinstance(library.get("missing_readiness"), dict) else {}
    for key in ["missing_image_analysis", "missing_visual_alignment", "blocked_as_primary_reference"]:
        lines.append(f"### {key}")
        lines.extend([f"- {item}" for item in missing.get(key, [])] or ["- None"])
        lines.append("")
    return "\n".join(lines)


def rebuild_material_library_map(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    cards = _card_records(base)
    by_role: Dict[str, List[Dict[str, Any]]] = {}
    by_usage: Dict[str, List[Dict[str, Any]]] = {}
    missing_image_analysis: List[str] = []
    missing_visual_alignment: List[str] = []
    blocked: List[str] = []
    for card in cards:
        readiness = card.get("readiness") if isinstance(card.get("readiness"), dict) else {}
        item = {
            "material_card_id": _text(card.get("material_card_id")),
            "material_id": _text(card.get("material_id")),
            "role": _text(card.get("role")),
            "status": _text(card.get("status")),
            "markdown_path": f"artifacts/material_cards/{_text(card.get('material_card_id'))}.md",
            "can_reference_image": bool(readiness.get("can_reference_image")),
            "can_video_first_frame": bool(readiness.get("can_video_first_frame")),
            "blocked_as_primary_reference": bool(readiness.get("blocked_as_primary_reference")),
        }
        by_role.setdefault(item["role"] or "unknown", []).append(item)
        for usage in _list(card.get("usage")):
            by_usage.setdefault(str(usage), []).append(item)
        if not readiness.get("has_image_analysis"):
            missing_image_analysis.append(item["material_id"])
        if not readiness.get("has_visual_alignment"):
            missing_visual_alignment.append(item["material_id"])
        if readiness.get("blocked_as_primary_reference"):
            blocked.append(item["material_id"])
    library = {
        "schema_version": MATERIAL_LIBRARY_MAP_SCHEMA_VERSION,
        "material_library_map_id": "material-library-map",
        "product_id": base.name,
        "created_at": now_iso(),
        "card_count": len(cards),
        "by_role": by_role,
        "by_usage": by_usage,
        "missing_readiness": {
            "missing_image_analysis": missing_image_analysis,
            "missing_visual_alignment": missing_visual_alignment,
            "blocked_as_primary_reference": blocked,
        },
        "safety": {
            "mutates_product_brain": False,
            "external_call_performed": False,
        },
    }
    json_path = base / "structured" / "material_library_map.json"
    artifact_json_path = base / "artifacts" / "material_library" / "material-library-map.json"
    md_path = base / "artifacts" / "material_library" / "material_library.md"
    write_json(json_path, library)
    write_json(artifact_json_path, library)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_library_markdown(library), encoding="utf-8")
    update_index_and_log(base, "material-library-map", "rebuild", [f"{len(cards)} material card(s) mapped"])
    return {
        "success": True,
        "schema_version": MATERIAL_LIBRARY_MAP_SCHEMA_VERSION,
        "product_id": base.name,
        "card_count": len(cards),
        "files": {"json": str(json_path), "artifact_json": str(artifact_json_path), "markdown": str(md_path)},
        "material_library_map": library,
        "mutates_product_brain": False,
        "external_call_performed": False,
    }
