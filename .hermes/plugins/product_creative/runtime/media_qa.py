"""Unified deterministic-first media QA orchestration."""

from __future__ import annotations

import hashlib
from typing import Any

from ..common import now_iso
from ..contracts.creative_artifacts import (
    MediaExecutionPlanArtifact,
    MediaQaReportArtifact,
    MediaQualityCheck,
)
from .media_technical_qa import inspect_media_technical_quality
from .media_text_qa import OcrAdapter, inspect_media_text_quality
from .packaging_visual_qa import inspect_packaging_visual_quality
from .professional_artifacts import (
    load_professional_artifact,
    save_professional_artifact,
)
from .story_continuity_qa import (
    VisualAdapter,
    inspect_story_continuity_quality,
)


MEDIA_QA_POLICY_VERSION = "m14.1"
_configured_ocr_adapter: OcrAdapter | None = None
_configured_visual_adapter: VisualAdapter | None = None


def configure_media_qa_adapters(
    *,
    ocr_adapter: OcrAdapter | None,
    visual_adapter: VisualAdapter | None,
) -> None:
    """Configure process-local QA ports for an approved runtime or fixture."""

    global _configured_ocr_adapter, _configured_visual_adapter
    _configured_ocr_adapter = ocr_adapter
    _configured_visual_adapter = visual_adapter


def configured_media_qa_adapters() -> tuple[
    OcrAdapter | None,
    VisualAdapter | None,
]:
    return _configured_ocr_adapter, _configured_visual_adapter


def _overall_result(
    checks: list[MediaQualityCheck],
) -> tuple[str, str, list[str]]:
    failed = [item for item in checks if item.status == "FAIL"]
    unknown = [item for item in checks if item.status == "UNKNOWN"]
    nonrepairable_critical = [
        item
        for item in failed
        if item.severity == "critical" and not item.repairable
    ]
    if nonrepairable_critical:
        return (
            "REJECT",
            "BLOCKED",
            [
                f"{item.check_id}: non-repairable critical failure"
                for item in nonrepairable_critical
            ],
        )
    if failed and all(item.repairable and item.shot_id for item in failed):
        return "REPAIR", "NEEDS_REVISION", []
    if failed or unknown:
        return (
            "HUMAN_REVIEW",
            "BLOCKED",
            [
                *[
                    f"{item.check_id}: non-automatic failure"
                    for item in failed
                    if not (item.repairable and item.shot_id)
                ],
                *[
                    f"{item.check_id}: uncertain observation"
                    for item in unknown
                ],
            ],
        )
    return "PASS", "PASS", []


def run_media_qa(
    product_id: str,
    *,
    plan_id: str,
    manifest_id: str,
    ocr_adapter: OcrAdapter | None,
    visual_adapter: VisualAdapter | None,
    qa_run: int = 1,
) -> MediaQaReportArtifact:
    """Run all M14 QA ports and persist one immutable report."""

    plan = load_professional_artifact(product_id, plan_id)
    if not isinstance(plan, MediaExecutionPlanArtifact):
        raise ValueError("media QA requires a Media Execution Plan")
    checks = inspect_media_technical_quality(
        product_id,
        plan_id=plan_id,
        manifest_id=manifest_id,
    )
    checks.extend(
        inspect_media_text_quality(
            product_id,
            plan_id=plan_id,
            manifest_id=manifest_id,
            ocr_adapter=ocr_adapter,
        )
    )
    if plan.product_plate_id:
        checks.extend(
            inspect_packaging_visual_quality(
                product_id,
                plan_id=plan_id,
                manifest_id=manifest_id,
                product_plate_id=plan.product_plate_id,
            )
        )
    checks.extend(
        inspect_story_continuity_quality(
            product_id,
            plan_id=plan_id,
            manifest_id=manifest_id,
            visual_adapter=visual_adapter,
        )
    )
    overall, status, blockers = _overall_result(checks)
    failed_shot_ids = sorted(
        {
            item.shot_id
            for item in checks
            if item.status == "FAIL" and item.shot_id
        }
    )
    warnings = [
        f"{item.check_id}: {item.observed}"
        for item in checks
        if item.status == "WARN"
    ]
    evidence_refs = list(
        dict.fromkeys(
            evidence
            for item in checks
            for evidence in item.evidence
        )
    )
    adapter_provenance: dict[str, Any] = {
        "policy_version": MEDIA_QA_POLICY_VERSION,
        "ocr_adapter": (
            getattr(ocr_adapter, "__name__", type(ocr_adapter).__name__)
            if ocr_adapter is not None
            else "unavailable"
        ),
        "visual_adapter": (
            getattr(visual_adapter, "__name__", type(visual_adapter).__name__)
            if visual_adapter is not None
            else "unavailable"
        ),
    }
    report_identity = hashlib.sha256(
        f"{plan.task_id}\0{manifest_id}".encode("utf-8")
    ).hexdigest()[:20]
    report = MediaQaReportArtifact(
        artifact_id=f"media-qa-{report_identity}-run-{qa_run}",
        task_id=plan.task_id,
        product_id=plan.product_id,
        created_at=now_iso(),
        source_refs=[plan_id, manifest_id],
        status=status,
        plan_id=plan_id,
        manifest_id=manifest_id,
        qa_run=qa_run,
        overall_result=overall,
        checks=checks,
        failed_shot_ids=failed_shot_ids,
        hard_blockers=blockers,
        warnings=warnings,
        evidence_refs=evidence_refs,
        model_provenance=adapter_provenance,
    )
    save_professional_artifact(report)
    return report
