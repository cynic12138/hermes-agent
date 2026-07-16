"""Provider video task lifecycle and result import for Product Creative."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

from .common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json
from .provider_adapters import is_http_url as _is_http_url
from .provider_config import provider_api_key as _provider_api_key, provider_endpoint as _provider_endpoint
from .provider_contracts import GENERATION_RESULT_SCHEMA_VERSION, VIDEO_TASK_SCHEMA_VERSION, VIDEO_TASK_STATUS_SCHEMA_VERSION
from .provider_http import get_json as _get_json, post_json as _post_json
from .provider_io import download_video_asset as _download_video
from .provider_paths import resolve_video_task_path as _resolve_video_task_path
from .provider_registry import provider_entry as _provider_entry
from .provider_response import (
    find_first_key as _find_first_key,
    find_urls as _find_urls,
    redact_url_credentials as _redact_url_credentials,
    sanitize_urls as _sanitize_urls,
)


__all__ = ["check_video_task_status", "import_video_result", "write_live_video_task"]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _video_task_markdown(task: Dict[str, Any]) -> str:
    lines = [
        f"# {task['video_task_id']}",
        "",
        f"Provider: {task['provider']}",
        f"Status: {task['status']}",
        f"Remote task id: {task.get('remote_task_id', '')}",
        f"Job: {task.get('job_id', '')}",
        f"External call performed: {task['external_call_performed']}",
        "",
        "## Request",
        "",
        f"- Endpoint: {task.get('request', {}).get('endpoint', '')}",
        f"- Model: {task.get('request', {}).get('body', {}).get('model', '')}",
        f"- Ratio: {task.get('request', {}).get('body', {}).get('ratio', '')}",
        f"- Duration: {task.get('request', {}).get('body', {}).get('duration', '')}",
        f"- Generate audio: {task.get('request', {}).get('body', {}).get('generate_audio', False)}",
        "",
        "## Next Step",
        "",
        task.get("next_step", ""),
        "",
    ]
    return "\n".join(lines)


def write_live_video_task(
    base: Path,
    job: Dict[str, Any],
    payload: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    request = payload.get("request") or {}
    draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
    body = draft.get("body") if isinstance(draft.get("body"), dict) else {}
    if not draft:
        raise RuntimeError("video payload is missing provider_request_draft")
    if not draft.get("body_ready_for_live"):
        raise RuntimeError("video payload is not ready for live execution; resolve reference assets into provider-ready handles first")
    endpoint = _provider_endpoint(provider)
    api_key = _provider_api_key(provider)
    if not endpoint:
        raise RuntimeError("provider endpoint is not configured")
    if provider.get("auth_env") and not api_key:
        raise RuntimeError(f"provider auth env is missing: {provider.get('auth_env')}")
    response_payload = _post_json(endpoint, body, api_key)
    remote_task_id = (
        _find_first_key(response_payload, {"task_id", "id", "generation_id", "content_generation_task_id"})
        or f"remote-task-{timestamp()}"
    )
    video_task_id = f"video-task-{timestamp()}"
    task = {
        "schema_version": VIDEO_TASK_SCHEMA_VERSION,
        "video_task_id": video_task_id,
        "remote_task_id": remote_task_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": provider.get("name", job.get("provider", "")),
        "job_id": job.get("job_id", ""),
        "source_payload_id": payload.get("payload_id", ""),
        "source_brief_id": payload.get("source_brief_id", ""),
        "execution_policy_id": job.get("execution_policy_id", ""),
        "status": "submitted",
        "external_call_performed": True,
        "request": {
            "endpoint": endpoint,
            "body": body,
            "body_ready_for_live": True,
        },
        "provider_response": response_payload,
        "result": {
            "available": False,
            "result_url": "",
            "result_id": "",
        },
        "next_step": "Use video-task-status to query the provider task, or video-result-import if the provider result URL is obtained manually.",
    }
    out_dir = base / "artifacts" / "video_tasks"
    json_path = out_dir / f"{video_task_id}.json"
    md_path = out_dir / f"{video_task_id}.md"
    write_json(json_path, task)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_video_task_markdown(task), encoding="utf-8")
    append_jsonl(base / "structured" / "video_task_index.jsonl", {
        "video_task_id": video_task_id,
        "remote_task_id": remote_task_id,
        "created_at": task["created_at"],
        "provider": task["provider"],
        "job_id": task["job_id"],
        "status": task["status"],
    })
    return {"task": task, "files": {"json": str(json_path), "markdown": str(md_path)}}


def _status_endpoint(provider: Dict[str, Any], remote_task_id: str) -> str:
    template = _text(provider.get("status_endpoint"))
    if template:
        return template.replace("{task_id}", urllib.parse.quote(remote_task_id, safe=""))
    endpoint = _provider_endpoint(provider)
    if endpoint:
        return endpoint.rstrip("/") + "/" + urllib.parse.quote(remote_task_id, safe="")
    return ""


def _normalize_video_task_status(provider_status: str, result_url: str) -> str:
    clean = provider_status.strip().lower()
    if result_url:
        return "completed"
    if clean in {"succeeded", "success", "completed", "done", "finished"}:
        return "completed"
    if clean in {"failed", "error", "cancelled", "canceled", "expired"}:
        return "failed"
    if clean in {"queued", "pending", "running", "processing", "in_progress", "submitted"}:
        return "processing"
    return clean or "unknown"


def _provider_task_status(response_payload: Dict[str, Any]) -> str:
    return _find_first_key(response_payload, {"status", "state", "task_status", "phase"})


def _write_video_task_files(base: Path, task: Dict[str, Any]) -> Dict[str, str]:
    out_dir = base / "artifacts" / "video_tasks"
    json_path = out_dir / f"{task['video_task_id']}.json"
    md_path = out_dir / f"{task['video_task_id']}.md"
    write_json(json_path, task)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_video_task_markdown(task), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _generated_video_markdown(result: Dict[str, Any]) -> str:
    lines = [
        f"# {result['result_id']}",
        "",
        f"Video task: {result.get('video_task_id', '')}",
        f"Provider: {result['provider']}",
        f"Status: {result['status']}",
        f"Remote URL: {result.get('remote_url', '')}",
        "",
        "## Outputs",
        "",
    ]
    for item in result.get("outputs") or []:
        lines.append(f"- {item.get('type')}: {item.get('path') or item.get('remote_url')} ({item.get('description')})")
    lines.extend(["", "## Review", "", result.get("review", {}).get("notes", ""), ""])
    return "\n".join(lines)


def _write_generated_video_result(
    base: Path,
    task: Dict[str, Any],
    provider: Dict[str, Any],
    remote_url: str,
    provider_response: Dict[str, Any] | None = None,
    download: bool = True,
    note: str = "",
) -> Dict[str, Any]:
    if not _is_http_url(remote_url):
        raise ValueError("generated video result requires a provider-accessible remote URL")

    persisted_remote_url = _redact_url_credentials(remote_url)
    persisted_provider_response = _sanitize_urls(provider_response or {})
    result_id = f"video-result-{timestamp()}"
    out_dir = base / "artifacts" / "generated_videos"
    outputs: List[Dict[str, Any]] = [
        {
            "type": "video",
            "remote_url": persisted_remote_url,
            "path": "",
            "mime_type": "video/mp4",
            "mock": False,
            "description": "Live video generated by provider. Remote URL is the canonical provider result handle.",
        }
    ]
    download_error = ""
    if download:
        try:
            downloaded = _download_video(remote_url, out_dir, f"video-output-{timestamp()}")
            outputs[0]["path"] = str(Path(downloaded["path"]).resolve().relative_to(base))
            outputs[0]["mime_type"] = downloaded["mime_type"]
            outputs[0]["bytes"] = int(downloaded["bytes"])
            outputs[0]["description"] = "Live video generated by provider and downloaded to local artifact storage."
        except RuntimeError as exc:
            download_error = str(exc)

    result = {
        "schema_version": GENERATION_RESULT_SCHEMA_VERSION,
        "result_id": result_id,
        "job_id": task.get("job_id", ""),
        "video_task_id": task.get("video_task_id", ""),
        "remote_task_id": task.get("remote_task_id", ""),
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": provider.get("name", task.get("provider", "")),
        "provider_status": provider.get("status", ""),
        "brief_type": "video",
        "mode": "live",
        "status": "completed",
        "external_call_performed": True,
        "source_payload_id": task.get("source_payload_id", ""),
        "source_brief_id": task.get("source_brief_id", ""),
        "remote_url": persisted_remote_url,
        "outputs": outputs,
        "provider_response": persisted_provider_response,
        "download_error": download_error,
        "review": {
            "requires_human_review": True,
            "ready_for_feedback": True,
            "notes": "Live video result. Human review and explicit Product Brain proposal/apply are required before learning from this output.",
        },
        "summary": "Imported a live generated video result and made it available for user feedback.",
        "note": note,
    }
    json_path = out_dir / f"{result_id}.json"
    md_path = out_dir / f"{result_id}.md"
    write_json(json_path, result)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_generated_video_markdown(result), encoding="utf-8")
    append_jsonl(
        base / "structured" / "generated_video_index.jsonl",
        {
            "result_id": result_id,
            "created_at": result["created_at"],
            "video_task_id": result["video_task_id"],
            "remote_task_id": result["remote_task_id"],
            "provider": result["provider"],
            "status": result["status"],
            "remote_url": persisted_remote_url,
            "path": outputs[0].get("path", ""),
        },
    )
    update_index_and_log(base, "generated-video", result_id, [f"Task: {result['video_task_id']}", f"Status: {result['status']}"])
    return {"result": result, "files": {"json": str(json_path), "markdown": str(md_path), "video": outputs[0].get("path", "")}}


def _video_task_status_markdown(status_doc: Dict[str, Any]) -> str:
    lines = [
        f"# {status_doc['video_task_status_id']}",
        "",
        f"Video task: {status_doc['video_task_id']}",
        f"Remote task: {status_doc['remote_task_id']}",
        f"Provider: {status_doc['provider']}",
        f"Provider status: {status_doc.get('provider_task_status', '')}",
        f"Normalized status: {status_doc['normalized_status']}",
        f"Result URL: {status_doc.get('result_url', '')}",
        "",
        "## Next Step",
        "",
        status_doc.get("next_step", ""),
        "",
    ]
    return "\n".join(lines)


def check_video_task_status(
    product_id: str,
    task: str,
    provider: str = "",
    download: bool = True,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    task_path = _resolve_video_task_path(base, task)
    task_doc = read_json(task_path, {})
    entry = _provider_entry(provider or _text(task_doc.get("provider")) or "volcengine-ark-video")
    remote_task_id = _text(task_doc.get("remote_task_id"))
    if not remote_task_id:
        raise ValueError("video task does not contain remote_task_id")
    endpoint = _status_endpoint(entry, remote_task_id)
    api_key = _provider_api_key(entry)
    if not endpoint:
        raise RuntimeError("provider status endpoint is not configured")
    if entry.get("auth_env") and not api_key:
        raise RuntimeError(f"provider auth env is missing: {entry.get('auth_env')}")

    response_payload = _get_json(endpoint, api_key)
    urls = _find_urls(response_payload)
    result_url = urls[0] if urls else ""
    persisted_result_url = _redact_url_credentials(result_url)
    persisted_response_payload = _sanitize_urls(response_payload)
    provider_status = _provider_task_status(response_payload)
    normalized = _normalize_video_task_status(provider_status, result_url)
    result_bundle: Dict[str, Any] = {"result": None, "files": {}}
    if normalized == "completed" and result_url:
        result_bundle = _write_generated_video_result(base, task_doc, entry, result_url, response_payload, download)

    status_id = f"video-task-status-{timestamp()}"
    status_doc = {
        "schema_version": VIDEO_TASK_STATUS_SCHEMA_VERSION,
        "video_task_status_id": status_id,
        "status_id": status_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": entry.get("name", provider or task_doc.get("provider", "")),
        "video_task_id": task_doc.get("video_task_id", task_path.stem),
        "remote_task_id": remote_task_id,
        "provider_task_status": provider_status,
        "normalized_status": normalized,
        "result_url": persisted_result_url,
        "result_id": (result_bundle.get("result") or {}).get("result_id", ""),
        "external_call_performed": True,
        "provider_response": persisted_response_payload,
        "next_step": "Review the generated video and record feedback." if result_url else "Check the task again later or import the result URL manually.",
    }
    out_dir = base / "artifacts" / "video_task_status"
    json_path = out_dir / f"{status_id}.json"
    md_path = out_dir / f"{status_id}.md"
    write_json(json_path, status_doc)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_video_task_status_markdown(status_doc), encoding="utf-8")
    append_jsonl(
        base / "structured" / "video_task_status_index.jsonl",
        {
            "video_task_status_id": status_id,
            "created_at": status_doc["created_at"],
            "video_task_id": status_doc["video_task_id"],
            "remote_task_id": remote_task_id,
            "provider": status_doc["provider"],
            "normalized_status": normalized,
            "result_id": status_doc["result_id"],
        },
    )

    task_doc["status"] = normalized
    task_doc["last_status_check_id"] = status_id
    task_doc["last_status_check_path"] = str(json_path.relative_to(base))
    task_doc["result"] = {
        "available": bool(status_doc["result_id"] or result_url),
        "result_url": persisted_result_url,
        "result_id": status_doc["result_id"],
        "result_path": str(Path(result_bundle["files"]["json"]).resolve().relative_to(base)) if result_bundle.get("files", {}).get("json") else "",
    }
    task_doc["next_step"] = status_doc["next_step"]
    _write_video_task_files(base, task_doc)
    update_index_and_log(base, "video-task-status", status_id, [f"Task: {status_doc['video_task_id']}", f"Status: {normalized}"])
    return {
        "success": True,
        "product_id": base.name,
        "video_task_status_id": status_id,
        "video_task_id": status_doc["video_task_id"],
        "normalized_status": normalized,
        "result_url": persisted_result_url,
        "result_id": status_doc["result_id"],
        "external_call_performed": True,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "result_files": result_bundle.get("files", {}),
        "status": status_doc,
        "result": result_bundle.get("result"),
    }


def import_video_result(
    product_id: str,
    task: str,
    url: str,
    provider: str = "",
    note: str = "",
    download: bool = True,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    task_path = _resolve_video_task_path(base, task)
    task_doc = read_json(task_path, {})
    entry = _provider_entry(provider or _text(task_doc.get("provider")) or "volcengine-ark-video")
    result_bundle = _write_generated_video_result(base, task_doc, entry, _text(url), {}, download, note)
    result = result_bundle["result"]
    task_doc["status"] = "completed"
    task_doc["result"] = {
        "available": True,
        "result_url": result["remote_url"],
        "result_id": result["result_id"],
        "result_path": str(Path(result_bundle["files"]["json"]).resolve().relative_to(base)),
    }
    task_doc["next_step"] = "Review the generated video and record feedback."
    _write_video_task_files(base, task_doc)
    return {
        "success": True,
        "product_id": base.name,
        "result_id": result["result_id"],
        "video_task_id": task_doc.get("video_task_id", task_path.stem),
        "files": result_bundle["files"],
        "result": result,
    }


