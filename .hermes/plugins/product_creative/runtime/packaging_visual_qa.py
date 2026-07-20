"""Deterministic Product Plate provenance and frame-fidelity QA."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import Any

from PIL import Image, ImageChops, ImageStat

from ..common import ensure_product
from ..contracts.creative_artifacts import (
    MediaCompositeManifestArtifact,
    MediaExecutionPlanArtifact,
    MediaQualityCheck,
    MediaShotResultArtifact,
    ProductPlateArtifact,
)
from .media_dependencies import resolve_media_tool
from .professional_artifacts import load_professional_artifact


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _workspace_path(product_root: Path, relative_path: str) -> Path:
    root = product_root.resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ValueError("packaging QA path must stay inside the product workspace")
    return path


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
        category="packaging",
        scope="packaging",
        status=status,
        severity=severity,
        shot_id=shot_id,
        expected=expected,
        observed=observed,
        evidence=evidence,
        repairable=repairable and status != "PASS",
    )


def _extract_frame(
    media_path: Path,
    output_path: Path,
    at_seconds: float,
) -> None:
    ffmpeg = resolve_media_tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for packaging visual QA")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(max(0.0, at_seconds)),
            "-i",
            str(media_path),
            "-frames:v",
            "1",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if result.returncode != 0 or not output_path.is_file():
        raise RuntimeError((result.stderr or "frame extraction failed")[-2000:])


def _plate_geometry(
    plate: Image.Image,
    canvas: tuple[int, int],
) -> tuple[int, int, int, int]:
    width, height = canvas
    scale = min(
        width * 0.72 / plate.width,
        height * 0.46 / plate.height,
        1.0,
    )
    plate_width = max(1, round(plate.width * scale))
    plate_height = max(1, round(plate.height * scale))
    left = round((width - plate_width) / 2)
    top = height - plate_height - max(20, round(height * 0.08))
    return left, top, plate_width, plate_height


def _opaque_mean_absolute_error(
    frame_crop: Image.Image,
    plate: Image.Image,
) -> tuple[float, int]:
    expected = plate.convert("RGBA")
    actual = frame_crop.convert("RGB")
    expected_rgb = expected.convert("RGB")
    alpha = expected.getchannel("A")
    mask = alpha.point(lambda value: 255 if value >= 200 else 0)
    opaque_pixels = sum(mask.histogram()[1:])
    if opaque_pixels == 0:
        return 255.0, 0
    difference = ImageChops.difference(actual, expected_rgb)
    masked = Image.new("RGB", difference.size, (0, 0, 0))
    masked.paste(difference, mask=mask)
    channel_sums = ImageStat.Stat(masked).sum
    mean = sum(channel_sums) / (opaque_pixels * 3)
    return float(mean), opaque_pixels


def inspect_packaging_visual_quality(
    product_id: str,
    *,
    plan_id: str,
    manifest_id: str,
    product_plate_id: str,
) -> list[MediaQualityCheck]:
    """Verify M13 plate provenance and compare rendered product pixels."""

    product_root = ensure_product(product_id)
    plan = load_professional_artifact(product_root.name, plan_id)
    manifest = load_professional_artifact(product_root.name, manifest_id)
    plate_artifact = load_professional_artifact(
        product_root.name,
        product_plate_id,
    )
    if not isinstance(plan, MediaExecutionPlanArtifact):
        raise ValueError("packaging QA requires a Media Execution Plan")
    if not isinstance(manifest, MediaCompositeManifestArtifact):
        raise ValueError("packaging QA requires a Composite Manifest")
    if not isinstance(plate_artifact, ProductPlateArtifact):
        raise ValueError("packaging QA requires a Product Plate")
    if manifest.plan_id != plan.artifact_id:
        raise ValueError("packaging QA manifest does not belong to the plan")
    if plan.product_plate_id != plate_artifact.artifact_id:
        raise ValueError("packaging QA plate does not belong to the plan")

    plate_path = _workspace_path(
        product_root,
        plate_artifact.plate_relative_path,
    )
    actual_plate_hash = _sha256(plate_path)
    result_by_shot: dict[str, MediaShotResultArtifact] = {}
    for artifact_id in manifest.shot_result_ids:
        artifact = load_professional_artifact(product_root.name, artifact_id)
        if isinstance(artifact, MediaShotResultArtifact):
            result_by_shot[artifact.shot_id] = artifact

    checks: list[MediaQualityCheck] = []
    for shot in plan.shots:
        if not shot.product_plate_required:
            continue
        result = result_by_shot.get(shot.shot_id)
        if result is None:
            checks.append(
                _check(
                    f"packaging-source-integrity:{shot.shot_id}",
                    status="FAIL",
                    severity="critical",
                    shot_id=shot.shot_id,
                    expected={"shot_result": True},
                    observed={"shot_result": False},
                    evidence=[f"manifest:{manifest.artifact_id}"],
                    repairable=False,
                )
            )
            continue
        recorded_plate_hash = str(result.input_hashes.get("product_plate") or "")
        source_intact = (
            actual_plate_hash == plate_artifact.plate_content_hash
            and recorded_plate_hash == plate_artifact.plate_content_hash
        )
        checks.append(
            _check(
                f"packaging-source-integrity:{shot.shot_id}",
                status="PASS" if source_intact else "FAIL",
                severity="low" if source_intact else "critical",
                shot_id=shot.shot_id,
                expected={"plate_sha256": plate_artifact.plate_content_hash},
                observed={
                    "workspace_plate_sha256": actual_plate_hash,
                    "shot_input_plate_sha256": recorded_plate_hash,
                },
                evidence=[
                    f"plate:{plate_artifact.artifact_id}",
                    f"shot-result:{result.artifact_id}",
                ],
                repairable=False,
            )
        )
        provenance = "alpha-overlay product plate" in " ".join(
            result.command_summary
        )
        checks.append(
            _check(
                f"packaging-compositor-provenance:{shot.shot_id}",
                status="PASS" if provenance else "FAIL",
                severity="low" if provenance else "critical",
                shot_id=shot.shot_id,
                expected={"immutable_plate_overlay": True},
                observed={"immutable_plate_overlay": provenance},
                evidence=[f"shot-result:{result.artifact_id}"],
                repairable=False,
            )
        )

        media_path = _workspace_path(product_root, result.output_relative_path)
        evidence_path = (
            product_root
            / "artifacts"
            / "media_qa"
            / "packaging"
            / plan.artifact_id
            / f"{shot.shot_id}.png"
        )
        _extract_frame(
            media_path,
            evidence_path,
            min(shot.duration_seconds / 2, max(0.0, shot.duration_seconds - 0.05)),
        )
        with Image.open(plate_path) as plate_image, Image.open(
            evidence_path
        ) as frame_image:
            left, top, plate_width, plate_height = _plate_geometry(
                plate_image,
                plan.canvas,
            )
            resized_plate = plate_image.convert("RGBA").resize(
                (plate_width, plate_height),
                Image.Resampling.LANCZOS,
            )
            frame_crop = frame_image.convert("RGB").crop(
                (left, top, left + plate_width, top + plate_height)
            )
            mean_error, opaque_pixels = _opaque_mean_absolute_error(
                frame_crop,
                resized_plate,
            )
        if mean_error < 24:
            status, severity, repairable = "PASS", "low", False
        elif mean_error < 45:
            status, severity, repairable = "WARN", "high", True
        else:
            status, severity, repairable = "FAIL", "critical", True
        checks.append(
            _check(
                f"packaging-fidelity:{shot.shot_id}",
                status=status,
                severity=severity,
                shot_id=shot.shot_id,
                expected={
                    "maximum_mean_absolute_error": 24,
                    "transform": "uniform_scale_translate_alpha_overlay",
                },
                observed={
                    "mean_absolute_error": round(mean_error, 4),
                    "opaque_pixels_compared": opaque_pixels,
                    "plate_box": [left, top, plate_width, plate_height],
                    "mask_mode": plate_artifact.mask_mode,
                },
                evidence=[
                    f"frame:{evidence_path.relative_to(product_root)}",
                    f"plate:{plate_artifact.plate_relative_path}",
                ],
                repairable=repairable,
            )
        )
    return checks
