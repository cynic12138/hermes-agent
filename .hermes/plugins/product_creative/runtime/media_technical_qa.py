"""Deterministic technical QA for M13 shot and composite media."""

from __future__ import annotations

from fractions import Fraction
import hashlib
from pathlib import Path
import re
import struct
import subprocess
from typing import Any

from ..common import ensure_product
from ..contracts.creative_artifacts import (
    MediaCompositeManifestArtifact,
    MediaExecutionPlanArtifact,
    MediaQualityCheck,
    MediaShotResultArtifact,
)
from .media_compositor import probe_media
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
        raise ValueError("media QA path must stay inside the product workspace")
    return path


def _check(
    check_id: str,
    *,
    category: str,
    scope: str,
    status: str,
    severity: str,
    expected: dict[str, Any],
    observed: dict[str, Any],
    evidence: list[str],
    shot_id: str = "",
    time_range: tuple[float, float] | None = None,
    repairable: bool = False,
) -> MediaQualityCheck:
    return MediaQualityCheck(
        check_id=check_id,
        category=category,
        scope=scope,
        status=status,
        severity=severity,
        shot_id=shot_id,
        time_range=time_range,
        expected=expected,
        observed=observed,
        evidence=evidence,
        repairable=repairable and status != "PASS",
    )


def _video_stream(probe: dict[str, Any]) -> dict[str, Any]:
    return next(
        (
            stream
            for stream in probe.get("streams") or []
            if stream.get("codec_type") == "video"
        ),
        {},
    )


def _audio_stream(probe: dict[str, Any]) -> dict[str, Any]:
    return next(
        (
            stream
            for stream in probe.get("streams") or []
            if stream.get("codec_type") == "audio"
        ),
        {},
    )


def _duration(probe: dict[str, Any]) -> float:
    try:
        return float((probe.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        return 0


def _fps(stream: dict[str, Any]) -> float:
    value = str(
        stream.get("avg_frame_rate")
        or stream.get("r_frame_rate")
        or "0"
    )
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0


def _top_level_boxes(path: Path) -> list[str]:
    boxes: list[str] = []
    file_size = path.stat().st_size
    with path.open("rb") as stream:
        position = 0
        while position + 8 <= file_size:
            stream.seek(position)
            header = stream.read(8)
            if len(header) != 8:
                break
            size, box_type = struct.unpack(">I4s", header)
            header_size = 8
            if size == 1:
                extended = stream.read(8)
                if len(extended) != 8:
                    break
                size = struct.unpack(">Q", extended)[0]
                header_size = 16
            elif size == 0:
                size = file_size - position
            if size < header_size:
                break
            boxes.append(box_type.decode("ascii", errors="replace"))
            position += size
    return boxes


def _ffmpeg_analysis(path: Path, filter_expression: str) -> str:
    ffmpeg = resolve_media_tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for technical media QA")
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vf",
            filter_expression,
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffmpeg QA failed")[-2000:])
    return result.stderr or ""


def _audio_analysis(path: Path, filter_expression: str) -> str:
    ffmpeg = resolve_media_tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for technical media QA")
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vn",
            "-af",
            filter_expression,
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffmpeg audio QA failed")[-2000:])
    return result.stderr or ""


def _sum_metric(output: str, name: str) -> float:
    values = re.findall(
        rf"{re.escape(name)}\s*:\s*([0-9]+(?:\.[0-9]+)?)",
        output,
    )
    return sum(float(value) for value in values)


def _black_check(
    path: Path,
    *,
    shot_id: str,
    duration: float,
) -> MediaQualityCheck:
    output = _ffmpeg_analysis(
        path,
        "blackdetect=d=0.10:pix_th=0.10:pic_th=0.98",
    )
    black_duration = _sum_metric(output, "black_duration")
    ratio = min(1.0, black_duration / duration) if duration > 0 else 0
    if ratio >= 0.8:
        status, severity, repairable = "FAIL", "high", True
    elif ratio >= 0.1:
        status, severity, repairable = "WARN", "medium", True
    else:
        status, severity, repairable = "PASS", "low", False
    return _check(
        f"black-frame:{shot_id}",
        category="technical",
        scope="shot",
        status=status,
        severity=severity,
        shot_id=shot_id,
        time_range=(0.0, duration),
        expected={"maximum_black_ratio": 0.1},
        observed={
            "black_duration_seconds": round(black_duration, 4),
            "black_ratio": round(ratio, 4),
        },
        evidence=[f"ffmpeg:blackdetect:{shot_id}"],
        repairable=repairable,
    )


def _freeze_check(
    path: Path,
    *,
    shot_id: str,
    duration: float,
    motion_required: bool = False,
    maximum_freeze_ratio: float = 0.8,
) -> MediaQualityCheck:
    output = _ffmpeg_analysis(
        path,
        "freezedetect=n=-50dB:d=0.30",
    )
    freeze_duration = _sum_metric(output, "freeze_duration")
    freeze_starts = [
        float(value)
        for value in re.findall(
            r"freeze_start\s*:\s*([0-9]+(?:\.[0-9]+)?)",
            output,
        )
    ]
    completed_freezes = re.findall(
        r"freeze_duration\s*:\s*([0-9]+(?:\.[0-9]+)?)",
        output,
    )
    # freezedetect does not emit freeze_duration when a freeze continues to
    # end-of-file. Count that open interval explicitly or a fully static clip
    # would be reported as having zero frozen seconds.
    if len(freeze_starts) > len(completed_freezes):
        freeze_duration += max(0.0, duration - freeze_starts[-1])
    ratio = min(1.0, freeze_duration / duration) if duration > 0 else 0
    threshold = maximum_freeze_ratio if motion_required else 0.8
    excessive_freeze = ratio >= threshold and duration >= 0.5
    if excessive_freeze and motion_required:
        status, severity = "FAIL", "high"
    elif excessive_freeze:
        status, severity = "WARN", "medium"
    else:
        status, severity = "PASS", "low"
    return _check(
        f"freeze-frame:{shot_id}",
        category="technical",
        scope="shot",
        status=status,
        severity=severity,
        shot_id=shot_id,
        time_range=(0.0, duration),
        expected={
            "motion_required": motion_required,
            "maximum_freeze_ratio": threshold,
        },
        observed={
            "freeze_duration_seconds": round(freeze_duration, 4),
            "freeze_ratio": round(ratio, 4),
        },
        evidence=[f"ffmpeg:freezedetect:{shot_id}"],
        repairable=status != "PASS",
    )


def _audio_checks(path: Path, *, duration: float) -> list[MediaQualityCheck]:
    silence_output = _audio_analysis(
        path,
        "silencedetect=noise=-50dB:d=0.20",
    )
    silence_duration = _sum_metric(silence_output, "silence_duration")
    silence_ratio = (
        min(1.0, silence_duration / duration)
        if duration > 0
        else 0
    )
    silence_status = "WARN" if silence_ratio >= 0.95 else "PASS"
    volume_output = _audio_analysis(path, "volumedetect")
    match = re.search(r"max_volume:\s*(-?(?:inf|[0-9.]+))\s*dB", volume_output)
    raw_peak = match.group(1) if match else ""
    peak = (
        float("-inf")
        if raw_peak == "-inf"
        else float(raw_peak)
        if raw_peak
        else None
    )
    clipping = peak is not None and peak >= -0.1
    return [
        _check(
            "final-silence-ratio",
            category="technical",
            scope="audio",
            status=silence_status,
            severity="medium" if silence_status == "WARN" else "low",
            expected={"maximum_silence_ratio": 0.95},
            observed={"silence_ratio": round(silence_ratio, 4)},
            evidence=["ffmpeg:silencedetect:final"],
            repairable=silence_status == "WARN",
        ),
        _check(
            "final-peak-clipping",
            category="technical",
            scope="audio",
            status="WARN" if clipping else "PASS",
            severity="high" if clipping else "low",
            expected={"maximum_peak_db": -0.1},
            observed={"max_volume_db": peak},
            evidence=["ffmpeg:volumedetect:final"],
            repairable=clipping,
        ),
    ]


def inspect_media_technical_quality(
    product_id: str,
    *,
    plan_id: str,
    manifest_id: str,
    duration_tolerance_seconds: float = 0.35,
) -> list[MediaQualityCheck]:
    """Inspect M13 media without network, LLM, Provider, or durable mutation."""

    product_root = ensure_product(product_id)
    plan = load_professional_artifact(product_root.name, plan_id)
    manifest = load_professional_artifact(product_root.name, manifest_id)
    if not isinstance(plan, MediaExecutionPlanArtifact):
        raise ValueError("technical media QA requires a Media Execution Plan")
    if not isinstance(manifest, MediaCompositeManifestArtifact):
        raise ValueError("technical media QA requires a Composite Manifest")
    if manifest.plan_id != plan.artifact_id:
        raise ValueError("media manifest does not belong to the supplied plan")

    output = _workspace_path(product_root, manifest.output_relative_path)
    if not output.is_file():
        return [
            _check(
                "final-file-readable",
                category="technical",
                scope="final",
                status="FAIL",
                severity="critical",
                expected={"exists": True, "readable": True},
                observed={"exists": False, "readable": False},
                evidence=[f"manifest:{manifest.artifact_id}"],
                repairable=False,
            )
        ]

    probe = probe_media(output)
    video = _video_stream(probe)
    audio = _audio_stream(probe)
    actual_duration = _duration(probe)
    expected_duration = sum(shot.duration_seconds for shot in plan.shots)
    expected_codec = str(plan.output_requirements.get("codec") or "h264")
    expected_audio = str(plan.output_requirements.get("audio_codec") or "aac")
    expected_pixel_format = str(
        plan.output_requirements.get("pixel_format") or "yuv420p"
    )
    boxes = _top_level_boxes(output)
    faststart = (
        "moov" in boxes
        and "mdat" in boxes
        and boxes.index("moov") < boxes.index("mdat")
    )
    checks = [
        _check(
            "final-file-readable",
            category="technical",
            scope="final",
            status="PASS",
            severity="low",
            expected={"exists": True, "readable": True},
            observed={"exists": True, "readable": True},
            evidence=[f"manifest:{manifest.artifact_id}"],
        ),
        _check(
            "final-content-hash",
            category="technical",
            scope="final",
            status=(
                "PASS"
                if _sha256(output) == manifest.output_content_hash
                else "FAIL"
            ),
            severity="critical",
            expected={"sha256": manifest.output_content_hash},
            observed={"sha256": _sha256(output)},
            evidence=[f"file:{manifest.output_relative_path}"],
            repairable=False,
        ),
        _check(
            "final-video-codec",
            category="technical",
            scope="final",
            status="PASS" if video.get("codec_name") == expected_codec else "FAIL",
            severity="critical",
            expected={"codec": expected_codec},
            observed={"codec": str(video.get("codec_name") or "")},
            evidence=["ffprobe:final:video"],
            repairable=True,
        ),
        _check(
            "final-pixel-format",
            category="technical",
            scope="final",
            status=(
                "PASS"
                if video.get("pix_fmt") == expected_pixel_format
                else "FAIL"
            ),
            severity="high",
            expected={"pixel_format": expected_pixel_format},
            observed={"pixel_format": str(video.get("pix_fmt") or "")},
            evidence=["ffprobe:final:video"],
            repairable=True,
        ),
        _check(
            "final-audio-codec",
            category="technical",
            scope="audio",
            status="PASS" if audio.get("codec_name") == expected_audio else "FAIL",
            severity="high",
            expected={"codec": expected_audio},
            observed={"codec": str(audio.get("codec_name") or "")},
            evidence=["ffprobe:final:audio"],
            repairable=True,
        ),
        _check(
            "final-canvas",
            category="technical",
            scope="final",
            status=(
                "PASS"
                if (
                    int(video.get("width") or 0),
                    int(video.get("height") or 0),
                )
                == plan.canvas
                else "FAIL"
            ),
            severity="high",
            expected={"width": plan.canvas[0], "height": plan.canvas[1]},
            observed={
                "width": int(video.get("width") or 0),
                "height": int(video.get("height") or 0),
            },
            evidence=["ffprobe:final:video"],
            repairable=True,
        ),
        _check(
            "final-fps",
            category="technical",
            scope="final",
            status="PASS" if abs(_fps(video) - plan.fps) <= 0.01 else "FAIL",
            severity="medium",
            expected={"fps": plan.fps},
            observed={"fps": _fps(video)},
            evidence=["ffprobe:final:video"],
            repairable=True,
        ),
        _check(
            "final-duration",
            category="technical",
            scope="final",
            status=(
                "PASS"
                if abs(actual_duration - expected_duration)
                <= duration_tolerance_seconds
                else "FAIL"
            ),
            severity="high",
            expected={
                "duration_seconds": expected_duration,
                "tolerance_seconds": duration_tolerance_seconds,
            },
            observed={"duration_seconds": actual_duration},
            evidence=["ffprobe:final:format"],
            repairable=True,
        ),
        _check(
            "final-faststart",
            category="technical",
            scope="final",
            status="PASS" if faststart else "FAIL",
            severity="medium",
            expected={"moov_before_mdat": True},
            observed={"top_level_boxes": boxes},
            evidence=["mp4:box-order"],
            repairable=True,
        ),
    ]

    shot_results: list[MediaShotResultArtifact] = []
    for artifact_id in manifest.shot_result_ids:
        artifact = load_professional_artifact(product_root.name, artifact_id)
        if not isinstance(artifact, MediaShotResultArtifact):
            raise ValueError("composite manifest contains a non-shot artifact")
        shot_results.append(artifact)
    expected_order = [shot.shot_id for shot in plan.shots]
    observed_order = [result.shot_id for result in shot_results]
    checks.append(
        _check(
            "shot-order",
            category="technical",
            scope="final",
            status="PASS" if observed_order == expected_order else "FAIL",
            severity="critical",
            expected={"shot_ids": expected_order},
            observed={"shot_ids": observed_order},
            evidence=[f"manifest:{manifest.artifact_id}"],
            repairable=False,
        )
    )

    planned_by_id = {shot.shot_id: shot for shot in plan.shots}
    for result in shot_results:
        planned = planned_by_id.get(result.shot_id)
        if planned is None:
            continue
        shot_path = _workspace_path(product_root, result.output_relative_path)
        shot_probe = probe_media(shot_path)
        shot_duration = _duration(shot_probe)
        checks.append(
            _check(
                f"shot-duration:{result.shot_id}",
                category="technical",
                scope="shot",
                status=(
                    "PASS"
                    if abs(shot_duration - planned.duration_seconds)
                    <= duration_tolerance_seconds
                    else "FAIL"
                ),
                severity="high",
                shot_id=result.shot_id,
                time_range=(0.0, shot_duration),
                expected={
                    "duration_seconds": planned.duration_seconds,
                    "tolerance_seconds": duration_tolerance_seconds,
                },
                observed={"duration_seconds": shot_duration},
                evidence=[f"ffprobe:shot:{result.shot_id}"],
                repairable=True,
            )
        )
        checks.append(
            _black_check(
                shot_path,
                shot_id=result.shot_id,
                duration=shot_duration,
            )
        )
        checks.append(
            _freeze_check(
                shot_path,
                shot_id=result.shot_id,
                duration=shot_duration,
                motion_required=planned.motion_required,
                maximum_freeze_ratio=planned.maximum_freeze_ratio,
            )
        )

    if audio:
        checks.extend(_audio_checks(output, duration=actual_duration))
    return checks
