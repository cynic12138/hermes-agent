"""Provider payload artifact construction for Product Creative."""

from __future__ import annotations

from typing import Any, Dict

from .common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from .provider_adapters import image_request as _image_request, video_request as _video_request
from .provider_contracts import PROVIDER_PAYLOAD_SCHEMA_VERSION
from .provider_paths import resolve_brief_path as _resolve_brief_path
from .provider_registry import provider_entry as _provider_entry


__all__ = ["prepare_provider_payload"]


def _payload_markdown(payload: Dict[str, Any]) -> str:
    request = payload["request"]
    lines = [
        f"# {payload['payload_id']}",
        "",
        f"Provider: {payload['provider']}",
        f"Mode: {payload['mode']}",
        f"External call performed: {payload['external_call_performed']}",
        f"Brief: {payload['source_brief_id']}",
        f"Type: {payload['brief_type']}",
        f"Aspect ratio: {request.get('aspect_ratio')}",
        "",
        "## Prompt",
        "",
        request.get("prompt") or "",
        "",
    ]
    if payload["brief_type"] == "image":
        lines.extend(["## Text To Render", ""])
        for item in request.get("text_to_render") or []:
            lines.append(f"- {item}")
        lines.append("")
    else:
        lines.extend(["## Storyboard", "", "| Shot | Duration | Description | Caption |", "| --- | --- | --- | --- |"])
        for shot in request.get("storyboard") or []:
            lines.append(
                f"| {shot.get('shot')} | {shot.get('duration')} | {shot.get('description')} | {shot.get('caption')} |"
            )
        lines.append("")

    assets = request.get("reference_assets") or []
    if assets:
        lines.extend(["## Reference Assets", ""])
        for item in assets:
            marker = "missing" if item.get("missing") else "ready"
            lines.append(f"- {item.get('asset_id')}: {item.get('role')} ({marker}) {item.get('source')}")
        lines.append("")
    draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
    if draft:
        body = draft.get("body") if isinstance(draft.get("body"), dict) else {}
        lines.extend(
            [
                "## Provider Request Draft",
                "",
                f"- API family: {draft.get('api_family', '')}",
                f"- Method: {draft.get('method', '')}",
                f"- Endpoint: {draft.get('endpoint', '')}",
                f"- Model: {body.get('model', '')}",
                f"- Ratio: {body.get('ratio', '')}",
                f"- Duration: {body.get('duration', '')}",
                f"- Generate audio: {body.get('generate_audio', False)}",
                f"- Body ready for live: {draft.get('body_ready_for_live', False)}",
                "",
                "### Unresolved Reference Assets",
                "",
            ]
        )
        unresolved = draft.get("unresolved_reference_assets") or []
        lines.extend([f"- {item.get('asset_id')}: {item.get('local_reference')}" for item in unresolved] or ["- None"])
        lines.append("")
    return "\n".join(lines)


def prepare_provider_payload(
    product_id: str,
    brief: str,
    provider: str = "generic",
    brief_type: str = "image",
) -> Dict[str, Any]:
    if brief_type not in {"image", "video"}:
        raise ValueError("brief_type must be image or video")

    base = ensure_product(product_id)
    brief_path = _resolve_brief_path(base, brief)
    brief_payload = read_json(brief_path, {})
    actual_type = brief_payload.get("brief_type")
    if actual_type != brief_type:
        raise ValueError(f"expected {brief_type} brief, got {actual_type or 'unknown'}")
    entry = _provider_entry(provider)
    product_state = read_product_state(base)

    payload_id = f"provider-payload-{timestamp()}-{brief_type}"
    request = _image_request(brief_payload, entry, product_state) if brief_type == "image" else _video_request(brief_payload, entry, product_state)
    payload = {
        "schema_version": PROVIDER_PAYLOAD_SCHEMA_VERSION,
        "payload_id": payload_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "mode": "dry_run",
        "external_call_performed": False,
        "provider": entry.get("name", provider or "generic"),
        "brief_type": brief_type,
        "source_brief_id": brief_payload.get("brief_id", brief_path.stem),
        "source_brief_path": str(brief_path.relative_to(base)),
        "target": brief_payload.get("target", {}),
        "request": request,
        "execution_contract": {
            "execute_supported": bool(entry.get("execute_supported")),
            "requires_human_review_before_execution": True,
            "adapter_status": entry.get("adapter_contract", {}).get("execute", "boundary_defined"),
            "next_step": "Validate readiness before external execution.",
        },
    }

    out_dir = base / "artifacts" / "provider_payloads"
    json_path = out_dir / f"{payload_id}.json"
    md_path = out_dir / f"{payload_id}.md"
    write_json(json_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_payload_markdown(payload), encoding="utf-8")
    append_jsonl(
        base / "structured" / "provider_payload_index.jsonl",
        {
            "payload_id": payload_id,
            "created_at": payload["created_at"],
            "provider": payload["provider"],
            "brief_type": brief_type,
            "source_brief_id": payload["source_brief_id"],
            "mode": payload["mode"],
        },
    )
    update_index_and_log(
        base,
        "provider-payload",
        payload_id,
        [
            f"Provider: {payload['provider']}",
            f"Mode: {payload['mode']}",
            f"Source brief: {brief_path.relative_to(base)}",
        ],
    )
    return {
        "success": True,
        "product_id": base.name,
        "payload_id": payload_id,
        "provider": payload["provider"],
        "mode": payload["mode"],
        "external_call_performed": False,
        "brief_type": brief_type,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "payload": payload,
    }


