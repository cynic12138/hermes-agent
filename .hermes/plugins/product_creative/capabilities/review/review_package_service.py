"""Provider result review and comparison packages."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from .manifest_service import ARTIFACT_MANIFEST_SCHEMA_VERSION, rebuild_artifact_manifest

from .artifact_shared import _list, _path_from_rel, _rel, _resolve_known_artifact, _text

REVIEW_PACKAGE_SCHEMA_VERSION = "product_creative.review_package.v0.5.3"

COMPARISON_PACKAGE_SCHEMA_VERSION = "product_creative.comparison_package.v0.6.4"

def _brief_summary(brief: Dict[str, Any]) -> Dict[str, Any]:
    if brief.get("brief_type") == "image":
        return {
            "headline": brief.get("copy", {}).get("headline", ""),
            "subheadline": brief.get("copy", {}).get("subheadline", ""),
            "text_to_render": brief.get("copy", {}).get("text_to_render", []),
            "prompt": brief.get("generation_contract", {}).get("prompt", ""),
        }
    return {
        "style": brief.get("story", {}).get("style", ""),
        "estimated_duration": brief.get("story", {}).get("estimated_duration", ""),
        "storyboard": brief.get("story", {}).get("storyboard", []),
        "prompt": brief.get("generation_contract", {}).get("prompt", ""),
    }

def _review_markdown(package: Dict[str, Any]) -> str:
    lines = [
        f"# {package['review_package_id']}",
        "",
        f"Product: {package['product']['name']}",
        f"Brief type: {package['brief_type']}",
        f"Job status: {package['job']['status']}",
        f"Result status: {package['result'].get('status', '')}",
        f"External call performed: {package['external_call_performed']}",
        "",
        "## Product",
        "",
        package["product"].get("brief", ""),
        "",
        "## Selling Points",
        "",
    ]
    lines.extend([f"- {item}" for item in package["product"].get("selling_points", [])] or ["- None"])
    lines.extend(["", "## Creative Summary", ""])
    summary = package["creative_summary"]
    if package["brief_type"] == "image":
        lines.extend(
            [
                f"- Headline: {summary.get('headline', '')}",
                f"- Subheadline: {summary.get('subheadline', '')}",
                "",
                "### Text To Render",
                "",
            ]
        )
        lines.extend([f"- {item}" for item in summary.get("text_to_render", [])] or ["- None"])
    else:
        lines.extend(
            [
                f"- Style: {summary.get('style', '')}",
                f"- Estimated duration: {summary.get('estimated_duration', '')}",
                "",
                "| Shot | Duration | Description | Caption |",
                "| --- | --- | --- | --- |",
            ]
        )
        for shot in summary.get("storyboard", []):
            lines.append(
                f"| {shot.get('shot')} | {shot.get('duration')} | {shot.get('description')} | {shot.get('caption')} |"
            )
    lines.extend(["", "## Prompt", "", summary.get("prompt", ""), "", "## Review Checklist", ""])
    lines.extend(f"- [ ] {item}" for item in package["review_checklist"])
    lines.append("")
    return "\n".join(lines)

def create_review_package(product_id: str, job: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    job_path = _resolve_known_artifact(base, job, ["generation_jobs"])
    job_payload = read_json(job_path, {})
    payload_path = _path_from_rel(base, _text(job_payload.get("source_payload_path")))
    payload = read_json(payload_path, {}) if payload_path else {}
    brief_path = _path_from_rel(base, _text(payload.get("source_brief_path")))
    brief = read_json(brief_path, {}) if brief_path else {}
    result_path = _path_from_rel(base, _text(job_payload.get("result_path")))
    result = read_json(result_path, {}) if result_path else {}
    state = read_product_state(base)

    review_id = f"review-pack-{timestamp()}"
    package = {
        "schema_version": REVIEW_PACKAGE_SCHEMA_VERSION,
        "review_package_id": review_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_review",
        "brief_type": job_payload.get("brief_type", ""),
        "external_call_performed": bool(job_payload.get("external_call_performed"))
        or bool(result.get("external_call_performed")),
        "product": {
            "name": state.get("name", base.name),
            "brief": state.get("basic", {}).get("brief", ""),
            "selling_points": state.get("selling_points", []),
        },
        "artifacts": {
            "job": {"id": job_payload.get("job_id", job_path.stem), "path": _rel(base, job_path)},
            "payload": {
                "id": payload.get("payload_id", payload_path.stem if payload_path else ""),
                "path": _rel(base, payload_path) if payload_path else "",
            },
            "brief": {
                "id": brief.get("brief_id", brief_path.stem if brief_path else ""),
                "path": _rel(base, brief_path) if brief_path else "",
            },
            "result": {
                "id": result.get("result_id", result_path.stem if result_path else ""),
                "path": _rel(base, result_path) if result_path else "",
            },
        },
        "job": {
            "provider": job_payload.get("provider", ""),
            "mode": job_payload.get("mode", ""),
            "status": job_payload.get("status", ""),
            "validation_status": job_payload.get("validation", {}).get("status", ""),
        },
        "result": {
            "status": result.get("status", ""),
            "mock": any(bool(item.get("mock")) for item in _list(result.get("outputs")) if isinstance(item, dict)),
            "ready_for_feedback": result.get("review", {}).get("ready_for_feedback", False),
        },
        "creative_summary": _brief_summary(brief),
        "risk_notes": [
            "Human review is required before treating generated media as production-ready.",
            "Mock results do not represent actual image/video quality.",
            "Product Brain must not be updated without explicit review and apply.",
        ],
        "review_checklist": [
            "Check factual claims against Product State.",
            "Check channel fit and aspect ratio.",
            "Check text overlay length and readability.",
            "Check visual/video prompt against forbidden invention list.",
            "Decide whether this result can enter feedback collection.",
        ],
    }
    out_dir = base / "artifacts" / "review_packages"
    json_path = out_dir / f"{review_id}.json"
    md_path = out_dir / f"{review_id}.md"
    write_json(json_path, package)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_review_markdown(package), encoding="utf-8")
    update_index_and_log(base, "review-package", review_id, [str(json_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "review_package_id": review_id,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "review_package": package,
    }

def _comparison_markdown(package: Dict[str, Any]) -> str:
    lines = [
        f"# {package['comparison_package_id']}",
        "",
        f"Product: {package['product_id']}",
        f"Count: {package['count']}",
        "",
        "| # | Job | Result | Status | Mode | Image |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for idx, item in enumerate(package.get("items", []), 1):
        lines.append(
            f"| {idx} | {item.get('job_id')} | {item.get('result_id')} | {item.get('status')} | {item.get('mode')} | {item.get('image_path')} |"
        )
    lines.extend(["", "## Review Criteria", ""])
    lines.extend(f"- {item}" for item in package.get("review_criteria", []))
    lines.append("")
    return "\n".join(lines)

def create_comparison_package(product_id: str, jobs: List[str]) -> Dict[str, Any]:
    base = ensure_product(product_id)
    if len(jobs) < 2:
        raise ValueError("at least two jobs are required for a comparison package")

    items = []
    for job in jobs:
        job_path = _resolve_known_artifact(base, job, ["generation_jobs"])
        job_payload = read_json(job_path, {})
        result_path = _path_from_rel(base, _text(job_payload.get("result_path")))
        result_payload = read_json(result_path, {}) if result_path else {}
        output = {}
        outputs = [item for item in _list(result_payload.get("outputs")) if isinstance(item, dict)]
        if outputs:
            output = outputs[0]
        items.append(
            {
                "job_id": job_payload.get("job_id", job_path.stem),
                "job_path": _rel(base, job_path),
                "result_id": result_payload.get("result_id", ""),
                "result_path": _rel(base, result_path) if result_path else "",
                "status": result_payload.get("status", job_payload.get("status", "")),
                "mode": job_payload.get("mode", ""),
                "provider": job_payload.get("provider", ""),
                "image_path": output.get("path", ""),
                "external_call_performed": bool(job_payload.get("external_call_performed"))
                or bool(result_payload.get("external_call_performed")),
            }
        )

    package_id = f"comparison-pack-{timestamp()}"
    package = {
        "schema_version": COMPARISON_PACKAGE_SCHEMA_VERSION,
        "comparison_package_id": package_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_comparison",
        "count": len(items),
        "items": items,
        "review_criteria": [
            "Product recognizability",
            "Channel and aspect fit",
            "Visual clarity",
            "Text overlay feasibility",
            "No unverified claims or invented packaging",
            "Overall preference for future Product Brain learning",
        ],
        "requires_human_selection": True,
    }
    out_dir = base / "artifacts" / "comparison_packages"
    json_path = out_dir / f"{package_id}.json"
    md_path = out_dir / f"{package_id}.md"
    write_json(json_path, package)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_comparison_markdown(package), encoding="utf-8")
    append_jsonl(base / "structured" / "comparison_package_index.jsonl", {
        "comparison_package_id": package_id,
        "created_at": package["created_at"],
        "count": package["count"],
        "status": package["status"],
    })
    update_index_and_log(base, "comparison-package", package_id, [f"{len(items)} result(s) compared"])
    return {
        "success": True,
        "product_id": base.name,
        "comparison_package_id": package_id,
        "count": len(items),
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "comparison_package": package,
    }
