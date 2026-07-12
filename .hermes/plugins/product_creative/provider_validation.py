"""Provider payload validation for Product Creative."""

from __future__ import annotations

from typing import Any, Dict, List

from .common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json
from .provider_contracts import PROVIDER_PAYLOAD_SCHEMA_VERSION, PROVIDER_VALIDATION_SCHEMA_VERSION
from .provider_paths import resolve_payload_path as _resolve_payload_path
from .provider_registry import provider_entry as _provider_entry


__all__ = [
    "PROVIDER_VALIDATION_SCHEMA_VERSION",
    "validate_payload_doc",
    "validate_provider_payload",
]


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def validate_payload_doc(payload: Dict[str, Any], provider: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    request = payload.get("request") or {}
    brief_type = payload.get("brief_type")
    prompt = _text(request.get("prompt"))
    supported_types = _list(provider.get("supported_types"))
    limits = provider.get("limits") or {}
    accepted_ratios = _list(provider.get("accepted_aspect_ratios"))

    if payload.get("schema_version") != PROVIDER_PAYLOAD_SCHEMA_VERSION:
        errors.append("unsupported provider payload schema_version")
    if brief_type not in {"image", "video"}:
        errors.append("brief_type must be image or video")
    if supported_types and brief_type not in supported_types:
        errors.append(f"provider does not support {brief_type}")
    if not prompt:
        errors.append("request.prompt is required")
    if accepted_ratios and request.get("aspect_ratio") not in accepted_ratios:
        warnings.append(f"aspect ratio {request.get('aspect_ratio') or ''} is not listed by provider")

    max_prompt_chars = int(limits.get("max_prompt_chars") or 0)
    if max_prompt_chars and len(prompt) > max_prompt_chars:
        warnings.append(f"prompt length {len(prompt)} exceeds provider advisory limit {max_prompt_chars}")

    if brief_type == "image":
        if not _list(request.get("text_to_render")):
            warnings.append("image payload has no text_to_render")
    if brief_type == "video":
        storyboard = _list(request.get("storyboard"))
        if not storyboard:
            errors.append("video payload requires request.storyboard")
        max_shots = int(limits.get("max_storyboard_shots") or 0)
        if max_shots and len(storyboard) > max_shots:
            warnings.append(f"storyboard shot count {len(storyboard)} exceeds provider advisory limit {max_shots}")
        if provider.get("adapter") == "async-video-task":
            draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
            body = draft.get("body") if isinstance(draft.get("body"), dict) else {}
            content = _list(body.get("content"))
            if not draft:
                errors.append("async-video-task payload requires request.provider_request_draft")
            if not body.get("model"):
                errors.append("async-video-task body requires model")
            if not content or not isinstance(content[0], dict) or content[0].get("type") != "text":
                errors.append("async-video-task body.content must start with a text item")
            if accepted_ratios and body.get("ratio") not in accepted_ratios:
                warnings.append(f"provider body ratio {body.get('ratio') or ''} is not listed by provider")
            if int(body.get("duration") or 0) <= 0:
                errors.append("async-video-task body.duration must be positive")
            unresolved = _list(draft.get("unresolved_reference_assets"))
            if unresolved:
                warnings.append("async-video-task has reference assets that MaterialResolver could not convert into provider-ready handles")
            if draft and not bool(draft.get("body_ready_for_live")):
                warnings.append("provider request draft is not ready for live execution")

    payload_provider = _text(payload.get("provider"))
    if payload_provider and payload_provider != provider.get("name"):
        warnings.append(f"payload provider is {payload_provider}, validating against {provider.get('name')}")

    return {
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "warnings": warnings,
        "adapter_contract": {
            "validate": True,
            "build_request": True,
            "execute": bool(provider.get("execute_supported")),
            "normalize_result": True,
        },
    }


def _validation_markdown(validation: Dict[str, Any]) -> str:
    lines = [
        f"# {validation['validation_id']}",
        "",
        f"Provider: {validation['provider']}",
        f"Payload: {validation['payload_id']}",
        f"Brief type: {validation['brief_type']}",
        f"Status: {validation['status']}",
        "",
        "## Errors",
        "",
    ]
    errors = validation.get("errors") or []
    lines.extend([f"- {item}" for item in errors] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    warnings = validation.get("warnings") or []
    lines.extend([f"- {item}" for item in warnings] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def validate_provider_payload(product_id: str, payload: str, provider: str = "generic") -> Dict[str, Any]:
    base = ensure_product(product_id)
    payload_path = _resolve_payload_path(base, payload)
    payload_doc = read_json(payload_path, {})
    entry = _provider_entry(provider)
    details = validate_payload_doc(payload_doc, entry)
    validation_id = f"provider-validation-{timestamp()}"
    validation = {
        "schema_version": PROVIDER_VALIDATION_SCHEMA_VERSION,
        "validation_id": validation_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": entry.get("name", provider),
        "provider_status": entry.get("status", ""),
        "payload_id": payload_doc.get("payload_id", payload_path.stem),
        "payload_path": str(payload_path.relative_to(base)),
        "brief_type": payload_doc.get("brief_type", ""),
        **details,
    }

    out_dir = base / "artifacts" / "provider_validations"
    json_path = out_dir / f"{validation_id}.json"
    md_path = out_dir / f"{validation_id}.md"
    write_json(json_path, validation)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_validation_markdown(validation), encoding="utf-8")
    append_jsonl(
        base / "structured" / "provider_validation_index.jsonl",
        {
            "validation_id": validation_id,
            "created_at": validation["created_at"],
            "provider": validation["provider"],
            "payload_id": validation["payload_id"],
            "status": validation["status"],
        },
    )
    update_index_and_log(
        base,
        "provider-validation",
        validation_id,
        [f"Provider: {validation['provider']}", f"Status: {validation['status']}"],
    )
    return {
        "success": validation["status"] == "valid",
        "product_id": base.name,
        "validation_id": validation_id,
        "status": validation["status"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "validation": validation,
    }


