"""Deterministic shot rendering and final MP4 composition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from ..common import ensure_product, now_iso
from ..contracts.creative_artifacts import (
    MediaCompositeManifestArtifact,
    MediaExecutionPlanArtifact,
    MediaShotPlan,
    MediaShotResultArtifact,
    ProductPlateArtifact,
)
from .media_dependencies import resolve_media_tool
from .professional_artifacts import save_professional_artifact


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _workspace_path(product_root: Path, path: Path) -> Path:
    root = product_root.resolve()
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError("media path must stay inside the product workspace")
    return resolved


def _run(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown ffmpeg error").strip()
        raise RuntimeError(detail[-2000:])


def probe_media(path: Path) -> dict[str, Any]:
    ffprobe = resolve_media_tool("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required for media verification")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "ffprobe failed").strip())
    return json.loads(result.stdout)


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, cents = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cents:02d}"


def _ass_escape(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def _write_ass(path: Path, caption: str, plan: MediaExecutionPlanArtifact, duration: float) -> None:
    width, height = plan.canvas
    font_size = max(18, round(height * 0.045))
    margin_vertical = max(24, round(height * 0.06))
    body = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
        "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
        "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Default,Microsoft YaHei,{font_size},&H00FFFFFF,&H00FFFFFF,"
        "&H00161616,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,"
        f"40,40,{margin_vertical},1\n\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,"
        "Effect,Text\n"
        f"Dialogue: 0,{_ass_time(0)},{_ass_time(duration)},Default,,0,0,0,,"
        f"{_ass_escape(caption)}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8-sig")


def _filter_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value


def _source_is_image(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


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


def render_shot(
    product_id: str,
    *,
    plan: MediaExecutionPlanArtifact,
    shot: MediaShotPlan,
    source_media: Path,
    product_plate: ProductPlateArtifact | None,
    attempt: int,
) -> MediaShotResultArtifact:
    """Normalize one source to H.264/AAC and add immutable product/text layers."""

    product_root = ensure_product(product_id)
    if plan.product_id != product_root.name:
        raise ValueError("media plan belongs to a different product workspace")
    if shot.shot_id not in {item.shot_id for item in plan.shots}:
        raise ValueError("shot is not part of the media plan")
    source = _workspace_path(product_root, source_media)
    if not source.is_file():
        raise FileNotFoundError(f"shot source does not exist: {source}")
    ffmpeg = resolve_media_tool("ffmpeg")
    task_token = hashlib.sha256(plan.task_id.encode("utf-8")).hexdigest()[:10]
    artifact_id = (
        f"media-shot-{task_token}-{shot.shot_id}-"
        f"{plan.content_hash[:10]}-a{attempt}"
    )
    if not ffmpeg:
        artifact = MediaShotResultArtifact(
            artifact_id=artifact_id,
            task_id=plan.task_id,
            product_id=product_root.name,
            created_at=now_iso(),
            source_refs=[plan.artifact_id, f"source:{_sha256(source)}"],
            status="BLOCKED",
            plan_id=plan.artifact_id,
            shot_id=shot.shot_id,
            attempt=attempt,
            execution_status="FAILED_FINAL",
            provider="local-compositor",
            external_call_performed=False,
            input_hashes={"source_media": _sha256(source)},
            source_relative_path=str(source.relative_to(product_root)),
            error_code="ffmpeg_missing",
            error_detail="ffmpeg is required for deterministic shot rendering",
            command_summary=[],
        )
        save_professional_artifact(artifact)
        return artifact

    output_dir = (
        product_root
        / "artifacts"
        / "media_shots"
        / plan.artifact_id
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{shot.ordinal:02d}-{shot.shot_id}.mp4"
    subtitle = output_dir / f"{shot.ordinal:02d}-{shot.shot_id}.ass"
    input_hashes = {"source_media": _sha256(source)}
    command_summary = [
        f"normalize {shot.shot_id} to {plan.canvas[0]}x{plan.canvas[1]}@{plan.fps}",
        "attach silent stereo AAC",
    ]
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    if _source_is_image(source):
        command.extend(["-loop", "1", "-i", str(source)])
    else:
        command.extend(["-stream_loop", "-1", "-i", str(source)])

    plate_path: Path | None = None
    if shot.product_plate_required:
        if product_plate is None:
            raise ValueError("shot requires a product plate")
        if product_plate.product_id != product_root.name:
            raise ValueError("product plate belongs to a different workspace")
        plate_path = _workspace_path(
            product_root,
            product_root / product_plate.plate_relative_path,
        )
        command.extend(["-i", str(plate_path)])
        input_hashes["product_plate"] = _sha256(plate_path)
        command_summary.append(
            f"uniform-scale and alpha-overlay product plate {product_plate.artifact_id}"
        )
        if shot.product_plate_motion == "subtle_entrance":
            command_summary.append(
                "apply 0.30s vertical entrance, then keep product plate static"
            )

    audio_index = 2 if plate_path else 1
    command.extend(
        [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
        ]
    )
    width, height = plan.canvas
    filters = [
        (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={plan.fps},format=rgba[base]"
        )
    ]
    video_label = "base"
    if plate_path:
        from PIL import Image

        with Image.open(plate_path) as image:
            scale = min(
                width * 0.72 / image.width,
                height * 0.46 / image.height,
                1.0,
            )
            plate_width = max(1, round(image.width * scale))
            plate_height = max(1, round(image.height * scale))
        filters.append(
            f"[1:v]scale={plate_width}:{plate_height}:flags=lanczos[plate]"
        )
        plate_margin = max(20, round(height * 0.08))
        if shot.product_plate_motion == "subtle_entrance":
            plate_y = f"H-(h+{plate_margin})*min(t/0.30\\,1)"
            overlay_options = "eval=frame:format=auto"
        else:
            plate_y = f"H-h-{plate_margin}"
            overlay_options = "format=auto"
        filters.append(
            f"[base][plate]overlay=(W-w)/2:{plate_y}:"
            f"{overlay_options}[withplate]"
        )
        video_label = "withplate"
    if shot.caption:
        _write_ass(subtitle, shot.caption, plan, shot.duration_seconds)
        filters.append(
            f"[{video_label}]ass='{_filter_path(subtitle)}'[outv]"
        )
        video_label = "outv"
        command_summary.append("render deterministic ASS subtitle")

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            f"[{video_label}]",
            "-map",
            f"{audio_index}:a",
            "-t",
            str(shot.duration_seconds),
            "-r",
            str(plan.fps),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output),
        ]
    )
    try:
        _run(command)
        probe = probe_media(output)
        video = _video_stream(probe)
        audio = _audio_stream(probe)
        if (
            int(video.get("width") or 0) != width
            or int(video.get("height") or 0) != height
            or video.get("codec_name") != "h264"
            or video.get("pix_fmt") != "yuv420p"
            or audio.get("codec_name") != "aac"
        ):
            raise RuntimeError("rendered shot failed codec or canvas verification")
        duration = float((probe.get("format") or {}).get("duration") or 0)
        artifact = MediaShotResultArtifact(
            artifact_id=artifact_id,
            task_id=plan.task_id,
            product_id=product_root.name,
            created_at=now_iso(),
            source_refs=[
                plan.artifact_id,
                *(
                    [product_plate.artifact_id]
                    if product_plate and shot.product_plate_required
                    else []
                ),
            ],
            status="READY",
            plan_id=plan.artifact_id,
            shot_id=shot.shot_id,
            attempt=attempt,
            execution_status="COMPLETED",
            provider="local-compositor",
            external_call_performed=False,
            input_hashes=input_hashes,
            source_relative_path=str(source.relative_to(product_root)),
            output_relative_path=str(output.relative_to(product_root)),
            output_content_hash=_sha256(output),
            duration_seconds=duration,
            command_summary=command_summary,
        )
    except Exception as exc:
        artifact = MediaShotResultArtifact(
            artifact_id=artifact_id,
            task_id=plan.task_id,
            product_id=product_root.name,
            created_at=now_iso(),
            source_refs=[plan.artifact_id],
            status="BLOCKED",
            plan_id=plan.artifact_id,
            shot_id=shot.shot_id,
            attempt=attempt,
            execution_status=(
                "FAILED_RETRYABLE"
                if attempt < shot.max_attempts
                else "FAILED_FINAL"
            ),
            provider="local-compositor",
            external_call_performed=False,
            input_hashes=input_hashes,
            source_relative_path=str(source.relative_to(product_root)),
            error_code="media_render_failed",
            error_detail=f"{type(exc).__name__}: {exc}"[:2000],
            command_summary=command_summary,
        )
    save_professional_artifact(artifact)
    return artifact


def compose_final_video(
    product_id: str,
    *,
    plan: MediaExecutionPlanArtifact,
    shot_results: list[MediaShotResultArtifact],
) -> MediaCompositeManifestArtifact:
    """Concatenate exactly one completed result per planned shot."""

    product_root = ensure_product(product_id)
    ffmpeg = resolve_media_tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for final composition")
    by_shot = {
        result.shot_id: result
        for result in shot_results
        if result.execution_status == "COMPLETED"
    }
    expected = [shot.shot_id for shot in plan.shots]
    if set(by_shot) != set(expected):
        raise ValueError("final composition requires one completed result per planned shot")
    ordered = [by_shot[shot_id] for shot_id in expected]
    paths = [
        _workspace_path(
            product_root,
            product_root / result.output_relative_path,
        )
        for result in ordered
    ]
    output_dir = product_root / "artifacts" / "generated_videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    concat_path = output_dir / f"concat-{plan.artifact_id}.txt"
    concat_path.write_text(
        "".join(
            f"file '{str(path).replace(chr(92), '/').replace(chr(39), chr(39) * 2)}'\n"
            for path in paths
        ),
        encoding="utf-8",
    )
    output = output_dir / f"reliable-{plan.artifact_id}.mp4"
    _run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    probe = probe_media(output)
    video = _video_stream(probe)
    audio = _audio_stream(probe)
    duration = float((probe.get("format") or {}).get("duration") or 0)
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise RuntimeError("final video failed codec verification")
    output_content_hash = _sha256(output)
    task_token = hashlib.sha256(plan.task_id.encode("utf-8")).hexdigest()[:10]
    manifest = MediaCompositeManifestArtifact(
        artifact_id=(
            f"media-composite-{task_token}-{output_content_hash[:12]}"
        ),
        task_id=plan.task_id,
        product_id=product_root.name,
        created_at=now_iso(),
        source_refs=[plan.artifact_id, *(result.artifact_id for result in ordered)],
        status="READY",
        plan_id=plan.artifact_id,
        shot_result_ids=[result.artifact_id for result in ordered],
        output_relative_path=str(output.relative_to(product_root)),
        output_content_hash=output_content_hash,
        duration_seconds=duration,
        codec=str(video.get("codec_name") or ""),
        audio_codec=str(audio.get("codec_name") or ""),
        subtitle_mode="deterministic_ass",
        command_summary=[
            "concat shots in Media Execution Plan order",
            "copy normalized H.264/AAC streams",
            "write faststart MP4",
        ],
    )
    save_professional_artifact(manifest)
    return manifest
