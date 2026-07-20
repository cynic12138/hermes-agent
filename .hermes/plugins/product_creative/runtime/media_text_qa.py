"""Subtitle source and OCR-visible text QA for M14 media."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable

from ..common import ensure_product
from ..contracts.creative_artifacts import (
    MediaCompositeManifestArtifact,
    MediaExecutionPlanArtifact,
    MediaQualityCheck,
    MediaShotResultArtifact,
)
from .professional_artifacts import load_professional_artifact


OcrAdapter = Callable[..., dict[str, Any]]
_GARBLE_PATTERN = re.compile(r"\ufffd|\?{2,}|�")


def _workspace_path(product_root: Path, relative_path: str) -> Path:
    root = product_root.resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ValueError("media text QA path must stay inside the product workspace")
    return path


def _normalize_text(value: str) -> str:
    return re.sub(r"[\s，。！？、,.!?：:；;“”\"'（）()【】\[\]-]+", "", value)


def _check(
    check_id: str,
    *,
    status: str,
    severity: str,
    shot_id: str,
    expected: dict[str, Any],
    observed: dict[str, Any],
    evidence: list[str],
    repairable: bool,
) -> MediaQualityCheck:
    return MediaQualityCheck(
        check_id=check_id,
        category="subtitle",
        scope="subtitle",
        status=status,
        severity=severity,
        shot_id=shot_id,
        expected=expected,
        observed=observed,
        evidence=evidence,
        repairable=repairable and status != "PASS",
    )


def _unknown_checks(
    shot_id: str,
    expected_text: str,
    evidence: list[str],
) -> list[MediaQualityCheck]:
    reason = "A real OCR observation is required to prove rendered subtitle visibility."
    return [
        _check(
            f"subtitle-visible:{shot_id}",
            status="UNKNOWN",
            severity="high",
            shot_id=shot_id,
            expected={"text": expected_text, "minimum_confidence": 0.8},
            observed={"reason": reason},
            evidence=evidence,
            repairable=False,
        ),
        _check(
            f"subtitle-safe-area:{shot_id}",
            status="UNKNOWN",
            severity="high",
            shot_id=shot_id,
            expected={"normalized_safe_area": [0.03, 0.03, 0.97, 0.95]},
            observed={"reason": reason},
            evidence=evidence,
            repairable=False,
        ),
        _check(
            f"subtitle-duration:{shot_id}",
            status="UNKNOWN",
            severity="medium",
            shot_id=shot_id,
            expected={"visible": True},
            observed={"reason": reason},
            evidence=evidence,
            repairable=False,
        ),
    ]


def inspect_media_text_quality(
    product_id: str,
    *,
    plan_id: str,
    manifest_id: str,
    ocr_adapter: OcrAdapter | None,
    minimum_confidence: float = 0.8,
) -> list[MediaQualityCheck]:
    """Inspect deterministic subtitle sources and optional real OCR observations."""

    product_root = ensure_product(product_id)
    plan = load_professional_artifact(product_root.name, plan_id)
    manifest = load_professional_artifact(product_root.name, manifest_id)
    if not isinstance(plan, MediaExecutionPlanArtifact):
        raise ValueError("media text QA requires a Media Execution Plan")
    if not isinstance(manifest, MediaCompositeManifestArtifact):
        raise ValueError("media text QA requires a Composite Manifest")
    if manifest.plan_id != plan.artifact_id:
        raise ValueError("media text QA manifest does not belong to the plan")

    result_by_shot: dict[str, MediaShotResultArtifact] = {}
    for artifact_id in manifest.shot_result_ids:
        artifact = load_professional_artifact(product_root.name, artifact_id)
        if isinstance(artifact, MediaShotResultArtifact):
            result_by_shot[artifact.shot_id] = artifact

    checks: list[MediaQualityCheck] = []
    for shot in plan.shots:
        expected_text = shot.caption.strip()
        if not expected_text:
            continue
        result = result_by_shot.get(shot.shot_id)
        if result is None:
            checks.append(
                _check(
                    f"subtitle-source:{shot.shot_id}",
                    status="FAIL",
                    severity="critical",
                    shot_id=shot.shot_id,
                    expected={"text": expected_text, "ass_exists": True},
                    observed={"ass_exists": False, "reason": "shot result is missing"},
                    evidence=[f"manifest:{manifest.artifact_id}"],
                    repairable=True,
                )
            )
            continue
        media_path = _workspace_path(product_root, result.output_relative_path)
        ass_path = media_path.with_suffix(".ass")
        source_text = (
            ass_path.read_text(encoding="utf-8-sig")
            if ass_path.is_file()
            else ""
        )
        normalized_expected = _normalize_text(expected_text)
        source_matches = (
            ass_path.is_file()
            and normalized_expected in _normalize_text(source_text)
            and not _GARBLE_PATTERN.search(source_text)
        )
        checks.append(
            _check(
                f"subtitle-source:{shot.shot_id}",
                status="PASS" if source_matches else "FAIL",
                severity="low" if source_matches else "critical",
                shot_id=shot.shot_id,
                expected={"text": expected_text, "ass_exists": True},
                observed={
                    "ass_exists": ass_path.is_file(),
                    "source_matches": source_matches,
                    "garbled_source": bool(_GARBLE_PATTERN.search(source_text)),
                },
                evidence=[f"ass:{ass_path.relative_to(product_root)}"],
                repairable=not source_matches,
            )
        )
        if ocr_adapter is None:
            checks.extend(
                _unknown_checks(
                    shot.shot_id,
                    expected_text,
                    [f"media:{result.output_relative_path}"],
                )
            )
            continue
        observation = ocr_adapter(
            product_id=product_root.name,
            shot_id=shot.shot_id,
            media_path=media_path,
            expected_text=expected_text,
            start_seconds=0.0,
            end_seconds=shot.duration_seconds,
        )
        confidence = float(observation.get("confidence") or 0)
        evidence = [
            str(item)
            for item in observation.get("evidence_refs") or []
            if str(item).strip()
        ] or [f"ocr:{shot.shot_id}"]
        if confidence < minimum_confidence:
            checks.extend(
                _unknown_checks(
                    shot.shot_id,
                    expected_text,
                    evidence,
                )
            )
            continue
        observed_text = str(observation.get("observed_text") or "")
        visible_matches = (
            normalized_expected in _normalize_text(observed_text)
            and not _GARBLE_PATTERN.search(observed_text)
        )
        checks.append(
            _check(
                f"subtitle-visible:{shot.shot_id}",
                status="PASS" if visible_matches else "FAIL",
                severity="low" if visible_matches else "critical",
                shot_id=shot.shot_id,
                expected={
                    "text": expected_text,
                    "minimum_confidence": minimum_confidence,
                },
                observed={
                    "text": observed_text,
                    "confidence": confidence,
                    "garbled": bool(_GARBLE_PATTERN.search(observed_text)),
                },
                evidence=evidence,
                repairable=not visible_matches,
            )
        )
        box = observation.get("bounding_box")
        safe = (
            isinstance(box, (list, tuple))
            and len(box) == 4
            and float(box[0]) >= 0.03
            and float(box[1]) >= 0.03
            and float(box[0]) + float(box[2]) <= 0.97
            and float(box[1]) + float(box[3]) <= 0.95
        )
        checks.append(
            _check(
                f"subtitle-safe-area:{shot.shot_id}",
                status="PASS" if safe else "FAIL",
                severity="low" if safe else "high",
                shot_id=shot.shot_id,
                expected={"normalized_safe_area": [0.03, 0.03, 0.97, 0.95]},
                observed={"bounding_box": list(box) if box else []},
                evidence=evidence,
                repairable=not safe,
            )
        )
        visible_duration = float(
            observation.get("visible_duration_seconds") or 0
        )
        minimum_duration = min(
            shot.duration_seconds,
            max(0.3, shot.duration_seconds * 0.5),
        )
        long_enough = visible_duration >= minimum_duration
        checks.append(
            _check(
                f"subtitle-duration:{shot.shot_id}",
                status="PASS" if long_enough else "FAIL",
                severity="low" if long_enough else "medium",
                shot_id=shot.shot_id,
                expected={"minimum_visible_seconds": minimum_duration},
                observed={"visible_duration_seconds": visible_duration},
                evidence=evidence,
                repairable=not long_enough,
            )
        )
    return checks
