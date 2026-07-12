"""Provider generation job execution for Product Creative."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json
from .provider_config import provider_api_key as _provider_api_key, provider_endpoint as _provider_endpoint, provider_model as _provider_model
from .provider_contracts import GENERATION_JOB_SCHEMA_VERSION, GENERATION_RESULT_SCHEMA_VERSION
from .provider_http import post_json as _post_json
from .provider_io import download_image_asset as _download_image
from .provider_paths import resolve_payload_path as _resolve_payload_path, resolve_video_policy_path as _resolve_video_policy_path
from .provider_readiness import check_live_readiness
from .provider_registry import provider_entry as _provider_entry
from .provider_response import find_urls as _find_urls
from .provider_validation import validate_payload_doc as _validate_payload_doc
from .provider_video_tasks import write_live_video_task as _write_live_video_task


__all__ = ["create_generation_job"]


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _build_provider_request(payload: Dict[str, Any], provider: Dict[str, Any], mode: str) -> Dict[str, Any]:
    request = payload.get("request") or {}
    draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
    http = {}
    if provider.get("endpoint") or provider.get("endpoint_env"):
        http = {
            "method": "POST",
            "endpoint": provider.get("endpoint") or f"env:{provider.get('endpoint_env')}",
            "auth": "bearer_env" if provider.get("auth_env") else "none",
            "model": provider.get("model") or f"env:{provider.get('model_env')}",
            "response_format": provider.get("request_defaults", {}).get("response_format", ""),
        }
    execute_state = "not_executed"
    if mode == "mock":
        execute_state = "mock_only"
    elif mode == "live":
        execute_state = "live"
    return {
        "provider": provider.get("name", "generic"),
        "operation": f"generate_{payload.get('brief_type')}",
        "mode": mode,
        "target": payload.get("target", {}),
        "request": request,
        "provider_body_draft": draft.get("body", {}),
        "body_ready_for_live": bool(draft.get("body_ready_for_live")) if draft else True,
        "unresolved_reference_assets": draft.get("unresolved_reference_assets", []) if draft else [],
        "http": http,
        "prompt_mapping": {
            "source": "image_brief.generation_contract.prompt" if payload.get("brief_type") == "image" else "video_brief.generation_contract.prompt",
            "status": "adapted" if request.get("prompt_adapter") else "direct_mapping",
            "adapter_schema_version": (request.get("prompt_adapter") or {}).get("schema_version", ""),
            "deferred": "Provider-specific prompt optimization remains reviewable and should be improved after result feedback.",
        },
        "adapter_contract": {
            "validate": "implemented",
            "build_request": "implemented",
            "execute": execute_state,
            "normalize_result": (
                "implemented_for_live_image"
                if mode == "live" and payload.get("brief_type") == "image"
                else "implemented_for_async_video_task_submission"
                if mode == "live" and payload.get("brief_type") == "video"
                else "implemented_for_mock"
            ),
        },
    }


def _result_markdown(result: Dict[str, Any]) -> str:
    lines = [
        f"# {result['result_id']}",
        "",
        f"Job: {result['job_id']}",
        f"Provider: {result['provider']}",
        f"Type: {result['brief_type']}",
        f"Status: {result['status']}",
        f"External call performed: {result['external_call_performed']}",
        "",
        "## Summary",
        "",
        result.get("summary", ""),
        "",
        "## Outputs",
        "",
    ]
    for item in result.get("outputs") or []:
        lines.append(f"- {item.get('type')}: {item.get('description')}")
    lines.append("")
    return "\n".join(lines)


def _write_mock_result(base: Path, job: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    brief_type = payload.get("brief_type")
    result_id = f"{brief_type}-result-{timestamp()}"
    out_dir = base / "artifacts" / ("generated_images" if brief_type == "image" else "generated_videos")
    extension = "png" if brief_type == "image" else "mp4"
    result = {
        "schema_version": GENERATION_RESULT_SCHEMA_VERSION,
        "result_id": result_id,
        "job_id": job["job_id"],
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": job["provider"],
        "brief_type": brief_type,
        "mode": "mock",
        "status": "mocked",
        "external_call_performed": False,
        "source_payload_id": payload.get("payload_id", ""),
        "outputs": [
            {
                "type": brief_type,
                "path": "",
                "mime_type": f"{brief_type}/{extension}",
                "mock": True,
                "description": f"Mock {brief_type} output placeholder. No binary file was generated.",
            }
        ],
        "review": {
            "requires_human_review": True,
            "ready_for_feedback": True,
            "notes": "Mock result for workflow validation. Human review is required before learning or Product Brain evolution.",
        },
        "summary": f"Validated {brief_type} request and produced a mock result without external provider calls.",
    }
    json_path = out_dir / f"{result_id}.json"
    md_path = out_dir / f"{result_id}.md"
    write_json(json_path, result)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_result_markdown(result), encoding="utf-8")
    return {"result": result, "files": {"json": str(json_path), "markdown": str(md_path)}}


def _live_image_body(payload: Dict[str, Any], provider: Dict[str, Any]) -> Dict[str, Any]:
    request = payload.get("request") or {}
    defaults = provider.get("request_defaults") or {}
    body = {
        "model": _provider_model(provider),
        "prompt": _text(request.get("prompt")),
        "response_format": defaults.get("response_format", "url"),
        "size": defaults.get("size", "2K"),
        "stream": bool(defaults.get("stream", False)),
        "watermark": bool(defaults.get("watermark", True)),
    }
    if defaults.get("sequential_image_generation"):
        body["sequential_image_generation"] = defaults.get("sequential_image_generation")
    return body


def _write_live_image_result(
    base: Path,
    job: Dict[str, Any],
    payload: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    endpoint = _provider_endpoint(provider)
    api_key = _provider_api_key(provider)
    if not endpoint:
        raise RuntimeError("provider endpoint is not configured")
    if provider.get("auth_env") and not api_key:
        raise RuntimeError(f"provider auth env is missing: {provider.get('auth_env')}")

    body = _live_image_body(payload, provider)
    response_payload = _post_json(endpoint, body, api_key)
    urls = _find_urls(response_payload)
    if not urls:
        raise RuntimeError("provider response did not contain an image URL")

    result_id = f"image-result-{timestamp()}"
    out_dir = base / "artifacts" / "generated_images"
    downloaded = _download_image(urls[0], out_dir, f"image-output-{timestamp()}")
    result = {
        "schema_version": GENERATION_RESULT_SCHEMA_VERSION,
        "result_id": result_id,
        "job_id": job["job_id"],
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": job["provider"],
        "provider_status": provider.get("status", ""),
        "model": body.get("model", ""),
        "brief_type": "image",
        "mode": "live",
        "status": "completed",
        "external_call_performed": True,
        "source_payload_id": payload.get("payload_id", ""),
        "source_brief_id": payload.get("source_brief_id", ""),
        "remote_url": urls[0],
        "outputs": [
            {
                "type": "image",
                "path": str(Path(downloaded["path"]).resolve().relative_to(base)),
                "mime_type": downloaded["mime_type"],
                "bytes": int(downloaded["bytes"]),
                "mock": False,
                "description": "Live image generated by provider and downloaded to local artifact storage.",
            }
        ],
        "provider_request": {
            "endpoint": endpoint,
            "model": body.get("model", ""),
            "size": body.get("size", ""),
            "response_format": body.get("response_format", ""),
            "watermark": body.get("watermark", True),
            "prompt_mapping": "M0.6.5 adapted image prompt from image_brief.generation_contract.prompt",
            "prompt_adapter": (payload.get("request") or {}).get("prompt_adapter", {}),
        },
        "provider_response": {
            "url_count": len(urls),
            "top_level_keys": sorted(response_payload.keys()) if isinstance(response_payload, dict) else [],
        },
        "review": {
            "requires_human_review": True,
            "ready_for_feedback": True,
            "notes": "Live image result. Human review is required before Product Brain evolution.",
        },
        "summary": "Generated a live image through the provider and stored the downloaded file locally.",
    }
    json_path = out_dir / f"{result_id}.json"
    md_path = out_dir / f"{result_id}.md"
    write_json(json_path, result)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_result_markdown(result), encoding="utf-8")
    return {"result": result, "files": {"json": str(json_path), "markdown": str(md_path), "image": downloaded["path"]}}


def _job_markdown(job: Dict[str, Any]) -> str:
    lines = [
        f"# {job['job_id']}",
        "",
        f"Provider: {job['provider']}",
        f"Mode: {job['mode']}",
        f"Status: {job['status']}",
        f"Payload: {job['source_payload_id']}",
        f"Brief type: {job['brief_type']}",
        f"External call performed: {job['external_call_performed']}",
        "",
        "## Validation",
        "",
        f"- Status: {job['validation']['status']}",
    ]
    for item in job["validation"].get("errors") or []:
        lines.append(f"- Error: {item}")
    for item in job["validation"].get("warnings") or []:
        lines.append(f"- Warning: {item}")
    lines.append("")
    return "\n".join(lines)


def create_generation_job(
    product_id: str,
    payload: str,
    provider: str = "generic",
    mode: str = "mock",
    execution_policy: str = "",
) -> Dict[str, Any]:
    if mode not in {"dry_run", "mock", "live"}:
        raise ValueError("supported modes are dry_run, mock, live")

    base = ensure_product(product_id)
    payload_path = _resolve_payload_path(base, payload)
    payload_doc = read_json(payload_path, {})
    entry = _provider_entry(provider)
    if mode not in _list(entry.get("supported_modes")):
        raise ValueError(f"provider '{entry.get('name')}' does not support mode '{mode}'")

    validation = _validate_payload_doc(payload_doc, entry)
    policy_doc: Dict[str, Any] = {}
    policy_path: Path | None = None
    if mode == "live":
        brief_type = payload_doc.get("brief_type")
        if brief_type == "image":
            readiness = check_live_readiness(base.name, entry.get("name", provider), "image", str(payload_path))
        elif brief_type == "video" and entry.get("adapter") == "async-video-task":
            readiness = check_live_readiness(base.name, entry.get("name", provider), "video", str(payload_path))
            if not execution_policy:
                raise ValueError("live video execution requires an approved video execution policy")
            policy_path = _resolve_video_policy_path(base, execution_policy)
            policy_doc = read_json(policy_path, {})
            if policy_doc.get("status") != "approved" or not bool(policy_doc.get("external_call_allowed")):
                raise ValueError("video execution policy is not approved for live execution")
            if policy_doc.get("payload_id") != payload_doc.get("payload_id", payload_path.stem):
                raise ValueError("video execution policy does not match the provider payload")
        else:
            raise ValueError("live execution supports image payloads and async video task payloads only")
        if not readiness["ready_for_live"]:
            raise ValueError("provider is not ready for live execution: " + "; ".join(readiness["blockers"]))
    provider_request = _build_provider_request(payload_doc, entry, mode)
    job_id = f"generation-job-{timestamp()}-{payload_doc.get('brief_type', 'unknown')}"
    job = {
        "schema_version": GENERATION_JOB_SCHEMA_VERSION,
        "job_id": job_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": entry.get("name", provider),
        "mode": mode,
        "status": "failed" if validation["status"] != "valid" else ("mocked" if mode == "mock" else "validated"),
        "external_call_performed": False,
        "brief_type": payload_doc.get("brief_type", ""),
        "source_payload_id": payload_doc.get("payload_id", payload_path.stem),
        "source_payload_path": str(payload_path.relative_to(base)),
        "validation": validation,
        "provider_request": provider_request,
        "result_id": "",
        "result_path": "",
        "video_task_id": "",
        "video_task_path": "",
        "execution_policy_id": policy_doc.get("policy_id", ""),
        "execution_policy_path": str(policy_path.relative_to(base)) if policy_path else "",
        "execution_contract": {
            "live_execution_supported": bool(entry.get("execute_supported")),
            "requires_human_confirmation_before_live": True,
            "result_requires_human_review": True,
        },
    }

    result_bundle: Dict[str, Any] = {"result": None, "files": {}}
    task_bundle: Dict[str, Any] = {"task": None, "files": {}}
    if validation["status"] == "valid" and mode == "mock":
        result_bundle = _write_mock_result(base, job, payload_doc)
        job["result_id"] = result_bundle["result"]["result_id"]
        job["result_path"] = str(Path(result_bundle["files"]["json"]).resolve().relative_to(base))
    elif validation["status"] == "valid" and mode == "live":
        if payload_doc.get("brief_type") == "image":
            result_bundle = _write_live_image_result(base, job, payload_doc, entry)
            job["status"] = "completed"
            job["external_call_performed"] = True
            job["result_id"] = result_bundle["result"]["result_id"]
            job["result_path"] = str(Path(result_bundle["files"]["json"]).resolve().relative_to(base))
        else:
            task_bundle = _write_live_video_task(base, job, payload_doc, entry)
            job["status"] = "submitted"
            job["external_call_performed"] = True
            job["video_task_id"] = task_bundle["task"]["video_task_id"]
            job["video_task_path"] = str(Path(task_bundle["files"]["json"]).resolve().relative_to(base))

    out_dir = base / "artifacts" / "generation_jobs"
    json_path = out_dir / f"{job_id}.json"
    md_path = out_dir / f"{job_id}.md"
    write_json(json_path, job)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_job_markdown(job), encoding="utf-8")
    append_jsonl(
        base / "structured" / "generation_job_index.jsonl",
        {
            "job_id": job_id,
            "created_at": job["created_at"],
            "provider": job["provider"],
            "mode": job["mode"],
            "status": job["status"],
            "source_payload_id": job["source_payload_id"],
            "result_id": job["result_id"],
            "video_task_id": job["video_task_id"],
        },
    )
    update_index_and_log(
        base,
        "generation-job",
        job_id,
        [f"Provider: {job['provider']}", f"Mode: {mode}", f"Status: {job['status']}"],
    )
    return {
        "success": validation["status"] == "valid",
        "product_id": base.name,
        "job_id": job_id,
        "status": job["status"],
        "provider": job["provider"],
        "mode": mode,
        "external_call_performed": bool(job["external_call_performed"]),
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "result_files": result_bundle["files"],
        "video_task_files": task_bundle["files"],
        "job": job,
        "result": result_bundle["result"],
        "video_task": task_bundle["task"],
    }


