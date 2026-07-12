"""Material asset registry service."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...brain.provenance import register_source as _register_source
from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, slug, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import brain_documents, material_documents

from .shared import _list, _rel, _text

MATERIAL_ASSET_SCHEMA_VERSION = "product_creative.material_asset.v2.14"

MATERIAL_LIBRARY_SCHEMA_VERSION = "product_creative.material_library.v2.14"

MATERIAL_ROLES = {
    "current_main_image",
    "product_photo",
    "detail_image",
    "style_reference",
    "video_first_frame",
    "generated_candidate",
    "reference_image",
}

def _read_image_size(path: Path) -> Tuple[int, int]:
    data = path.read_bytes()
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if len(data) >= 10 and data[:6] in {b"GIF87a", b"GIF89a"}:
        return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")
    if len(data) >= 4 and data[:2] == b"\xff\xd8":
        idx = 2
        while idx + 9 < len(data):
            if data[idx] != 0xFF:
                idx += 1
                continue
            marker = data[idx + 1]
            idx += 2
            if marker in {0xD8, 0xD9}:
                continue
            if idx + 2 > len(data):
                break
            segment_length = int.from_bytes(data[idx:idx + 2], "big")
            if segment_length < 2 or idx + segment_length > len(data):
                break
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height = int.from_bytes(data[idx + 3:idx + 5], "big")
                width = int.from_bytes(data[idx + 5:idx + 7], "big")
                return width, height
            idx += segment_length
    return 0, 0

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _orientation(width: int, height: int) -> str:
    if not width or not height:
        return "unknown"
    if abs(width - height) <= max(width, height) * 0.05:
        return "square"
    return "landscape" if width > height else "portrait"

def _mime_type(path: Path) -> str:
    guess = mimetypes.guess_type(path.name)[0]
    return guess or "application/octet-stream"

def _material_markdown(asset: Dict[str, Any]) -> str:
    lines = [
        f"# {asset['material_id']}",
        "",
        f"Role: {asset['role']}",
        f"Status: {asset['status']}",
        f"Product: {asset['product_id']}",
        f"Stored: {asset['stored_path']}",
        f"Source: {asset['source_path']}",
        f"Dimensions: {asset['media'].get('width')} x {asset['media'].get('height')}",
        f"SHA256: {asset['sha256']}",
        "",
        "## Description",
        "",
        asset.get("description") or "No description.",
        "",
        "## Usage",
        "",
    ]
    lines.extend([f"- {item}" for item in asset.get("usage", [])] or ["- Not specified"])
    remote_urls = [item for item in asset.get("remote_urls", []) if isinstance(item, dict)]
    if remote_urls:
        lines.extend(["", "## Remote URLs", ""])
        for item in remote_urls:
            lines.append(f"- {item.get('url')} ({item.get('usage') or item.get('role') or 'reference'})")
    lines.append("")
    return "\n".join(lines)

def _asset_paths(base: Path, role: str, source: Path) -> Tuple[Path, str]:
    safe_role = slug(role)
    suffix = source.suffix.lower() or ".bin"
    filename = f"{timestamp()}-{safe_role}-{slug(source.stem)}{suffix}"
    return base / "assets" / "images" / filename, filename

def _material_records(base: Path) -> List[Dict[str, Any]]:
    records = material_documents(base).list_assets()
    records.sort(key=lambda item: (_text(item.get("created_at")), _text(item.get("material_id"))))
    return records

def _write_material_library(base: Path, records: List[Dict[str, Any]]) -> Path:
    active_by_role: Dict[str, str] = {}
    for item in records:
        if item.get("status") == "active":
            active_by_role[_text(item.get("role"))] = _text(item.get("material_id"))
    library = {
        "schema_version": MATERIAL_LIBRARY_SCHEMA_VERSION,
        "product_id": base.name,
        "updated_at": now_iso(),
        "asset_count": len(records),
        "active_by_role": active_by_role,
        "assets": records,
    }
    path = material_documents(base).save_library(library)
    return Path(path)

def _update_product_assets(base: Path, asset: Dict[str, Any]) -> None:
    repository = brain_documents(base)
    state = repository.load_state()
    assets = state.setdefault("assets", {})
    materials = [item for item in _list(assets.get("materials")) if item.get("material_id") != asset["material_id"]]
    materials.append(
        {
            "material_id": asset["material_id"],
            "role": asset["role"],
            "stored": asset["stored_path"],
            "source": asset["source_path"],
            "remote_url": _text(asset.get("remote_url")),
            "description": asset.get("description", ""),
            "status": asset.get("status", "active"),
        }
    )
    assets["materials"] = materials
    if asset["role"] == "current_main_image":
        assets["current_main_image_id"] = asset["material_id"]
    if asset["role"] == "video_first_frame":
        assets["video_first_frame_id"] = asset["material_id"]
    state["updated_at"] = now_iso()
    repository.save_state(state)

def _is_http_url(value: str) -> bool:
    text = _text(value)
    return text.startswith("http://") or text.startswith("https://")

def _material_json_path(base: Path, material_id: str) -> Path:
    repository = material_documents(base)
    material = repository.get_asset(material_id)
    if material:
        return base / "artifacts" / "material_assets" / f"{material_id}.json"
    raise FileNotFoundError(f"material asset '{material_id}' does not exist")

def _update_product_asset_remote_url(base: Path, asset: Dict[str, Any]) -> None:
    repository = brain_documents(base)
    state = repository.load_state()
    materials = _list(state.get("assets", {}).get("materials"))
    for item in materials:
        if item.get("material_id") == asset.get("material_id"):
            item["remote_url"] = _text(asset.get("remote_url"))
            item["remote_urls"] = _list(asset.get("remote_urls"))
    state["updated_at"] = now_iso()
    repository.save_state(state)

def register_material_asset(
    product_id: str,
    path: str,
    role: str = "product_photo",
    description: str = "",
    usage: List[str] | None = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    role = _text(role) or "product_photo"
    if role not in MATERIAL_ROLES:
        raise ValueError(f"role must be one of: {', '.join(sorted(MATERIAL_ROLES))}")
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"material asset does not exist: {path}")
    stored, _filename = _asset_paths(base, role, source)
    stored.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, stored)
    width, height = _read_image_size(stored)
    digest = _sha256(stored)
    material_id = f"material-{timestamp()}-{digest[:8]}"
    stored_rel = _rel(base, stored)
    source_id = _register_source(base, "material_asset", stored_rel, "medium", str(source.resolve()))
    asset = {
        "schema_version": MATERIAL_ASSET_SCHEMA_VERSION,
        "material_id": material_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "active",
        "role": role,
        "description": _text(description),
        "usage": [str(item) for item in usage or [] if str(item).strip()],
        "source_id": source_id,
        "source_path": str(source.resolve()),
        "stored_path": stored_rel,
        "sha256": digest,
        "media": {
            "kind": "image",
            "mime_type": _mime_type(stored),
            "bytes": stored.stat().st_size,
            "width": width,
            "height": height,
            "orientation": _orientation(width, height),
        },
        "generation_policy": {
            "can_be_reference_image": bool(width and height),
            "can_be_video_first_frame": bool(width and height and role in {"current_main_image", "video_first_frame", "product_photo"}),
            "requires_user_rights_confirmation": True,
        },
        "brain_write_policy": {
            "direct_write_to_product_brain": False,
            "requires_visual_analysis": True,
            "requires_human_confirmation_for_learning": True,
        },
    }
    out_dir = base / "artifacts" / "material_assets"
    json_path = out_dir / f"{material_id}.json"
    md_path = out_dir / f"{material_id}.md"
    material_documents(base).save_asset(material_id, asset)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_material_markdown(asset), encoding="utf-8")
    append_jsonl(base / "structured" / "material_assets_index.jsonl", {
        "material_id": material_id,
        "created_at": asset["created_at"],
        "role": role,
        "stored_path": stored_rel,
        "source_id": source_id,
    })
    records = _material_records(base)
    library_path = _write_material_library(base, records)
    _update_product_assets(base, asset)
    update_index_and_log(base, "material-asset", material_id, [f"{role}: {stored_rel}"])
    return {
        "success": True,
        "product_id": base.name,
        "material_id": material_id,
        "role": role,
        "files": {"json": str(json_path), "markdown": str(md_path), "library": str(library_path)},
        "asset": asset,
    }

def bind_material_remote_url(
    product_id: str,
    asset: str,
    url: str,
    usage: str = "video_reference",
    note: str = "",
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    material = _resolve_material(base, asset)
    clean_url = _text(url)
    if not _is_http_url(clean_url):
        raise ValueError("remote url must start with http:// or https://")
    material_id = _text(material.get("material_id"))
    remote_urls = [item for item in _list(material.get("remote_urls")) if isinstance(item, dict)]
    existing = next((item for item in remote_urls if item.get("url") == clean_url), None)
    entry = {
        "url": clean_url,
        "usage": _text(usage) or "video_reference",
        "bound_at": now_iso(),
        "note": _text(note),
        "requires_user_rights_confirmation": True,
    }
    if existing:
        existing.update(entry)
    else:
        remote_urls.append(entry)
    material["remote_url"] = clean_url
    material["remote_urls"] = remote_urls
    material.setdefault("generation_policy", {})["has_remote_reference_url"] = True
    material.setdefault("generation_policy", {})["can_be_remote_video_reference"] = True
    material["updated_at"] = now_iso()

    json_path = _material_json_path(base, material_id)
    md_path = json_path.with_suffix(".md")
    material_documents(base).save_asset(material_id, material)
    md_path.write_text(_material_markdown(material), encoding="utf-8")
    records = _material_records(base)
    library_path = _write_material_library(base, records)
    _update_product_asset_remote_url(base, material)
    append_jsonl(base / "structured" / "material_remote_url_index.jsonl", {
        "material_id": material_id,
        "bound_at": entry["bound_at"],
        "url": clean_url,
        "usage": entry["usage"],
    })
    update_index_and_log(base, "material-remote-url", material_id, [f"URL: {clean_url}", f"Usage: {entry['usage']}"])
    return {
        "success": True,
        "schema_version": "product_creative.material_remote_url.v2.21",
        "product_id": base.name,
        "material_id": material_id,
        "remote_url": clean_url,
        "usage": entry["usage"],
        "files": {"json": str(json_path), "markdown": str(md_path), "library": str(library_path)},
        "asset": material,
    }

def rebuild_material_manifest(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    records = _material_records(base)
    library_path = _write_material_library(base, records)
    update_index_and_log(base, "material-library", "manifest", [f"{len(records)} material asset(s) indexed"])
    return {
        "success": True,
        "schema_version": MATERIAL_LIBRARY_SCHEMA_VERSION,
        "product_id": base.name,
        "asset_count": len(records),
        "files": {"json": str(library_path)},
        "material_library": read_json(library_path, {}),
    }

def list_material_assets(product_id: str, role: str = "") -> Dict[str, Any]:
    base = ensure_product(product_id)
    library_path = base / "structured" / "material_library.json"
    if not library_path.exists():
        _write_material_library(base, _material_records(base))
    library = read_json(library_path, {})
    records = [item for item in _list(library.get("assets")) if isinstance(item, dict)]
    clean_role = _text(role)
    if clean_role:
        records = [item for item in records if item.get("role") == clean_role]
    return {
        "success": True,
        "schema_version": MATERIAL_LIBRARY_SCHEMA_VERSION,
        "product_id": base.name,
        "role": clean_role,
        "asset_count": len(records),
        "active_by_role": library.get("active_by_role", {}),
        "assets": records,
    }

def _resolve_material(base: Path, value: str) -> Dict[str, Any]:
    if not value:
        raise ValueError("material id or path is required")
    for item in _material_records(base):
        if value in {item.get("material_id"), item.get("stored_path"), item.get("source_path")}:
            return item
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("material path must stay inside the product workspace")
        for item in _material_records(base):
            stored = (base / _text(item.get("stored_path"))).resolve()
            if stored == resolved:
                return item
    raise FileNotFoundError(f"material asset '{value}' does not exist")
