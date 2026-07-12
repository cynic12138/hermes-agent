"""Generated result review package service."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state
from ...brain.rules import create_rule_candidates_for_evaluation
from ..learning.feedback_repository import read_result_feedback_entries

from .result_shared import _brief_context, _list, _media_outputs, _rel, _resolve_result_path, _text

RESULT_REVIEW_PACKAGE_SCHEMA_VERSION = "product_creative.result_review_package.v7.2"

def _review_markdown(package: Dict[str, Any]) -> str:
    lines = [
        f"# {package['result_review_package_id']}",
        "",
        f"Product: {package['product'].get('name', '')}",
        f"Result: {package['result'].get('result_id', '')}",
        f"Type: {package['result'].get('brief_type', '')}",
        f"Status: {package['result'].get('status', '')}",
        f"Provider: {package['result'].get('provider', '')}",
        "",
        "## Outputs",
        "",
    ]
    for item in package.get("outputs") or []:
        path = item.get("absolute_path") or item.get("remote_url") or item.get("path") or ""
        lines.append(f"- {item.get('type')}: {path}")
    lines.extend(["", "## Product Context", ""])
    lines.append(package["product"].get("brief", ""))
    lines.extend(["", "## Selling Points", ""])
    lines.extend([f"- {item}" for item in package["product"].get("selling_points", [])] or ["- None"])
    lines.extend(["", "## Source Prompt", ""])
    lines.append(package.get("source_prompt_excerpt") or "No prompt found.")
    identity = package.get("product_identity_review") or {}
    if identity:
        lines.extend(["", "## Product Identity Review", ""])
        lines.append(f"- Main image locked: {identity.get('main_image_locked')}")
        lines.append(f"- Source material: {identity.get('source_material_id', '')}")
        lines.append(f"- Composer/provider: {identity.get('provider', '')}")
        lines.append(f"- Allowed animation scope: {identity.get('allowed_animation_scope', '')}")
        forbidden = identity.get("forbidden_modifications") or []
        lines.extend(["", "Forbidden modifications:"])
        lines.extend([f"- {item}" for item in forbidden] or ["- None"])
    lines.extend(["", "## Review Checklist", ""])
    lines.extend([f"- {item}" for item in package.get("review_checklist", [])])
    lines.append("")
    return "\n".join(lines)

def create_result_review_package(product_id: str, result: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    result_path = _resolve_result_path(base, result)
    result_payload = read_json(result_path, {})
    state = apply_generation_safe_state(read_product_state(base))
    safe = state.get("generation_safe") if isinstance(state.get("generation_safe"), dict) else {}
    has_safe = isinstance(state.get("generation_safe"), dict)
    brief_context = _brief_context(base, result_payload)
    main_image_policy = result_payload.get("main_image_policy") if isinstance(result_payload.get("main_image_policy"), dict) else {}
    product_identity_review = {}
    if main_image_policy:
        product_identity_review = {
            "main_image_locked": bool(main_image_policy.get("locked")),
            "source_material_id": _text(result_payload.get("source_material_id")),
            "source_material_path": _text(result_payload.get("source_material_path")),
            "provider": _text(result_payload.get("provider")),
            "allowed_animation_scope": _text(main_image_policy.get("allowed_animation_scope")),
            "forbidden_modifications": _list(main_image_policy.get("forbidden_modifications")),
            "review_instruction": "Verify the fixed main image still matches the registered source image. Surrounding animation may change; product package/body/text/layout must not.",
        }
    package_id = f"result-review-package-{timestamp()}"
    prompt = _text(brief_context.get("prompt"))
    package = {
        "schema_version": RESULT_REVIEW_PACKAGE_SCHEMA_VERSION,
        "result_review_package_id": package_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_human_review",
        "source_result_id": result_payload.get("result_id", result_path.stem),
        "source_result_path": _rel(base, result_path),
        "mutates_product_brain": False,
        "external_call_performed": False,
        "product": {
            "name": safe.get("product_name") or state.get("name", base.name),
            "brief": safe.get("brief") if has_safe else (state.get("basic") or {}).get("brief", ""),
            "selling_points": safe.get("selling_points") if has_safe else state.get("selling_points", []),
        },
        "result": {
            "result_id": result_payload.get("result_id", result_path.stem),
            "brief_type": result_payload.get("brief_type", ""),
            "provider": result_payload.get("provider", ""),
            "mode": result_payload.get("mode", ""),
            "status": result_payload.get("status", ""),
            "remote_url": result_payload.get("remote_url", ""),
            "summary": result_payload.get("summary", ""),
        },
        "source_prompt_excerpt": prompt[:2000],
        "source_context": {
            "source_payload_id": brief_context.get("source_payload_id", ""),
            "source_brief_id": brief_context.get("source_brief_id", ""),
        },
        "product_identity_review": product_identity_review,
        "outputs": _media_outputs(base, result_payload),
        "review_checklist": [
            "产品主体是否清晰可识别。",
            "画面/视频是否符合当前产品定位和已确认卖点。",
            "包装文字、成分、功效、产地等事实是否被模型编造。",
            "图像构图或视频镜头是否能直接用于下一轮生成优化。",
            "用户确认后再允许沉淀为 Product Brain 学习。",
        ] + (
            [
                "主图固定类视频必须逐帧确认：产品包装本体、文字、图案、轮廓、颜色、吸嘴形态没有被改写。",
                "动漫、剧情、角色和动效只能发生在固定主图外部，不能覆盖或重绘主图内部产品。",
            ]
            if main_image_policy
            else []
        ),
        "next_actions": {
            "record_feedback_tool": "product_result_feedback",
            "evaluate_tool": "product_result_evaluate",
            "evolve_tool": "product_evolve",
        },
    }
    out_dir = base / "artifacts" / "result_review_packages"
    json_path = out_dir / f"{package_id}.json"
    md_path = out_dir / f"{package_id}.md"
    write_json(json_path, package)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_review_markdown(package), encoding="utf-8")
    append_jsonl(
        base / "structured" / "result_review_package_index.jsonl",
        {
            "result_review_package_id": package_id,
            "created_at": package["created_at"],
            "source_result_id": package["source_result_id"],
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "result-review-package", package_id, [str(json_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "result_review_package_id": package_id,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "package": package,
    }
