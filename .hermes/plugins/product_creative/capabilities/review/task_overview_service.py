"""Creative task overview service."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state
from ...ports.runtime_repositories import artifacts, materials


TASK_OVERVIEW_SCHEMA_VERSION = "product_creative.task_overview_package.v8.1"

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))

def _latest_json(base: Path, folder: str) -> Dict[str, Any]:
    records = artifacts().list(base.name, folder)
    return sorted(records, key=lambda item: _text(item.get("created_at")))[-1] if records else {}

def _resolve_result(base: Path, result: str) -> Dict[str, Any]:
    if result:
        candidate = Path(result)
        if candidate.exists():
            resolved = candidate.resolve()
            if base.resolve() == resolved or base.resolve() in resolved.parents:
                return read_json(resolved, {})
        name = result if result.endswith(".json") else f"{result}.json"
        stored = artifacts().get(base.name, Path(name).stem)
        if stored:
            return stored
        for folder in ["generated_images", "generated_videos"]:
            payload = read_json(base / "artifacts" / folder / name, {})
            if payload:
                return payload
    return _latest_json(base, "generated_videos") or _latest_json(base, "generated_images")

def _artifact_pointer(payload: Dict[str, Any], kind: str) -> Dict[str, Any]:
    if not payload:
        return {"kind": kind, "available": False}
    identity = ""
    for key in [
        "workflow_run_id",
        "result_id",
        "brief_id",
        "payload_id",
        "job_id",
        "feedback_id",
        "result_evaluation_id",
        "proposal_id",
        "pack_id",
        "material_id",
    ]:
        identity = _text(payload.get(key))
        if identity:
            break
    return {
        "kind": kind,
        "available": True,
        "id": identity,
        "status": payload.get("status", ""),
        "created_at": payload.get("created_at", ""),
    }

def _current_main_material(base: Path, state: Dict[str, Any]) -> Dict[str, Any]:
    current_id = _text(((state.get("assets") or {}).get("current_main_image_id")))
    if current_id:
        payload = _resolve_material(base, current_id)[0]
        if payload:
            return payload
    candidates = [
        payload for payload in materials().list(base.name)
        if payload.get("status") == "active" and payload.get("role") == "current_main_image"
    ]
    if candidates:
        return sorted(candidates, key=lambda item: _text(item.get("created_at")))[-1]
    return {}

def create_task_overview_package(
    product_id: str,
    result: str = "",
    workflow_run: str = "",
    title: str = "",
) -> Dict[str, Any]:
    """Create a compact user-facing overview of one product creative task."""

    base = ensure_product(product_id)
    state = apply_generation_safe_state(read_product_state(base))
    safe = state.get("generation_safe") if isinstance(state.get("generation_safe"), dict) else {}
    result_payload = _resolve_result(base, result)
    main_material = _current_main_material(base, state)
    package_id = f"task-overview-{timestamp()}"
    overview = {
        "schema_version": TASK_OVERVIEW_SCHEMA_VERSION,
        "task_overview_package_id": package_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_user_review",
        "title": _text(title) or "Product creative task overview",
        "mutates_product_brain": False,
        "external_call_performed": False,
        "product": {
            "name": safe.get("product_name") or state.get("name", base.name),
            "brief": safe.get("brief") or (state.get("basic") or {}).get("brief", ""),
            "selling_points": _list(safe.get("selling_points")),
            "confirmed_learning": (safe.get("learning") or {}),
        },
        "current_main_image": {
            "material_id": main_material.get("material_id", ""),
            "role": main_material.get("role", ""),
            "stored_path": main_material.get("stored_path", ""),
            "description": main_material.get("description", ""),
        },
        "latest_artifacts": {
            "workflow_run": _artifact_pointer(_latest_json(base, "workflow_runs"), "workflow_run"),
            "inspiration_pack": _artifact_pointer(_latest_json(base, "inspiration_packs"), "inspiration_pack"),
            "image_brief": _artifact_pointer(_latest_json(base, "image_briefs"), "image_brief"),
            "video_brief": _artifact_pointer(_latest_json(base, "video_scripts"), "video_brief"),
            "provider_payload": _artifact_pointer(_latest_json(base, "provider_payloads"), "provider_payload"),
            "generation_job": _artifact_pointer(_latest_json(base, "generation_jobs"), "generation_job"),
            "result": _artifact_pointer(result_payload, "generation_result"),
            "result_review": _artifact_pointer(_latest_json(base, "result_review_packages"), "result_review_package"),
            "result_feedback": _artifact_pointer(_latest_json(base, "result_feedback"), "result_feedback"),
            "result_evaluation": _artifact_pointer(_latest_json(base, "result_evaluations"), "result_evaluation"),
            "evolution_proposal": _artifact_pointer(_latest_json(base, "../structured/evolution_proposals"), "evolution_proposal"),
        },
        "selected_result": {
            "result_id": result_payload.get("result_id", ""),
            "brief_type": result_payload.get("brief_type", ""),
            "provider": result_payload.get("provider", ""),
            "status": result_payload.get("status", ""),
            "outputs": result_payload.get("outputs", []),
            "main_image_policy": result_payload.get("main_image_policy", {}),
            "review": result_payload.get("review", {}),
        },
        "review_questions": [
            "当前结果是否围绕同一个产品生成，而不是脱离 Product Brain？",
            "主图/素材是否被正确使用，是否有被重绘、裁剪、改字或换包装？",
            "文案、画面或视频是否只使用已确认事实和可审阅灵感？",
            "这次反馈是否值得形成 Product Brain proposal，还是只作为单次任务意见？",
        ],
        "next_actions": {
            "review_result": "product_result_review_package",
            "record_feedback": "product_result_feedback",
            "evaluate_result": "product_result_evaluate",
            "apply_learning": "product_evolve after explicit confirmation",
        },
    }
    out_dir = base / "artifacts" / "task_overview_packages"
    json_path = out_dir / f"{package_id}.json"
    md_path = out_dir / f"{package_id}.md"
    write_json(json_path, overview)
    md_path.write_text(_task_overview_markdown(overview), encoding="utf-8")
    append_jsonl(
        base / "structured" / "task_overview_package_index.jsonl",
        {
            "task_overview_package_id": package_id,
            "created_at": overview["created_at"],
            "source_result_id": overview["selected_result"].get("result_id", ""),
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "task-overview-package", package_id, [str(json_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "task_overview_package_id": package_id,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "package": overview,
    }

def _task_overview_markdown(package: Dict[str, Any]) -> str:
    lines = [
        f"# {package['task_overview_package_id']}",
        "",
        f"Product: {package['product'].get('name', '')}",
        f"Status: {package['status']}",
        "",
        "## Product Brain Summary",
        "",
        package["product"].get("brief", ""),
        "",
        "## Current Main Image",
        "",
        f"- Material: {package['current_main_image'].get('material_id', '')}",
        f"- Path: {package['current_main_image'].get('stored_path', '')}",
        "",
        "## Latest Artifacts",
        "",
    ]
    for key, item in (package.get("latest_artifacts") or {}).items():
        lines.append(f"- {key}: {item.get('id', '') or 'not available'} ({item.get('status', '')})")
    lines.extend(["", "## Selected Result", ""])
    result = package.get("selected_result") or {}
    lines.append(f"- Result: {result.get('result_id', '')}")
    lines.append(f"- Provider: {result.get('provider', '')}")
    lines.append(f"- Status: {result.get('status', '')}")
    policy = result.get("main_image_policy") or {}
    if policy:
        lines.extend(["", "## Main Image Policy", ""])
        for key, value in policy.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Review Questions", ""])
    lines.extend(f"- {item}" for item in package.get("review_questions", []))
    lines.append("")
    return "\n".join(lines)

def _resolve_material(base: Path, asset: str) -> Tuple[Dict[str, Any], Path]:
    if asset:
        candidate = Path(asset)
        if candidate.exists():
            resolved = candidate.resolve()
            root = base.resolve()
            if resolved != root and root not in resolved.parents:
                raise ValueError("material path must stay inside the product workspace")
            return {}, resolved
        name = asset if asset.endswith(".json") else f"{asset}.json"
        direct = base / "artifacts" / "material_assets" / name
        if direct.exists():
            payload = read_json(direct, {})
            return payload, _material_stored_path(base, payload)
    state = read_product_state(base)
    current_id = _text(((state.get("assets") or {}).get("current_main_image_id")))
    if current_id and current_id != asset:
        return _resolve_material(base, current_id)
    candidates = [
        payload for payload in materials().list(base.name)
        if payload.get("status") == "active" and payload.get("role") == "current_main_image"
    ]
    if not candidates:
        raise FileNotFoundError("no active current_main_image material is available")
    payload = sorted(candidates, key=lambda item: _text(item.get("created_at")))[-1]
    return payload, _material_stored_path(base, payload)

def _material_stored_path(base: Path, material: Dict[str, Any]) -> Path:
    stored = _text(material.get("stored_path"))
    if not stored:
        raise ValueError("material has no stored_path")
    path = base / stored
    if not path.exists():
        raise FileNotFoundError(f"material image does not exist: {stored}")
    return path
