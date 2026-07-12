"""Product content generation application service."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, today, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state
from ...contracts.models import CreativeTaskBrief
from ..inspiration.library_service import latest_inspiration_context
from ..material.pack_service import prepare_task_material_pack, record_material_usage
from ...ports.runtime_repositories import artifact_documents, product_brains

from .fallback_service import TARGET_REGISTRY, _build_channel_content, _build_copy_pack, _skill_metadata
from .llm_service import _generate_with_llm
from .grounding_service import _audit_grounding, _repair_grounding
from .render_service import CHANNEL_CONTENT_SCHEMA_VERSION, _artifact_markdown, _create_experiment_page, _material_context_for_target

def generate_product(
    product_id: str,
    target: str = "product-copy-pack",
    variants: int = 3,
    creative_brief: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if target not in TARGET_REGISTRY:
        raise ValueError(f"unsupported generation target '{target}'")
    base = ensure_product(product_id)
    state = apply_generation_safe_state(read_product_state(base))
    count = max(1, min(int(variants or 3), 5))
    task_brief = (
        CreativeTaskBrief.model_validate(creative_brief).model_dump(mode="json")
        if creative_brief
        else {}
    )
    material_context = _material_context_for_target(base.name, target)
    packs, generation_meta = _generate_with_llm(base, target, count, material_context, task_brief)
    generation_method = "llm"
    if packs is None:
        if target == "product-copy-pack":
            packs = [_build_copy_pack(state, idx) for idx in range(1, count + 1)]
        else:
            packs = [_build_channel_content(state, target, idx) for idx in range(1, count + 1)]
        generation_method = "rule-fallback"
    quality_warnings = _audit_grounding(packs, state)
    grounding_repairs: List[Dict[str, Any]] = []
    if quality_warnings:
        packs, grounding_repairs = _repair_grounding(packs, state)
        quality_warnings = _audit_grounding(packs, state)
    target_spec = TARGET_REGISTRY[target]
    artifact_id = f"{target_spec['artifact_prefix']}-{timestamp()}"
    json_path = base / "artifacts" / target_spec["artifact_folder"] / f"{artifact_id}.json"
    md_path = base / "artifacts" / target_spec["artifact_folder"] / f"{artifact_id}.md"
    payload = {
        "artifact_id": artifact_id,
        "schema_version": CHANNEL_CONTENT_SCHEMA_VERSION if target != "product-copy-pack" else "product_creative.copy_pack.v0.2.5",
        "product_id": base.name,
        "target": target,
        "target_spec": target_spec,
        "created_at": now_iso(),
        "generation_method": generation_method,
        "llm_attempted": generation_meta.get("llm_attempted", False),
        "grounding_audit": {
            "status": "needs_review" if quality_warnings else "passed_lite_audit",
            "warning_count": len(quality_warnings),
            "warnings": quality_warnings,
            "repairs": grounding_repairs,
        },
        "skill": _skill_metadata(),
        "variants": packs,
    }
    if material_context:
        payload["material_context"] = material_context
    if task_brief:
        payload["creative_brief"] = task_brief
    if generation_meta.get("fallback_reason"):
        payload["fallback_reason"] = generation_meta["fallback_reason"]
    if generation_meta.get("llm"):
        payload["llm"] = generation_meta["llm"]
    raw_model_output = generation_meta.get("raw_model_output")
    if raw_model_output:
        raw_llm_path = base / "raw" / "generated-content" / f"{artifact_id}-llm-output.txt"
        raw_llm_path.write_text(str(raw_model_output), encoding="utf-8")
        payload.setdefault("llm", {})["raw_output"] = str(raw_llm_path.relative_to(base))
    artifact_documents(base).save(target_spec["artifact_folder"], artifact_id, payload)
    generation_snapshot = product_brains().record_generation_snapshot(
        base.name,
        target,
        {
            "artifact_id": artifact_id,
            "generation_method": generation_method,
            "material_context": material_context,
            "creative_brief": task_brief,
        },
    )
    if material_context:
        record_material_usage(
            base.name,
            "channel_content",
            target,
            str(material_context.get("task_material_pack_id") or ""),
            artifact_id,
        )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_artifact_markdown(base.name, artifact_id, target, packs), encoding="utf-8")
    raw_path = base / "raw" / "generated-content" / f"{artifact_id}.md"
    raw_path.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    append_jsonl(
        base / "structured" / "artifact_index.jsonl",
        {
            "artifact_id": artifact_id,
            "target": target,
            "artifact_type": target_spec["artifact_type"],
            "created_at": payload["created_at"],
            "generation_method": generation_method,
            "grounding_status": payload["grounding_audit"]["status"],
            "json": str(json_path.relative_to(base)),
            "markdown": str(md_path.relative_to(base)),
        },
    )
    _create_experiment_page(base, artifact_id, target, packs)
    update_index_and_log(
        base,
        "generate",
        f"{target} {artifact_id}",
        [str(json_path.relative_to(base)), str(md_path.relative_to(base))],
    )
    return {
        "success": True,
        "product_id": base.name,
        "artifact_id": artifact_id,
        "artifact_json": str(json_path),
        "artifact_markdown": str(md_path),
        "generation_method": generation_method,
        "fallback_reason": payload.get("fallback_reason", ""),
        "grounding_status": payload["grounding_audit"]["status"],
        "grounding_warning_count": len(quality_warnings),
        "material_context": material_context,
        "generation_snapshot": generation_snapshot,
        "variants": packs,
    }
