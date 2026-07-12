"""M6 material execution input resolver.

This module keeps local material assets canonical while producing provider-specific
execution handles such as data URLs, remote URLs, or future asset IDs.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import artifacts


MATERIAL_EXECUTION_INPUT_SCHEMA_VERSION = "product_creative.material_execution_input.v6.2"
PROVIDER_CAPABILITY_SCHEMA_VERSION = "product_creative.provider_capability_matrix.v6.2"
DEFAULT_MAX_DATA_URL_BYTES = 5 * 1024 * 1024


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def _is_http_url(value: str) -> bool:
    text = _text(value)
    return text.startswith("http://") or text.startswith("https://")


def _is_data_url(value: str) -> bool:
    return _text(value).startswith("data:")


def _is_asset_url(value: str) -> bool:
    return _text(value).startswith("asset://")


def _mime_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _media_kind(mime: str, path: Path) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return "image"
    if suffix in {".mp3", ".wav", ".m4a", ".aac", ".flac"}:
        return "audio"
    if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
        return "video"
    return "unknown"


def _max_data_url_bytes() -> int:
    raw = os.getenv("PRODUCT_CREATIVE_MAX_DATA_URL_BYTES", "").strip()
    if not raw:
        return DEFAULT_MAX_DATA_URL_BYTES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_DATA_URL_BYTES


def _provider_capabilities(provider: str) -> Dict[str, Any]:
    name = _text(provider) or "generic"
    common = {
        "schema_version": PROVIDER_CAPABILITY_SCHEMA_VERSION,
        "provider": name,
        "max_data_url_bytes": _max_data_url_bytes(),
        "supports_remote_url": True,
        "supports_asset_url": True,
        "supports_image_data_url": False,
        "supports_audio_data_url": False,
        "supports_video_data_url": False,
        "notes": [],
    }
    if name in {"volcengine-ark-video", "volcengine-ark-vlm"}:
        common.update(
            {
                "supports_image_data_url": True,
                "supports_audio_data_url": True,
                "supports_video_data_url": False,
                "notes": [
                    "Ark JSON payloads can use image/audio data URLs when size stays below request limits.",
                    "Video references should use URL or provider asset IDs.",
                ],
            }
        )
    elif name in {"volcengine-ark-image", "generic-http-image"}:
        common.update(
            {
                "supports_image_data_url": True,
                "supports_audio_data_url": False,
                "supports_video_data_url": False,
                "notes": ["Image references may be represented as data URLs for provider adapters that accept them."],
            }
        )
    elif name.startswith("mock") or name == "generic":
        common.update(
            {
                "supports_image_data_url": True,
                "supports_audio_data_url": True,
                "supports_video_data_url": True,
                "notes": ["Mock providers accept all local references for dry-run validation."],
            }
        )
    return common


def provider_capability_matrix(provider: str = "") -> Dict[str, Any]:
    """Return the M6 provider input capability matrix without mutating product data."""

    if provider:
        return {"success": True, **_provider_capabilities(provider)}
    providers = ["generic", "volcengine-ark-image", "volcengine-ark-video", "volcengine-ark-vlm"]
    return {
        "success": True,
        "schema_version": PROVIDER_CAPABILITY_SCHEMA_VERSION,
        "providers": [_provider_capabilities(item) for item in providers],
    }


def _material_json_path(base: Path, material_id: str) -> Path:
    clean = _text(material_id)
    if not clean:
        raise ValueError("material id is required")
    path = base / "artifacts" / "material_assets" / f"{clean}.json"
    if path.exists():
        return path
    if artifacts().get(base.name, clean):
        return path
    raise FileNotFoundError(f"material asset '{material_id}' does not exist")


def _load_material(base: Path, material: str | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(material, dict):
        material_id = _text(material.get("material_id") or material.get("asset_id"))
        if material_id:
            try:
                loaded = read_json(_material_json_path(base, material_id), {})
                if isinstance(loaded, dict) and loaded:
                    merged = dict(loaded)
                    merged.update({k: v for k, v in material.items() if v not in ("", None, [])})
                    return merged
            except FileNotFoundError:
                return dict(material)
        return dict(material)
    return read_json(_material_json_path(base, material), {})


def _first_provider_value(material: Dict[str, Any]) -> str:
    for key in ["remote_url", "url"]:
        value = _text(material.get(key))
        if _is_http_url(value) or _is_data_url(value) or _is_asset_url(value):
            return value
    for item in _list(material.get("remote_urls")):
        if isinstance(item, dict):
            value = _text(item.get("url"))
            if _is_http_url(value) or _is_data_url(value) or _is_asset_url(value):
                return value
    for key in ["asset_url", "provider_asset_url"]:
        value = _text(material.get(key))
        if _is_asset_url(value):
            return value
    return ""


def _local_path(base: Path, material: Dict[str, Any]) -> Path | None:
    for key in ["stored_path", "stored", "local_path", "path", "source_path", "source"]:
        value = _text(material.get(key))
        if not value:
            continue
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = base / value
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _redacted(value: str) -> str:
    if _is_data_url(value):
        head = value.split(",", 1)[0]
        return f"{head},<redacted>"
    if "?" in value and (_is_http_url(value) or _is_asset_url(value)):
        return value.split("?", 1)[0] + "?<redacted>"
    return value


def _kind_allowed(kind: str, caps: Dict[str, Any]) -> bool:
    if kind == "image":
        return bool(caps.get("supports_image_data_url"))
    if kind == "audio":
        return bool(caps.get("supports_audio_data_url"))
    if kind == "video":
        return bool(caps.get("supports_video_data_url"))
    return False


def _execution_markdown(doc: Dict[str, Any]) -> str:
    lines = [
        f"# {doc['execution_input_id']}",
        "",
        f"Provider: {doc['provider']}",
        f"Material: {doc.get('material_id', '')}",
        f"Role: {doc['role']}",
        f"Status: {doc['status']}",
        f"Input kind: {doc.get('input_kind', '')}",
        f"Ready for provider: {doc.get('ready_for_provider', False)}",
        "",
        "## Value",
        "",
        doc.get("value_ref", "") or "None",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- {item}" for item in doc.get("blockers", [])] or ["- None"])
    lines.extend(["", "## Notes", ""])
    lines.extend([f"- {item}" for item in doc.get("notes", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def resolve_material_execution_input(
    product_id: str,
    material: str | Dict[str, Any],
    provider: str = "volcengine-ark-image",
    role: str = "reference_image",
    usage: str = "provider_payload",
    persist: bool = True,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    provider_name = _text(provider) or "volcengine-ark-image"
    role_name = _text(role) or "reference_image"
    caps = _provider_capabilities(provider_name)
    payload = _load_material(base, material)
    material_id = _text(payload.get("material_id") or payload.get("asset_id"))
    local = _local_path(base, payload)
    existing = _first_provider_value(payload)
    input_kind = ""
    provider_value = ""
    blockers: List[str] = []
    notes: List[str] = []
    mime = ""
    size_bytes = 0
    kind = "unknown"

    if existing:
        provider_value = existing
        if _is_data_url(existing):
            input_kind = "data_url"
        elif _is_asset_url(existing):
            input_kind = "asset_url"
        else:
            input_kind = "remote_url"
        notes.append("Using an existing provider-accessible material handle.")
    elif local:
        mime = _mime_type(local)
        size_bytes = local.stat().st_size
        kind = _media_kind(mime, local)
        if _kind_allowed(kind, caps) and size_bytes <= int(caps.get("max_data_url_bytes") or DEFAULT_MAX_DATA_URL_BYTES):
            provider_value = _data_url(local, mime)
            input_kind = "data_url"
            notes.append("Resolved local material as a provider data URL; artifact stores only a redacted value.")
        elif kind == "video":
            blockers.append("Video references cannot be embedded as data URLs for this provider; use remote URL or provider asset ID.")
        elif size_bytes > int(caps.get("max_data_url_bytes") or DEFAULT_MAX_DATA_URL_BYTES):
            blockers.append("Local material is too large for the configured data URL limit; use remote URL or object storage.")
        else:
            blockers.append(f"Provider '{provider_name}' does not support {kind or 'unknown'} data URLs.")
    else:
        blockers.append("No existing remote/data/asset URL and no readable local file were found for this material.")

    status = "ready" if provider_value and not blockers else "blocked"
    doc = {
        "schema_version": MATERIAL_EXECUTION_INPUT_SCHEMA_VERSION,
        "execution_input_id": f"material-input-{timestamp()}",
        "product_id": base.name,
        "created_at": now_iso(),
        "status": status,
        "provider": provider_name,
        "role": role_name,
        "usage": _text(usage) or "provider_payload",
        "material_id": material_id,
        "local_asset_path": _rel(base, local) if local and base.resolve() in local.resolve().parents else str(local) if local else "",
        "mime_type": mime or _text((payload.get("media") or {}).get("mime_type")),
        "size_bytes": size_bytes or (payload.get("media") or {}).get("bytes", 0),
        "media_kind": kind if kind != "unknown" else _text((payload.get("media") or {}).get("kind")),
        "input_kind": input_kind,
        "value_ref": _redacted(provider_value),
        "ready_for_provider": status == "ready",
        "blockers": blockers,
        "notes": notes,
        "not_canonical_source": True,
        "canonical_material_remains_local": True,
        "provider_capability": caps,
    }

    if persist:
        out_dir = base / "artifacts" / "material_execution_inputs"
        json_path = out_dir / f"{doc['execution_input_id']}.json"
        md_path = out_dir / f"{doc['execution_input_id']}.md"
        write_json(json_path, doc)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_execution_markdown(doc), encoding="utf-8")
        append_jsonl(
            base / "structured" / "material_execution_input_index.jsonl",
            {
                "execution_input_id": doc["execution_input_id"],
                "created_at": doc["created_at"],
                "material_id": material_id,
                "provider": provider_name,
                "role": role_name,
                "status": status,
                "input_kind": input_kind,
                "path": _rel(base, json_path),
            },
        )
        update_index_and_log(
            base,
            "material-execution-input",
            doc["execution_input_id"],
            [f"Provider: {provider_name}", f"Status: {status}", f"Input kind: {input_kind or 'none'}"],
        )
        files = {"json": str(json_path), "markdown": str(md_path)}
    else:
        files = {}

    return {
        "success": status == "ready",
        "schema_version": MATERIAL_EXECUTION_INPUT_SCHEMA_VERSION,
        "product_id": base.name,
        "execution_input_id": doc["execution_input_id"],
        "status": status,
        "ready_for_provider": status == "ready",
        "input_kind": input_kind,
        "provider_value": provider_value,
        "value_ref": doc["value_ref"],
        "blockers": blockers,
        "files": files,
        "material_execution_input": doc,
    }
