"""Generated image QA service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from .manifest_service import ARTIFACT_MANIFEST_SCHEMA_VERSION, rebuild_artifact_manifest

from .artifact_shared import _list, _path_from_rel, _rel, _resolve_known_artifact, _text

IMAGE_QA_SCHEMA_VERSION = "product_creative.image_qa.v0.6.2"

def _read_image_size(path: Path) -> Tuple[int, int]:
    data = path.read_bytes()
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
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

def _ratio_value(value: str) -> float:
    if ":" not in value:
        return 0.0
    left, right = value.split(":", 1)
    try:
        width = float(left)
        height = float(right)
    except ValueError:
        return 0.0
    if height <= 0:
        return 0.0
    return width / height

def _qa_markdown(qa: Dict[str, Any]) -> str:
    lines = [
        f"# {qa['qa_id']}",
        "",
        f"Result: {qa['source_result_id']}",
        f"Status: {qa['status']}",
        f"Image exists: {qa['checks']['image_exists']}",
        f"Dimensions: {qa['image'].get('width')} x {qa['image'].get('height')}",
        f"Expected aspect: {qa['expected'].get('aspect_ratio')}",
        f"Actual aspect: {qa['image'].get('aspect_ratio')}",
        "",
        "## Errors",
        "",
    ]
    lines.extend([f"- {item}" for item in qa.get("errors", [])] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in qa.get("warnings", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def qa_image_result(product_id: str, result: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    result_path = _resolve_known_artifact(base, result, ["generated_images"])
    result_payload = read_json(result_path, {})
    outputs = [item for item in _list(result_payload.get("outputs")) if isinstance(item, dict)]
    output = outputs[0] if outputs else {}
    image_path = _path_from_rel(base, _text(output.get("path")))
    source_payload_path = None
    expected_aspect = ""
    source_payload_id = _text(result_payload.get("source_payload_id"))
    if source_payload_id:
        try:
            source_payload_path = _resolve_known_artifact(base, source_payload_id, ["provider_payloads"])
            source_payload = read_json(source_payload_path, {})
            expected_aspect = _text(source_payload.get("request", {}).get("aspect_ratio"))
        except FileNotFoundError:
            source_payload_path = None

    errors: List[str] = []
    warnings: List[str] = []
    image_exists = bool(image_path and image_path.exists())
    width = height = 0
    if not image_exists:
        errors.append("image output file is missing")
    else:
        width, height = _read_image_size(image_path)
        if width <= 0 or height <= 0:
            errors.append("could not read image dimensions")

    actual_ratio = round(width / height, 4) if width and height else 0.0
    expected_ratio = _ratio_value(expected_aspect)
    if expected_ratio and actual_ratio and abs(actual_ratio - expected_ratio) > 0.12:
        warnings.append(f"actual aspect ratio differs from expected {expected_aspect}")
    if bool(output.get("mock")):
        errors.append("mock output cannot pass image QA")
    if not result_payload.get("external_call_performed"):
        warnings.append("result was not produced by live execution")

    status = "failed" if errors else ("needs_review" if warnings else "passed")
    qa_id = f"image-qa-{timestamp()}"
    qa = {
        "schema_version": IMAGE_QA_SCHEMA_VERSION,
        "qa_id": qa_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "source_result_id": result_payload.get("result_id", result_path.stem),
        "source_result_path": _rel(base, result_path),
        "source_payload_id": source_payload_id,
        "source_payload_path": _rel(base, source_payload_path) if source_payload_path else "",
        "status": status,
        "checks": {
            "image_exists": image_exists,
            "dimensions_readable": bool(width and height),
            "aspect_ratio_checked": bool(expected_ratio and actual_ratio),
        },
        "expected": {
            "aspect_ratio": expected_aspect,
            "aspect_ratio_value": expected_ratio,
        },
        "image": {
            "path": _rel(base, image_path) if image_path else "",
            "mime_type": output.get("mime_type", ""),
            "bytes": output.get("bytes", 0),
            "width": width,
            "height": height,
            "aspect_ratio": actual_ratio,
        },
        "errors": errors,
        "warnings": warnings,
        "external_call_performed": bool(result_payload.get("external_call_performed")),
        "requires_human_review": True,
    }
    out_dir = base / "artifacts" / "image_qa"
    json_path = out_dir / f"{qa_id}.json"
    md_path = out_dir / f"{qa_id}.md"
    write_json(json_path, qa)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_qa_markdown(qa), encoding="utf-8")
    append_jsonl(base / "structured" / "image_qa_index.jsonl", {
        "qa_id": qa_id,
        "created_at": qa["created_at"],
        "source_result_id": qa["source_result_id"],
        "status": qa["status"],
    })
    update_index_and_log(base, "image-qa", qa_id, [f"Status: {status}"])
    return {
        "success": status != "failed",
        "product_id": base.name,
        "qa_id": qa_id,
        "status": status,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "qa": qa,
    }
