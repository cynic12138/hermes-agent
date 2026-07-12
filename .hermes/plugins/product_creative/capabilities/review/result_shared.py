from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ...common import read_json

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))

def _resolve_result_path(base: Path, value: str) -> Path:
    if not value:
        raise ValueError("result id or path is required")
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("result path must stay inside the product workspace")
        return resolved
    name = value if value.endswith(".json") else f"{value}.json"
    for folder in ["generated_images", "generated_videos"]:
        path = base / "artifacts" / folder / name
        if path.exists():
            return path.resolve()
    raise FileNotFoundError(f"result '{value}' does not exist")

def _resolve_optional_artifact(base: Path, folder: str, value: str) -> Dict[str, Any]:
    if not value:
        return {}
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        if base.resolve() != resolved and base.resolve() not in resolved.parents:
            return {}
        return read_json(resolved, {})
    name = value if value.endswith(".json") else f"{value}.json"
    path = base / "artifacts" / folder / name
    return read_json(path, {}) if path.exists() else {}

def _path_entry(base: Path, value: str) -> Dict[str, str]:
    if not value:
        return {}
    path = Path(value)
    if not path.is_absolute():
        path = base / value
    if path.exists():
        return {"path": _rel(base, path), "absolute_path": str(path.resolve()), "exists": True}
    return {"path": value, "absolute_path": str(path), "exists": False}

def _media_outputs(base: Path, result: Dict[str, Any]) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for item in _list(result.get("outputs")):
        entry = {
            "type": _text(item.get("type")),
            "description": _text(item.get("description")),
            "mime_type": _text(item.get("mime_type")),
            "remote_url": _text(item.get("remote_url") or item.get("url")),
        }
        entry.update(_path_entry(base, _text(item.get("path") or item.get("local_path"))))
        outputs.append(entry)
    for field in ["local_image", "local_video", "image", "video"]:
        value = _text(result.get(field))
        if value:
            entry = {"type": field, "description": f"Result {field}"}
            entry.update(_path_entry(base, value))
            outputs.append(entry)
    return outputs

def _brief_context(base: Path, result: Dict[str, Any]) -> Dict[str, Any]:
    payload_id = _text(result.get("source_payload_id"))
    payload = _resolve_optional_artifact(base, "provider_payloads", payload_id)
    brief_id = _text(payload.get("source_brief_id") or payload.get("brief_id"))
    folder = "image_briefs" if result.get("brief_type") == "image" else "video_scripts"
    brief = _resolve_optional_artifact(base, folder, brief_id)
    contract = brief.get("generation_contract") if isinstance(brief.get("generation_contract"), dict) else {}
    return {
        "source_payload_id": payload_id,
        "source_brief_id": brief_id,
        "prompt": _text(contract.get("prompt") or contract.get("provider_prompt") or payload.get("prompt")),
        "brief": brief,
        "payload": payload,
    }
