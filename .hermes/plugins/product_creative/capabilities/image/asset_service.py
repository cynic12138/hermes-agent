"""Image capability service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ..material.asset_service import register_material_asset
from ..material.card_service import rebuild_material_cards, rebuild_material_library_map
from ...providers import check_live_readiness, create_generation_job, prepare_provider_payload, validate_provider_payload

from .shared import _list, _rel, _resolve_json_artifact, _text

SELECTED_IMAGE_ASSET_SCHEMA_VERSION = "product_creative.selected_image_asset.v4.7"

def register_selected_image_asset(
    product_id: str,
    result: str,
    role: str = "generated_candidate",
    description: str = "",
    confirmed: bool = False,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    clean_role = _text(role) or "generated_candidate"
    if clean_role == "current_main_image" and not confirmed:
        raise ValueError("promoting a generated image to current_main_image requires explicit confirmation")
    result_path = _resolve_json_artifact(base, result, "generated_images", "result_id")
    result_payload = read_json(result_path, {})
    outputs = [item for item in _list(result_payload.get("outputs")) if isinstance(item, dict)]
    if not outputs:
        raise ValueError("generation result has no image outputs")
    output = outputs[0]
    image_rel = _text(output.get("path"))
    image_path = (base / image_rel).resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"generated image file is missing: {image_rel}")
    usage = ["image_reference", "ecommerce_reference"]
    if clean_role == "current_main_image":
        usage.append("product_reference")
    asset_result = register_material_asset(
        base.name,
        str(image_path),
        clean_role,
        _text(description) or f"Selected generated image from {result_payload.get('result_id', result_path.stem)}.",
        usage,
    )
    asset_path = Path(asset_result["files"]["json"])
    asset_payload = read_json(asset_path, {})
    asset_payload["schema_version"] = SELECTED_IMAGE_ASSET_SCHEMA_VERSION
    asset_payload["generation_source"] = {
        "source_result_id": result_payload.get("result_id", result_path.stem),
        "source_result_path": _rel(base, result_path),
        "source_job_id": result_payload.get("job_id", ""),
        "source_provider": result_payload.get("provider", ""),
        "selected_at": now_iso(),
    }
    write_json(asset_path, asset_payload)
    card_result = rebuild_material_cards(base.name)
    map_result = rebuild_material_library_map(base.name)
    append_jsonl(
        base / "structured" / "selected_image_asset_index.jsonl",
        {
            "created_at": asset_payload["generation_source"]["selected_at"],
            "material_id": asset_result.get("material_id"),
            "role": clean_role,
            "source_result_id": result_payload.get("result_id", result_path.stem),
            "path": _rel(base, asset_path),
        },
    )
    update_index_and_log(base, "selected-image-asset", asset_result.get("material_id", ""), [f"Role: {clean_role}"])
    return {
        "success": True,
        "schema_version": SELECTED_IMAGE_ASSET_SCHEMA_VERSION,
        "product_id": base.name,
        "material_id": asset_result.get("material_id"),
        "role": clean_role,
        "files": asset_result.get("files", {}),
        "asset": asset_payload,
        "material_cards": card_result,
        "material_library_map": map_result,
    }
