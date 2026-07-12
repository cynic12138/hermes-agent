"""Creative Run orchestration for M0.6.6."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from ..review.api import (
    create_channel_review_package,
    create_comparison_package,
    create_review_package,
    qa_image_result,
    rebuild_artifact_manifest,
)
from .brief_export_service import export_briefs
from ...common import append_jsonl, ensure_product, now_iso, timestamp, update_index_and_log, write_json
from ..review.evaluation_service import evaluate_channel_content
from .generation_service import generate_product
from ...providers import (
    check_live_readiness,
    create_generation_job,
    prepare_provider_payload,
    validate_provider_payload,
)


CREATIVE_RUN_SCHEMA_VERSION = "product_creative.creative_run.v0.6.6"
CHANNEL_REVIEW_RUN_SCHEMA_VERSION = "product_creative.channel_review_run.v2.8"
CHANNEL_REVIEW_TARGETS = {
    "ecommerce-main-image-copy",
    "xiaohongshu-seeding-note",
    "douyin-short-video-script",
}


def _rel(base: Path, path: str) -> str:
    return str(Path(path).resolve().relative_to(base))


def _run_markdown(run: Dict[str, Any]) -> str:
    lines = [
        f"# {run['creative_run_id']}",
        "",
        f"Product: {run['product_id']}",
        f"Status: {run['status']}",
        f"Provider: {run['provider']}",
        f"Mode: {run['mode']}",
        f"Count: {run['count']}",
        f"External calls: {run['external_call_count']}",
        "",
        "## Artifacts",
        "",
        f"- Brief: {run['artifacts'].get('image_brief', {}).get('path', '')}",
        f"- Provider payload: {run['artifacts'].get('provider_payload', {}).get('path', '')}",
        f"- Validation: {run['artifacts'].get('validation', {}).get('path', '')}",
        f"- Readiness: {run['artifacts'].get('readiness', {}).get('path', '')}",
        f"- Comparison: {run['artifacts'].get('comparison_package', {}).get('path', '')}",
        "",
        "## Jobs",
        "",
    ]
    for item in run.get("jobs", []):
        lines.append(
            f"- {item.get('job_id')} | {item.get('status')} | result={item.get('result_id')} | review={item.get('review_package_id')}"
        )
    lines.append("")
    return "\n".join(lines)


def _channel_review_run_markdown(run: Dict[str, Any]) -> str:
    artifacts = run.get("artifacts", {})
    summary = run.get("summary", {})
    command = (
        run.get("next_actions", {})
        .get("record_selected_feedback", {})
        .get("command", "")
    )
    lines = [
        f"# {run['channel_review_run_id']}",
        "",
        f"Product: {run['product_id']}",
        f"Target: {run['target']}",
        f"Status: {run['status']}",
        f"Variants requested: {run['variants_requested']}",
        f"Best variant: {summary.get('best_variant') or 'not available'}",
        f"Evaluation status: {summary.get('evaluation_status')}",
        f"Overall score: {summary.get('overall_score') if summary.get('overall_score') is not None else 'not available'}",
        "",
        "## Artifacts",
        "",
        f"- Channel content: {artifacts.get('channel_content', {}).get('path', '')}",
        f"- Channel evaluation: {artifacts.get('channel_evaluation', {}).get('path', '')}",
        f"- Channel review package: {artifacts.get('channel_review_package', {}).get('path', '')}",
        f"- Manifest: {artifacts.get('manifest', {}).get('path', '')}",
        "",
        "## Steps",
        "",
    ]
    for step in run.get("steps", []):
        lines.append(f"- {step.get('name')}: {step.get('status')}")
    lines.extend(["", "## Next Feedback Command", "", "```powershell", command, "```", ""])
    return "\n".join(lines)


def create_channel_review_run(
    product_id: str,
    target: str,
    variants: int = 3,
    creative_brief: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if target not in CHANNEL_REVIEW_TARGETS:
        raise ValueError("channel-review-run requires a channel generation target")
    clean_variants = max(1, min(int(variants or 3), 5))

    base = ensure_product(product_id)
    run_id = f"channel-review-run-{timestamp()}"
    generated = generate_product(base.name, target, clean_variants, creative_brief)
    evaluation = evaluate_channel_content(base.name, generated["artifact_json"])
    review = create_channel_review_package(base.name, generated["artifact_json"], evaluation["files"]["json"])

    review_package = review.get("channel_review_package") or {}
    next_actions = review_package.get("next_actions") or {}
    run = {
        "schema_version": CHANNEL_REVIEW_RUN_SCHEMA_VERSION,
        "channel_review_run_id": run_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_human_review",
        "target": target,
        "creative_brief": creative_brief or {},
        "variants_requested": clean_variants,
        "workflow": {
            "version": "M2.8",
            "steps": [
                "generate",
                "channel-evaluate",
                "channel-review-package",
                "artifact-manifest",
            ],
            "product_brain_mutation": "never during channel-review-run",
            "requires_human_confirmation_for_learning": True,
        },
        "steps": [
            {
                "name": "generate",
                "status": "success",
                "artifact_id": generated.get("artifact_id", ""),
            },
            {
                "name": "channel-evaluate",
                "status": "success",
                "artifact_id": evaluation.get("evaluation_id", ""),
            },
            {
                "name": "channel-review-package",
                "status": "success",
                "artifact_id": review.get("channel_review_package_id", ""),
            },
        ],
        "artifacts": {
            "channel_content": {
                "id": generated.get("artifact_id", ""),
                "path": _rel(base, generated["artifact_json"]),
                "markdown": _rel(base, generated["artifact_markdown"]),
            },
            "channel_evaluation": {
                "id": evaluation.get("evaluation_id", ""),
                "path": _rel(base, evaluation["files"]["json"]),
                "markdown": _rel(base, evaluation["files"]["markdown"]),
            },
            "channel_review_package": {
                "id": review.get("channel_review_package_id", ""),
                "path": _rel(base, review["files"]["json"]),
                "markdown": _rel(base, review["files"]["markdown"]),
            },
            "manifest": {
                "path": "",
            },
        },
        "summary": {
            "best_variant": review.get("best_variant"),
            "evaluation_status": evaluation.get("summary", {}).get("status"),
            "overall_score": evaluation.get("summary", {}).get("overall_score"),
            "review_package_id": review.get("channel_review_package_id", ""),
        },
        "next_actions": next_actions,
        "requires_human_selection": True,
        "mutates_product_brain": False,
    }

    out_dir = base / "artifacts" / "channel_review_runs"
    json_path = out_dir / f"{run_id}.json"
    md_path = out_dir / f"{run_id}.md"
    write_json(json_path, run)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_channel_review_run_markdown(run), encoding="utf-8")
    append_jsonl(base / "structured" / "channel_review_run_index.jsonl", {
        "channel_review_run_id": run_id,
        "created_at": run["created_at"],
        "target": target,
        "variants_requested": clean_variants,
        "status": run["status"],
        "best_variant": run["summary"]["best_variant"],
        "channel_content_id": generated.get("artifact_id", ""),
        "channel_evaluation_id": evaluation.get("evaluation_id", ""),
        "channel_review_package_id": review.get("channel_review_package_id", ""),
        "json": str(json_path.relative_to(base)),
        "markdown": str(md_path.relative_to(base)),
    })
    update_index_and_log(base, "channel-review-run", run_id, [f"Target: {target}", f"Best variant: {run['summary']['best_variant']}"])

    manifest_result = rebuild_artifact_manifest(base.name)
    run["artifacts"]["manifest"]["path"] = _rel(base, manifest_result["files"]["json"])
    write_json(json_path, run)
    md_path.write_text(_channel_review_run_markdown(run), encoding="utf-8")

    return {
        "success": True,
        "product_id": base.name,
        "channel_review_run_id": run_id,
        "status": run["status"],
        "target": target,
        "best_variant": run["summary"]["best_variant"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "artifacts": run["artifacts"],
        "next_actions": next_actions,
        "channel_review_run": run,
    }


def create_creative_run(
    product_id: str,
    artifact: str,
    variant: int = 1,
    preset: str = "xiaohongshu-cover",
    provider: str = "generic",
    mode: str = "mock",
    count: int = 1,
) -> Dict[str, Any]:
    if mode not in {"dry_run", "mock", "live"}:
        raise ValueError("mode must be dry_run, mock, or live")
    raw_count = int(count or 1)
    if raw_count > 5:
        raise ValueError("creative runs are limited to 5 generations")
    clean_count = max(1, raw_count)

    base = ensure_product(product_id)
    run_id = f"creative-run-{timestamp()}"
    brief_result = export_briefs(base.name, artifact, variant, "image", preset, [])
    image_files = [item for item in brief_result.get("files", []) if item.get("brief_type") == "image"]
    if not image_files:
        raise RuntimeError("creative run did not produce an image brief")
    image_brief_path = image_files[0]["json"]

    payload_result = prepare_provider_payload(base.name, image_brief_path, provider, "image")
    validation_result = validate_provider_payload(base.name, payload_result["files"]["json"], provider)
    readiness_result: Dict[str, Any] = {}
    if mode == "live":
        readiness_result = check_live_readiness(base.name, provider, "image", payload_result["files"]["json"])
        if not readiness_result["ready_for_live"]:
            raise ValueError("provider is not ready for live execution: " + "; ".join(readiness_result["blockers"]))

    jobs = []
    job_paths: List[str] = []
    external_call_count = 0
    for index in range(clean_count):
        if index > 0:
            time.sleep(1)
        job_result = create_generation_job(base.name, payload_result["files"]["json"], provider, mode)
        result = job_result.get("result") or {}
        review_result = None
        qa_result = None
        if job_result.get("files", {}).get("json"):
            review_result = create_review_package(base.name, job_result["files"]["json"])
        if result.get("brief_type") == "image" and result.get("outputs"):
            first_output = result["outputs"][0] if result["outputs"] else {}
            if first_output.get("path"):
                qa_result = qa_image_result(base.name, job_result["result_files"]["json"])
        if job_result.get("external_call_performed") or result.get("external_call_performed"):
            external_call_count += 1
        jobs.append(
            {
                "index": index + 1,
                "job_id": job_result.get("job_id", ""),
                "job_path": str(Path(job_result["files"]["json"]).resolve().relative_to(base)),
                "status": job_result.get("status", ""),
                "result_id": result.get("result_id", ""),
                "result_path": str(Path(job_result["result_files"]["json"]).resolve().relative_to(base))
                if job_result.get("result_files", {}).get("json")
                else "",
                "review_package_id": review_result.get("review_package_id", "") if review_result else "",
                "review_package_path": str(Path(review_result["files"]["json"]).resolve().relative_to(base))
                if review_result
                else "",
                "qa_id": qa_result.get("qa_id", "") if qa_result else "",
                "qa_status": qa_result.get("status", "") if qa_result else "",
                "qa_path": str(Path(qa_result["files"]["json"]).resolve().relative_to(base)) if qa_result else "",
                "external_call_performed": bool(job_result.get("external_call_performed"))
                or bool(result.get("external_call_performed")),
            }
        )
        job_paths.append(job_result["files"]["json"])

    comparison_result = None
    if len(job_paths) >= 2:
        comparison_result = create_comparison_package(base.name, job_paths)
    manifest_result = rebuild_artifact_manifest(base.name)

    status = "completed" if all(item.get("status") in {"validated", "mocked", "completed"} for item in jobs) else "needs_review"
    run = {
        "schema_version": CREATIVE_RUN_SCHEMA_VERSION,
        "creative_run_id": run_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": status,
        "source_artifact_id": brief_result.get("artifact_id", ""),
        "variant": variant,
        "preset": preset,
        "provider": provider,
        "mode": mode,
        "count": clean_count,
        "external_call_count": external_call_count,
        "workflow": {
            "version": "M0.6.6",
            "supports_live_image_run": True,
            "max_generation_count": 5,
            "product_brain_mutation": "never during creative-run",
        },
        "artifacts": {
            "image_brief": {
                "id": image_files[0].get("brief_id", ""),
                "path": str(Path(image_brief_path).resolve().relative_to(base)),
            },
            "provider_payload": {
                "id": payload_result.get("payload_id", ""),
                "path": str(Path(payload_result["files"]["json"]).resolve().relative_to(base)),
            },
            "validation": {
                "id": validation_result.get("validation_id", ""),
                "path": str(Path(validation_result["files"]["json"]).resolve().relative_to(base)),
            },
            "readiness": {
                "id": readiness_result.get("readiness_id", ""),
                "path": str(Path(readiness_result["files"]["json"]).resolve().relative_to(base))
                if readiness_result
                else "",
            },
            "comparison_package": {
                "id": comparison_result.get("comparison_package_id", "") if comparison_result else "",
                "path": str(Path(comparison_result["files"]["json"]).resolve().relative_to(base))
                if comparison_result
                else "",
            },
            "manifest": {
                "path": str(Path(manifest_result["files"]["json"]).resolve().relative_to(base)),
            },
        },
        "jobs": jobs,
        "requires_human_review": True,
        "next_steps": [
            "Review generated results.",
            "Select a preferred result if comparing multiple outputs.",
            "Record result-feedback before creating Product Brain evolution proposals.",
        ],
    }
    out_dir = base / "artifacts" / "creative_runs"
    json_path = out_dir / f"{run_id}.json"
    md_path = out_dir / f"{run_id}.md"
    write_json(json_path, run)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_run_markdown(run), encoding="utf-8")
    append_jsonl(base / "structured" / "creative_run_index.jsonl", {
        "creative_run_id": run_id,
        "created_at": run["created_at"],
        "provider": provider,
        "mode": mode,
        "count": clean_count,
        "status": status,
        "external_call_count": external_call_count,
    })
    update_index_and_log(base, "creative-run", run_id, [f"Mode: {mode}", f"Count: {clean_count}"])
    return {
        "success": True,
        "product_id": base.name,
        "creative_run_id": run_id,
        "status": status,
        "external_call_count": external_call_count,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "creative_run": run,
    }
