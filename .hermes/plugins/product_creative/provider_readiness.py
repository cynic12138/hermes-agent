"""Provider readiness gates and video execution policy artifacts."""

from __future__ import annotations

from typing import Any, Dict, List

from .common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json
from .provider_adapters import is_data_url as _is_data_url, is_http_url as _is_http_url
from .provider_config import provider_endpoint, provider_model
from .provider_contracts import (
    LIVE_READINESS_SCHEMA_VERSION,
    VIDEO_EXECUTION_POLICY_SCHEMA_VERSION,
    VIDEO_REFERENCE_READINESS_SCHEMA_VERSION,
)
from .provider_paths import resolve_payload_path as _resolve_payload_path
from .provider_registry import env_value as _env_value, provider_entry as _provider_entry
from .provider_validation import validate_payload_doc


__all__ = [
    "LIVE_READINESS_SCHEMA_VERSION",
    "VIDEO_EXECUTION_POLICY_SCHEMA_VERSION",
    "VIDEO_REFERENCE_READINESS_SCHEMA_VERSION",
    "check_live_readiness",
    "check_video_reference_readiness",
    "create_video_execution_policy",
]


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _video_reference_readiness_markdown(readiness: Dict[str, Any]) -> str:
    lines = [
        f"# {readiness['reference_readiness_id']}",
        "",
        f"Payload: {readiness['payload_id']}",
        f"Status: {readiness['status']}",
        f"Ready for provider: {readiness['ready_for_provider']}",
        "",
        "## References",
        "",
    ]
    for item in readiness.get("references") or []:
        lines.append(f"- {item.get('type')}: {item.get('url')} ({item.get('status')})")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- {item}" for item in readiness.get("blockers", [])] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in readiness.get("warnings", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def check_video_reference_readiness(product_id: str, payload: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    payload_path = _resolve_payload_path(base, payload)
    payload_doc = read_json(payload_path, {})
    if payload_doc.get("brief_type") != "video":
        raise ValueError("video reference readiness requires a video provider payload")

    request = payload_doc.get("request") if isinstance(payload_doc.get("request"), dict) else {}
    draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
    body = draft.get("body") if isinstance(draft.get("body"), dict) else {}
    content = _list(body.get("content"))
    blockers: List[str] = []
    warnings: List[str] = []
    references: List[Dict[str, Any]] = []

    for item in content:
        if not isinstance(item, dict):
            continue
        ref_type = ""
        url = ""
        if isinstance(item.get("image_url"), dict):
            ref_type = "image_url"
            url = _text(item["image_url"].get("url"))
        elif isinstance(item.get("video_url"), dict):
            ref_type = "video_url"
            url = _text(item["video_url"].get("url"))
        elif isinstance(item.get("audio_url"), dict):
            ref_type = "audio_url"
            url = _text(item["audio_url"].get("url"))
        if not ref_type:
            continue
        status = "ready" if (_is_http_url(url) or _is_data_url(url) or url.startswith("asset://")) and not url.startswith("<public-url-for-") else "blocked"
        references.append(
            {
                "type": ref_type,
                "role": _text(item.get("role")),
                "url": url,
                "status": status,
            }
        )
        if status != "ready":
            blockers.append(f"{ref_type} reference is not a provider-ready handle: {url or '<empty>'}")

    unresolved = _list(draft.get("unresolved_reference_assets"))
    for item in unresolved:
        if not isinstance(item, dict):
            continue
        asset_id = _text(item.get("asset_id")) or _text(item.get("local_reference")) or "<unknown-asset>"
        blockers.append(f"reference asset '{asset_id}' needs asset-bind-url before live video generation")

    if not draft:
        blockers.append("provider payload is missing provider_request_draft")
    if not references:
        warnings.append("no reference media URLs were found; this may become text-to-video rather than image-to-video")
    if draft and not bool(draft.get("body_ready_for_live")) and not blockers:
        blockers.append("provider_request_draft.body_ready_for_live is false")

    ready = not blockers
    readiness_id = f"video-reference-readiness-{timestamp()}"
    readiness = {
        "schema_version": VIDEO_REFERENCE_READINESS_SCHEMA_VERSION,
        "reference_readiness_id": readiness_id,
        "readiness_id": readiness_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "payload_id": payload_doc.get("payload_id", payload_path.stem),
        "payload_path": str(payload_path.relative_to(base)),
        "source_brief_id": payload_doc.get("source_brief_id", ""),
        "status": "ready" if ready else "blocked",
        "ready_for_provider": ready,
        "body_ready_for_live": bool(draft.get("body_ready_for_live")) if draft else False,
        "references": references,
        "unresolved_reference_assets": unresolved,
        "blockers": blockers,
        "warnings": warnings,
        "external_call_performed": False,
    }
    out_dir = base / "artifacts" / "video_reference_readiness"
    json_path = out_dir / f"{readiness_id}.json"
    md_path = out_dir / f"{readiness_id}.md"
    write_json(json_path, readiness)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_video_reference_readiness_markdown(readiness), encoding="utf-8")
    append_jsonl(
        base / "structured" / "video_reference_readiness_index.jsonl",
        {
            "reference_readiness_id": readiness_id,
            "created_at": readiness["created_at"],
            "payload_id": readiness["payload_id"],
            "status": readiness["status"],
            "ready_for_provider": readiness["ready_for_provider"],
        },
    )
    update_index_and_log(
        base,
        "video-reference-readiness",
        readiness_id,
        [f"Payload: {readiness['payload_id']}", f"Status: {readiness['status']}"],
    )
    return {
        "success": True,
        "product_id": base.name,
        "reference_readiness_id": readiness_id,
        "status": readiness["status"],
        "ready_for_provider": ready,
        "blockers": blockers,
        "warnings": warnings,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "readiness": readiness,
    }


def _video_execution_policy_markdown(policy: Dict[str, Any]) -> str:
    lines = [
        f"# {policy['policy_id']}",
        "",
        f"Payload: {policy['payload_id']}",
        f"Provider: {policy['provider']}",
        f"Mode: {policy['mode']}",
        f"Status: {policy['status']}",
        f"Confirmed: {policy['confirmed']}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- {item}" for item in policy.get("blockers", [])] or ["- None"])
    lines.extend(["", "## Note", "", policy.get("note", ""), ""])
    return "\n".join(lines)


def create_video_execution_policy(
    product_id: str,
    payload: str,
    provider: str = "volcengine-ark-video",
    mode: str = "live",
    confirmed: bool = False,
    note: str = "",
) -> Dict[str, Any]:
    if mode != "live":
        raise ValueError("M5 video execution policy currently supports live mode only")
    base = ensure_product(product_id)
    payload_path = _resolve_payload_path(base, payload)
    payload_doc = read_json(payload_path, {})
    if payload_doc.get("brief_type") != "video":
        raise ValueError("video execution policy requires a video provider payload")

    readiness = check_live_readiness(base.name, provider, "video", str(payload_path))
    blockers = list(readiness.get("blockers") or [])
    if not confirmed:
        blockers.append("human confirmation is required before live video task submission")
    approved = bool(confirmed and readiness.get("ready_for_live") and not readiness.get("blockers"))
    policy_id = f"video-execution-policy-{timestamp()}"
    policy = {
        "schema_version": VIDEO_EXECUTION_POLICY_SCHEMA_VERSION,
        "policy_id": policy_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "payload_id": payload_doc.get("payload_id", payload_path.stem),
        "payload_path": str(payload_path.relative_to(base)),
        "source_brief_id": payload_doc.get("source_brief_id", ""),
        "provider": provider,
        "mode": mode,
        "status": "approved" if approved else "blocked",
        "confirmed": bool(confirmed),
        "external_call_allowed": approved,
        "external_call_performed": False,
        "blockers": blockers,
        "readiness_id": readiness.get("readiness_id", ""),
        "readiness_path": (readiness.get("files") or {}).get("json", ""),
        "note": note,
        "limits": {
            "default_live_video_calls_for_m5_validation": 1,
            "requires_reconfirmation_above_two_calls": True,
        },
        "safety": {
            "mutates_product_brain": False,
            "requires_result_feedback_before_learning": True,
            "requires_explicit_product_brain_apply": True,
        },
    }
    out_dir = base / "artifacts" / "video_execution_policies"
    json_path = out_dir / f"{policy_id}.json"
    md_path = out_dir / f"{policy_id}.md"
    write_json(json_path, policy)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_video_execution_policy_markdown(policy), encoding="utf-8")
    append_jsonl(
        base / "structured" / "video_execution_policy_index.jsonl",
        {
            "policy_id": policy_id,
            "created_at": policy["created_at"],
            "payload_id": policy["payload_id"],
            "provider": policy["provider"],
            "mode": policy["mode"],
            "status": policy["status"],
            "confirmed": policy["confirmed"],
        },
    )
    update_index_and_log(
        base,
        "video-execution-policy",
        policy_id,
        [f"Payload: {policy['payload_id']}", f"Status: {policy['status']}"],
    )
    return {
        "success": True,
        "product_id": base.name,
        "policy_id": policy_id,
        "status": policy["status"],
        "external_call_allowed": approved,
        "blockers": blockers,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "policy": policy,
    }




def _readiness_markdown(readiness: Dict[str, Any]) -> str:
    lines = [
        f"# {readiness['readiness_id']}",
        "",
        f"Provider: {readiness['provider']}",
        f"Kind: {readiness['kind']}",
        f"Status: {readiness['status']}",
        f"Ready for live: {readiness['ready_for_live']}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- {item}" for item in readiness.get("blockers", [])] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in readiness.get("warnings", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def check_live_readiness(
    product_id: str,
    provider: str = "generic",
    kind: str | None = None,
    payload: str | None = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    entry = _provider_entry(provider)
    payload_doc: Dict[str, Any] = {}
    payload_path: Path | None = None
    if payload:
        payload_path = _resolve_payload_path(base, payload)
        payload_doc = read_json(payload_path, {})
        kind = kind or payload_doc.get("brief_type")
    clean_kind = kind or ""

    blockers: List[str] = []
    warnings: List[str] = []
    supported_types = _list(entry.get("supported_types"))
    supported_modes = _list(entry.get("supported_modes"))
    required_config = _list(entry.get("requires_config"))
    required_config_any = _list(entry.get("requires_config_any"))

    if clean_kind and clean_kind not in supported_types:
        blockers.append(f"provider does not support {clean_kind}")
    if "live" not in supported_modes:
        blockers.append("provider does not declare live mode support")
    if not bool(entry.get("execute_supported")):
        blockers.append("provider execute_supported is false")

    missing_config = []
    for item in required_config:
        key = str(item)
        if key and not _env_value(key):
            missing_config.append(key)
    if missing_config:
        blockers.append("missing required environment config: " + ", ".join(missing_config))
    if required_config_any and not any(_env_value(str(item)) for item in required_config_any):
        blockers.append(
            "missing one of required environment config: "
            + ", ".join(str(item) for item in required_config_any)
        )
    if entry.get("endpoint_env") and not provider_endpoint(entry):
        blockers.append(f"missing provider endpoint env: {entry.get('endpoint_env')}")
    if entry.get("model_env") and not provider_model(entry):
        blockers.append(f"missing provider model env: {entry.get('model_env')}")

    validation = None
    if payload_doc:
        validation = validate_payload_doc(payload_doc, entry)
        if validation["status"] != "valid":
            blockers.extend(f"payload invalid: {item}" for item in validation.get("errors", []))
        warnings.extend(validation.get("warnings", []))
        if clean_kind == "video" and entry.get("adapter") == "async-video-task":
            request = payload_doc.get("request") if isinstance(payload_doc.get("request"), dict) else {}
            draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
            if not draft:
                blockers.append("video payload missing provider_request_draft")
            elif not bool(draft.get("body_ready_for_live")):
                blockers.append("video payload is not ready for live execution; resolve reference assets into provider-ready handles first")
    else:
        warnings.append("no provider payload supplied; readiness is provider-level only")

    readiness_id = f"live-readiness-{timestamp()}"
    ready = not blockers
    readiness = {
        "schema_version": LIVE_READINESS_SCHEMA_VERSION,
        "readiness_id": readiness_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": entry.get("name", provider),
        "provider_status": entry.get("status", ""),
        "kind": clean_kind,
        "payload_id": payload_doc.get("payload_id", "") if payload_doc else "",
        "payload_path": str(payload_path.relative_to(base)) if payload_path else "",
        "status": "ready" if ready else "blocked",
        "ready_for_live": ready,
        "blockers": blockers,
        "warnings": warnings,
        "required_config": required_config,
        "required_config_any": required_config_any,
        "missing_config": missing_config,
        "payload_validation": validation,
        "external_call_performed": False,
    }
    out_dir = base / "artifacts" / "live_readiness"
    json_path = out_dir / f"{readiness_id}.json"
    md_path = out_dir / f"{readiness_id}.md"
    write_json(json_path, readiness)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_readiness_markdown(readiness), encoding="utf-8")
    append_jsonl(
        base / "structured" / "live_readiness_index.jsonl",
        {
            "readiness_id": readiness_id,
            "created_at": readiness["created_at"],
            "provider": readiness["provider"],
            "kind": readiness["kind"],
            "status": readiness["status"],
            "ready_for_live": readiness["ready_for_live"],
        },
    )
    update_index_and_log(
        base,
        "live-readiness",
        readiness_id,
        [f"Provider: {readiness['provider']}", f"Status: {readiness['status']}"],
    )
    return {
        "success": True,
        "product_id": base.name,
        "readiness_id": readiness_id,
        "status": readiness["status"],
        "ready_for_live": ready,
        "blockers": blockers,
        "warnings": warnings,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "readiness": readiness,
    }
