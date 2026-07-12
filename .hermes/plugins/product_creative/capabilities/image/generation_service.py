"""Image capability service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ..material.pack_service import record_material_usage
from ..review.image_qa_service import qa_image_result
from ..review.review_package_service import create_comparison_package, create_review_package
from ...providers import check_live_readiness, create_generation_job, prepare_provider_payload, validate_provider_payload

from .brief_service import _resolve_image_brief
from .policy_service import BATCH_GENERATION_POLICY_SCHEMA_VERSION
from .shared import _latest_json, _list, _rel, _resolve_json_artifact, _text

IMAGE_GENERATION_RUN_SCHEMA_VERSION = "product_creative.image_generation_run.v4.5"

def _resolve_batch_policy(base: Path, policy: str) -> Dict[str, Any]:
    path = _resolve_json_artifact(base, policy, "batch_generation_policies", "policy_id")
    payload = read_json(path, {})
    if payload.get("schema_version") != BATCH_GENERATION_POLICY_SCHEMA_VERSION:
        raise ValueError("batch generation policy schema is not supported")
    payload["_path"] = _rel(base, path)
    return payload

def _latest_active_policy_for_brief(base: Path, brief: Dict[str, Any]) -> Dict[str, Any]:
    intent_id = _text(brief.get("source_image_intent_id"))
    brief_id = _text(brief.get("brief_id"))
    return _latest_json(
        base,
        "batch_generation_policies",
        "policy_id",
        lambda payload: payload.get("status") == "active"
        and (
            (intent_id and payload.get("source_image_intent_id") == intent_id)
            or (brief_id and payload.get("source_brief_id") == brief_id)
        ),
    ).get("payload", {})

def build_image_provider_payload(product_id: str, brief: str, provider: str = "volcengine-ark-image", batch_policy: str = "") -> Dict[str, Any]:
    base = ensure_product(product_id)
    brief_path, brief_payload = _resolve_image_brief(base, brief)
    policy = _resolve_batch_policy(base, batch_policy) if _text(batch_policy) else _latest_active_policy_for_brief(base, brief_payload)
    if brief_payload.get("status") != "confirmed_for_provider_payload":
        if not policy or policy.get("status") != "active":
            raise ValueError("image brief must be confirmed or covered by an active batch generation policy before provider payload generation")
    provider_name = _text(provider) or _text(policy.get("provider")) or "volcengine-ark-image"
    payload_result = prepare_provider_payload(base.name, str(brief_path), provider_name, "image")
    payload_path = Path(payload_result["files"]["json"])
    payload = read_json(payload_path, {})
    payload["m4_gate"] = {
        "schema_version": "product_creative.image_provider_gate.v4.4",
        "source_brief_status": _text(brief_payload.get("status")),
        "source_batch_policy_id": _text(policy.get("policy_id")),
        "gate_status": "passed",
        "live_requires_confirmation": True,
    }
    write_json(payload_path, payload)
    validation = validate_provider_payload(base.name, str(payload_path), provider_name)
    record_material_usage(
        base.name,
        "provider_payload",
        _text((brief_payload.get("target") or {}).get("channel")),
        _text((brief_payload.get("source_material_pack") or {}).get("task_material_pack_id")),
        payload.get("payload_id", ""),
    )
    return {
        "success": True,
        "schema_version": "product_creative.image_provider_payload_gate.v4.4",
        "product_id": base.name,
        "payload_id": payload.get("payload_id"),
        "provider": provider_name,
        "files": payload_result["files"],
        "validation": validation,
        "payload": payload,
    }

def _ensure_mock_image_file(base: Path, result: Dict[str, Any], result_json: str) -> Dict[str, Any]:
    outputs = [item for item in _list(result.get("outputs")) if isinstance(item, dict)]
    if not outputs or outputs[0].get("path") or not outputs[0].get("mock"):
        return result
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02"
        b"\x00\x00\x00\x0bIDATx\xdacd\xf8\xff\x1f\x00\x03\x03\x02\x00\xef\xbf\xa7\xdb"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    image_path = base / "artifacts" / "generated_images" / f"{result.get('result_id', 'mock-image')}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(png)
    outputs[0]["path"] = _rel(base, image_path)
    outputs[0]["bytes"] = len(png)
    outputs[0]["description"] = "M4 mock image placeholder. This is not a provider-generated production image."
    result["outputs"] = outputs
    review = result.get("review") if isinstance(result.get("review"), dict) else {}
    review["ready_for_feedback"] = True
    review["notes"] = "M4 mock result can collect workflow feedback, but it is not production image quality."
    result["review"] = review
    write_json(Path(result_json), result)
    return result

def create_image_generation_run(
    product_id: str,
    payload: str,
    provider: str = "generic",
    mode: str = "mock",
    count: int = 1,
) -> Dict[str, Any]:
    if mode not in {"dry_run", "mock", "live"}:
        raise ValueError("mode must be dry_run, mock, or live")
    clean_count = max(1, min(int(count or 1), 5))
    base = ensure_product(product_id)
    provider_name = _text(provider) or "generic"
    run_id = f"image-run-{timestamp()}"
    payload_path = _resolve_json_artifact(base, payload, "provider_payloads", "payload_id")
    if mode == "live":
        readiness = check_live_readiness(base.name, provider_name, "image", str(payload_path))
        if not readiness.get("ready_for_live"):
            raise ValueError("provider is not ready for live execution: " + "; ".join(readiness.get("blockers") or []))
    jobs = []
    job_paths: List[str] = []
    external_call_count = 0
    for index in range(clean_count):
        job_result = create_generation_job(base.name, str(payload_path), provider_name, mode)
        result = job_result.get("result") if isinstance(job_result.get("result"), dict) else {}
        if mode == "mock" and job_result.get("result_files", {}).get("json"):
            result = _ensure_mock_image_file(base, result, job_result["result_files"]["json"])
            job_result["result"] = result
        review = create_review_package(base.name, job_result["files"]["json"]) if job_result.get("files", {}).get("json") else {}
        qa = {}
        if result.get("brief_type") == "image" and result.get("outputs"):
            qa = qa_image_result(base.name, job_result["result_files"]["json"])
        if job_result.get("external_call_performed") or result.get("external_call_performed"):
            external_call_count += 1
        jobs.append(
            {
                "index": index + 1,
                "job_id": job_result.get("job_id", ""),
                "job_path": _rel(base, Path(job_result["files"]["json"])),
                "status": job_result.get("status", ""),
                "result_id": result.get("result_id", ""),
                "result_path": _rel(base, Path(job_result["result_files"]["json"])) if job_result.get("result_files", {}).get("json") else "",
                "review_package_id": review.get("review_package_id", ""),
                "review_package_path": _rel(base, Path(review["files"]["json"])) if review.get("files", {}).get("json") else "",
                "qa_id": qa.get("qa_id", ""),
                "qa_status": qa.get("status", ""),
                "qa_path": _rel(base, Path(qa["files"]["json"])) if qa.get("files", {}).get("json") else "",
                "external_call_performed": bool(job_result.get("external_call_performed")) or bool(result.get("external_call_performed")),
            }
        )
        job_paths.append(job_result["files"]["json"])
    comparison = create_comparison_package(base.name, job_paths) if len(job_paths) >= 2 else {}
    run = {
        "schema_version": IMAGE_GENERATION_RUN_SCHEMA_VERSION,
        "image_run_id": run_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "completed" if all(item["status"] in {"mocked", "validated", "completed"} for item in jobs) else "needs_review",
        "provider": provider_name,
        "mode": mode,
        "count": clean_count,
        "external_call_count": external_call_count,
        "source_payload_id": read_json(payload_path, {}).get("payload_id", payload_path.stem),
        "source_payload_path": _rel(base, payload_path),
        "jobs": jobs,
        "comparison_package": {
            "id": comparison.get("comparison_package_id", ""),
            "path": _rel(base, Path(comparison["files"]["json"])) if comparison.get("files", {}).get("json") else "",
        },
        "requires_human_review": True,
        "next_steps": [
            "Review generated image candidates.",
            "Record image result feedback for the selected result.",
            "Register selected image as generated_candidate if it should return to the material library.",
        ],
    }
    out_dir = base / "artifacts" / "image_generation_runs"
    json_path = out_dir / f"{run_id}.json"
    md_path = out_dir / f"{run_id}.md"
    write_json(json_path, run)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(f"# {run_id}\n\nStatus: {run['status']}\nCount: {clean_count}\n", encoding="utf-8")
    append_jsonl(
        base / "structured" / "image_generation_run_index.jsonl",
        {
            "image_run_id": run_id,
            "created_at": run["created_at"],
            "provider": provider_name,
            "mode": mode,
            "count": clean_count,
            "external_call_count": external_call_count,
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "image-generation-run", run_id, [f"Mode: {mode}", f"Count: {clean_count}"])
    return {
        "success": True,
        "schema_version": IMAGE_GENERATION_RUN_SCHEMA_VERSION,
        "product_id": base.name,
        "image_run_id": run_id,
        "status": run["status"],
        "external_call_count": external_call_count,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "image_generation_run": run,
    }
