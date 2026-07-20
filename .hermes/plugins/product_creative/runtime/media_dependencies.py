"""Preflight diagnostics for reliable local media production."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..common import ensure_product, now_iso
from ..contracts.creative_artifacts import (
    MediaDependencyCheck,
    MediaDependencyReportArtifact,
    ProductionBibleArtifact,
)
from ..ports.runtime_repositories import materials
from ..provider_registry import load_registry
from .professional_artifacts import (
    load_professional_artifact,
    save_professional_artifact,
)


_CHINESE_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
)


def _common_media_tool_candidates(name: str) -> tuple[Path, ...]:
    """Return bounded, already-installed Windows media-tool candidates."""

    if name not in {"ffmpeg", "ffprobe"}:
        return ()
    roots = tuple(
        Path(value)
        for key in ("ProgramFiles", "ProgramFiles(x86)")
        if (value := os.environ.get(key, "").strip())
    )
    relative_paths = (
        Path("AIMIXMaster")
        / "resources"
        / "app.asar.unpacked"
        / "node_modules"
        / "ffmpeg-static-all"
        / "win"
        / "bin"
        / f"{name}.exe",
    )
    candidates: list[Path] = []
    for root in roots:
        for relative in relative_paths:
            candidate = root / relative
            if candidate.is_file() and candidate not in candidates:
                candidates.append(candidate)
    return tuple(candidates)


def _media_tool_candidates(name: str) -> tuple[str, ...]:
    env_key = {
        "ffmpeg": "PRODUCT_CREATIVE_FFMPEG_PATH",
        "ffprobe": "PRODUCT_CREATIVE_FFPROBE_PATH",
    }.get(name, "")
    values: list[str] = []
    configured = os.environ.get(env_key, "").strip() if env_key else ""
    if configured and Path(configured).is_file():
        values.append(str(Path(configured)))
    discovered = str(shutil.which(name) or "")
    if discovered and discovered not in values:
        values.append(discovered)
    for candidate in _common_media_tool_candidates(name):
        value = str(candidate)
        if value not in values:
            values.append(value)
    return tuple(values)


def resolve_media_tool(name: str) -> str:
    """Resolve the first candidate that identifies itself as the requested tool."""

    if name not in {"ffmpeg", "ffprobe"}:
        return str(shutil.which(name) or "")
    expected_prefix = f"{name} version"
    for candidate in _media_tool_candidates(name):
        ok, output = _tool_output([candidate, "-version"])
        if ok and _first_line(output).lower().startswith(expected_prefix):
            return candidate
    return ""


def _find_chinese_font() -> Path | None:
    return next((path for path in _CHINESE_FONT_CANDIDATES if path.exists()), None)


def _first_line(value: str) -> str:
    return next((line.strip() for line in value.splitlines() if line.strip()), "")


def _tool_output(command: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return result.returncode == 0, output


def _provider_kinds(bible: ProductionBibleArtifact) -> set[str]:
    values = {
        str(value).strip().lower()
        for value in bible.provider_mapping.values()
        if str(value).strip()
    }
    return {kind for kind in ("image", "video") if kind in values}


def _provider_capability_check(
    bible: ProductionBibleArtifact,
) -> MediaDependencyCheck:
    required = _provider_kinds(bible)
    if not required:
        return MediaDependencyCheck(
            name="provider_capability",
            status="READY",
            detail="Production Bible does not require a generative media provider.",
            metadata={"required_types": []},
        )
    available: set[str] = set()
    for provider in load_registry().get("providers", []):
        if not isinstance(provider, dict):
            continue
        available.update(
            str(kind).strip()
            for kind in provider.get("supported_types") or []
            if str(kind).strip()
        )
    missing = sorted(required - available)
    if missing:
        return MediaDependencyCheck(
            name="provider_capability",
            status="BLOCKED",
            detail="Provider registry lacks required media capability: "
            + ", ".join(missing),
            metadata={
                "required_types": sorted(required),
                "available_types": sorted(available),
            },
        )
    return MediaDependencyCheck(
        name="provider_capability",
        status="READY",
        detail="Provider registry contains the required media capabilities.",
        metadata={"required_types": sorted(required)},
    )


def _material_check(product_root: Path, material_id: str) -> MediaDependencyCheck:
    material = materials().get(product_root.name, material_id)
    if not material:
        return MediaDependencyCheck(
            name="material",
            status="BLOCKED",
            detail=f"Material '{material_id}' does not exist in this product workspace.",
            metadata={"material_id": material_id},
        )
    stored_path = str(material.get("stored_path") or "")
    if not stored_path:
        return MediaDependencyCheck(
            name="material",
            status="BLOCKED",
            detail=f"Material '{material_id}' has no stored file path.",
            metadata={"material_id": material_id},
        )
    root = product_root.resolve()
    path = (root / stored_path).resolve()
    if root != path and root not in path.parents:
        return MediaDependencyCheck(
            name="material",
            status="BLOCKED",
            detail=f"Material '{material_id}' resolves outside the product workspace.",
            metadata={"material_id": material_id},
        )
    if not path.is_file():
        return MediaDependencyCheck(
            name="material",
            status="BLOCKED",
            detail=f"Material '{material_id}' file is missing.",
            metadata={"material_id": material_id},
        )
    return MediaDependencyCheck(
        name="material",
        status="READY",
        detail="Selected product material exists inside the current workspace.",
        metadata={
            "material_id": material_id,
            "role": str(material.get("role") or ""),
        },
    )


def inspect_media_dependencies(
    product_id: str,
    *,
    task_id: str,
    material_id: str,
    production_bible_id: str,
    required_free_bytes: int = 268_435_456,
) -> MediaDependencyReportArtifact:
    """Inspect local production dependencies without generating media or using network."""

    product_root = ensure_product(product_id)
    checks: list[MediaDependencyCheck] = []

    ffmpeg = resolve_media_tool("ffmpeg")
    ffprobe = resolve_media_tool("ffprobe")
    checks.append(
        MediaDependencyCheck(
            name="ffmpeg",
            status="READY" if ffmpeg else "BLOCKED",
            detail=(
                "ffmpeg executable is available."
                if ffmpeg
                else "ffmpeg is not available."
            ),
            metadata={"available": bool(ffmpeg)},
        )
    )
    checks.append(
        MediaDependencyCheck(
            name="ffprobe",
            status="READY" if ffprobe else "BLOCKED",
            detail=(
                "ffprobe executable is available."
                if ffprobe
                else "ffprobe is not available."
            ),
            metadata={"available": bool(ffprobe)},
        )
    )

    if ffmpeg and ffprobe:
        ffmpeg_ok, encoder_output = _tool_output(
            [ffmpeg, "-hide_banner", "-encoders"]
        )
        ffprobe_ok, probe_output = _tool_output([ffprobe, "-version"])
        ffprobe_version = _first_line(probe_output)
        ffprobe_identified = (
            ffprobe_ok and ffprobe_version.lower().startswith("ffprobe version")
        )
        has_h264 = "libx264" in encoder_output
        has_aac = " aac" in encoder_output.lower()
        codecs_ready = (
            ffmpeg_ok and ffprobe_identified and has_h264 and has_aac
        )
        checks.append(
            MediaDependencyCheck(
                name="video_codecs",
                status="READY" if codecs_ready else "BLOCKED",
                detail=(
                    "libx264 and AAC encoders are available."
                    if codecs_ready
                    else (
                        "ffmpeg must provide libx264 and AAC encoders, and "
                        "ffprobe must identify itself as ffprobe."
                    )
                ),
                metadata={
                    "ffmpeg_version": _first_line(encoder_output),
                    "ffprobe_version": ffprobe_version,
                    "ffprobe_usable": ffprobe_identified,
                    "libx264": has_h264,
                    "aac": has_aac,
                },
            )
        )
    else:
        checks.append(
            MediaDependencyCheck(
                name="video_codecs",
                status="BLOCKED",
                detail="Codec inspection requires both ffmpeg and ffprobe.",
                metadata={
                    "ffprobe_usable": bool(ffprobe),
                    "libx264": False,
                    "aac": False,
                },
            )
        )

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        pillow_ready = False
    else:
        pillow_ready = True
    checks.append(
        MediaDependencyCheck(
            name="pillow",
            status="READY" if pillow_ready else "BLOCKED",
            detail=(
                "Pillow is available for deterministic image composition."
                if pillow_ready
                else "Pillow is required for deterministic image composition."
            ),
            metadata={"available": pillow_ready},
        )
    )

    font = _find_chinese_font()
    checks.append(
        MediaDependencyCheck(
            name="chinese_font",
            status="READY" if font else "BLOCKED",
            detail=(
                "A deterministic Chinese font is available."
                if font
                else "A Chinese font is required for deterministic subtitles."
            ),
            metadata={"font_name": font.name if font else ""},
        )
    )

    free_bytes = shutil.disk_usage(product_root).free
    disk_ready = free_bytes >= required_free_bytes
    checks.append(
        MediaDependencyCheck(
            name="disk_space",
            status="READY" if disk_ready else "BLOCKED",
            detail=(
                "Workspace has sufficient free space for media production."
                if disk_ready
                else "Workspace does not have enough free space for media production."
            ),
            metadata={
                "required_free_bytes": required_free_bytes,
                "available_free_bytes": free_bytes,
            },
        )
    )
    checks.append(_material_check(product_root, material_id))

    try:
        bible = load_professional_artifact(product_root.name, production_bible_id)
    except (FileNotFoundError, ValueError) as exc:
        bible = None
        checks.append(
            MediaDependencyCheck(
                name="production_bible",
                status="BLOCKED",
                detail=f"Production Bible is unavailable or invalid: {exc}",
                metadata={"artifact_id": production_bible_id},
            )
        )
    else:
        if not isinstance(bible, ProductionBibleArtifact):
            checks.append(
                MediaDependencyCheck(
                    name="production_bible",
                    status="BLOCKED",
                    detail="Selected artifact is not a Production Bible.",
                    metadata={"artifact_id": production_bible_id},
                )
            )
            bible = None
        else:
            checks.append(
                MediaDependencyCheck(
                    name="production_bible",
                    status="READY",
                    detail="Production Bible is valid and belongs to this workspace.",
                    metadata={
                        "artifact_id": bible.artifact_id,
                        "shot_count": len(bible.shots),
                    },
                )
            )

    checks.append(
        _provider_capability_check(bible)
        if bible
        else MediaDependencyCheck(
            name="provider_capability",
            status="BLOCKED",
            detail="Provider capability cannot be evaluated without a valid Production Bible.",
            metadata={"required_types": []},
        )
    )

    blockers = [
        check.detail
        for check in checks
        if check.status == "BLOCKED"
    ]
    warnings = [
        check.detail
        for check in checks
        if check.status == "DEGRADED"
    ]
    overall_status = (
        "BLOCKED"
        if blockers
        else "DEGRADED"
        if warnings
        else "READY"
    )
    artifact = MediaDependencyReportArtifact(
        artifact_id=f"media-dependencies-{task_id}",
        task_id=task_id,
        product_id=product_root.name,
        created_at=now_iso(),
        source_refs=[
            f"material:{material_id}",
            f"production-bible:{production_bible_id}",
        ],
        status="BLOCKED" if blockers else "READY",
        overall_status=overall_status,
        checks=checks,
        blockers=blockers,
        warnings=warnings,
    )
    save_professional_artifact(artifact)
    return artifact
