"""Artifact manifest and index builder for Product Creative workspaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import ensure_product, now_iso, read_json, update_index_and_log, write_json


ARTIFACT_MANIFEST_SCHEMA_VERSION = "product_creative.artifact_manifest.v0.5.2"

ARTIFACT_FOLDERS: List[Tuple[str, str]] = [
    ("copy", "copy_pack"),
    ("evaluations", "evaluation"),
    ("image_intents", "image_intent"),
    ("image_briefs", "image_brief"),
    ("image_brief_reviews", "image_brief_review"),
    ("image_brief_patches", "image_brief_patch"),
    ("batch_generation_policies", "batch_generation_policy"),
    ("video_scripts", "video_brief"),
    ("provider_payloads", "provider_payload"),
    ("provider_validations", "provider_validation"),
    ("generation_jobs", "generation_job"),
    ("generated_images", "generation_result"),
    ("image_generation_runs", "image_generation_run"),
    ("generated_videos", "generation_result"),
    ("video_reference_readiness", "video_reference_readiness"),
    ("video_execution_policies", "video_execution_policy"),
    ("video_tasks", "video_task"),
    ("video_task_status", "video_task_status"),
    ("channel_content", "channel_content"),
    ("review_packages", "review_package"),
    ("result_review_packages", "result_review_package"),
    ("task_overview_packages", "task_overview_package"),
    ("result_evaluations", "result_evaluation"),
    ("result_feedback", "result_feedback"),
    ("live_readiness", "live_readiness"),
    ("creative_runs", "creative_run"),
    ("image_qa", "image_qa"),
    ("comparison_packages", "comparison_package"),
    ("wiki_lint", "wiki_lint"),
    ("state_exports", "state_export"),
    ("channel_evaluations", "channel_evaluation"),
    ("channel_feedback", "channel_feedback"),
    ("video_brief_feedback", "video_brief_feedback"),
    ("channel_review_packages", "channel_review_package"),
    ("channel_review_runs", "channel_review_run"),
    ("material_assets", "material_asset"),
    ("image_analysis", "image_analysis"),
    ("visual_alignments", "visual_alignment"),
    ("material_cards", "material_card"),
    ("material_library", "material_library_map"),
    ("task_material_packs", "task_material_pack"),
    ("material_usage", "material_usage"),
    ("material_feedback", "material_feedback"),
    ("video_intents", "video_intent"),
    ("video_brief_patches", "video_brief_patch"),
    ("workflow_runs", "workflow_run"),
]

ID_FIELDS = [
    "artifact_id",
    "brief_id",
    "payload_id",
    "validation_id",
    "job_id",
    "result_id",
    "review_package_id",
    "result_review_package_id",
    "task_overview_package_id",
    "result_evaluation_id",
    "feedback_id",
    "readiness_id",
    "creative_run_id",
    "qa_id",
    "comparison_package_id",
    "evaluation_id",
    "channel_review_package_id",
    "channel_review_run_id",
    "intent_id",
    "video_task_id",
    "reference_readiness_id",
    "policy_id",
    "video_task_status_id",
    "patch_id",
    "workflow_run_id",
    "material_id",
    "material_card_id",
    "material_library_map_id",
    "task_material_pack_id",
    "usage_id",
]

TYPE_ID_FIELDS = {
    "image_intent": ["intent_id"],
    "image_brief": ["brief_id"],
    "image_brief_review": ["review_id"],
    "image_brief_patch": ["patch_id"],
    "batch_generation_policy": ["policy_id"],
    "video_brief": ["brief_id"],
    "provider_payload": ["payload_id"],
    "provider_validation": ["validation_id"],
    "generation_job": ["job_id"],
    "generation_result": ["result_id"],
    "review_package": ["review_package_id"],
    "result_review_package": ["result_review_package_id"],
    "task_overview_package": ["task_overview_package_id"],
    "result_evaluation": ["result_evaluation_id", "evaluation_id"],
    "result_feedback": ["feedback_id"],
    "channel_feedback": ["feedback_id"],
    "video_brief_feedback": ["feedback_id"],
    "live_readiness": ["readiness_id"],
    "creative_run": ["creative_run_id"],
    "image_qa": ["qa_id"],
    "comparison_package": ["comparison_package_id"],
    "evaluation": ["evaluation_id"],
    "channel_evaluation": ["evaluation_id"],
    "channel_review_package": ["channel_review_package_id"],
    "channel_review_run": ["channel_review_run_id"],
    "image_generation_run": ["image_run_id"],
    "material_asset": ["material_id"],
    "image_analysis": ["analysis_id"],
    "visual_alignment": ["alignment_id"],
    "material_card": ["material_card_id"],
    "material_library_map": ["material_library_map_id"],
    "task_material_pack": ["task_material_pack_id"],
    "material_usage": ["usage_id"],
    "material_feedback": ["feedback_id"],
    "video_intent": ["intent_id"],
    "video_task": ["video_task_id"],
    "video_reference_readiness": ["reference_readiness_id", "readiness_id"],
    "video_execution_policy": ["policy_id"],
    "video_task_status": ["video_task_status_id", "status_id"],
    "video_brief_patch": ["patch_id"],
    "workflow_run": ["workflow_run_id"],
}

PARENT_FIELDS = [
    "source_artifact_id",
    "source_brief_id",
    "source_payload_id",
    "source_result_id",
    "source_evaluation_id",
    "source_intent_id",
    "source_analysis_id",
    "source_alignment_id",
    "source_material_id",
    "task_material_pack_id",
    "material_card_id",
    "source_task_id",
    "remote_task_id",
    "execution_policy_id",
    "job_id",
    "result_id",
]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _artifact_id(payload: Dict[str, Any], fallback: str, artifact_type: str = "") -> str:
    for field in TYPE_ID_FIELDS.get(artifact_type, []):
        value = _text(payload.get(field))
        if value:
            return value
    for field in ID_FIELDS:
        value = _text(payload.get(field))
        if value:
            return value
    return fallback


def _parent_ids(payload: Dict[str, Any]) -> List[str]:
    parents: List[str] = []
    for field in PARENT_FIELDS:
        value = _text(payload.get(field))
        if value and value not in parents:
            parents.append(value)
    for field in ["source_artifacts", "related_artifacts"]:
        for item in _list(payload.get(field)):
            if isinstance(item, dict):
                value = _text(item.get("artifact_id") or item.get("id"))
            else:
                value = _text(item)
            if value and value not in parents:
                parents.append(value)
    return parents


def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def _markdown_path(path: Path) -> str:
    md = path.with_suffix(".md")
    return str(md) if md.exists() else ""


def _artifact_record(base: Path, path: Path, artifact_type: str) -> Dict[str, Any]:
    payload = read_json(path, {})
    return {
        "artifact_id": _artifact_id(payload, path.stem, artifact_type),
        "artifact_type": artifact_type,
        "schema_version": _text(payload.get("schema_version")),
        "created_at": _text(payload.get("created_at")),
        "path": _rel(base, path),
        "markdown_path": _rel(base, Path(_markdown_path(path))) if _markdown_path(path) else "",
        "parent_ids": _parent_ids(payload),
        "external_call_performed": bool(payload.get("external_call_performed")),
        "status": _text(payload.get("status")),
    }


def rebuild_artifact_manifest(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    records: List[Dict[str, Any]] = []
    for folder, artifact_type in ARTIFACT_FOLDERS:
        artifact_dir = base / "artifacts" / folder
        if not artifact_dir.exists():
            continue
        for path in sorted(artifact_dir.glob("*.json")):
            records.append(_artifact_record(base, path, artifact_type))

    records.sort(key=lambda item: (item["created_at"], item["path"]))
    manifest = {
        "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "product_id": base.name,
        "created_at": now_iso(),
        "artifact_count": len(records),
        "artifacts": records,
    }
    json_path = base / "artifacts" / "manifest.json"
    jsonl_path = base / "artifacts" / "manifest.jsonl"
    write_json(json_path, manifest)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.write_text(
        "\n".join(
            json.dumps(item, ensure_ascii=False)
            for item in records
        )
        + ("\n" if records else ""),
        encoding="utf-8",
    )
    update_index_and_log(base, "artifact-manifest", "manifest", [f"{len(records)} artifact(s) indexed"])
    return {
        "success": True,
        "product_id": base.name,
        "artifact_count": len(records),
        "files": {"json": str(json_path), "jsonl": str(jsonl_path)},
        "manifest": manifest,
    }


