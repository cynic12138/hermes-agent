"""Provider artifact download helpers for Product Creative runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict


def _require_real_provider_enabled() -> None:
    if os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") != "1":
        raise PermissionError("Remote provider artifact download is disabled until explicitly enabled.")


def _video_extension(content_type: str, url: str) -> str:
    clean_type = content_type.split(";")[0].strip().lower()
    mapping = {
        "video/mp4": ".mp4",
        "video/mpeg": ".mpeg",
        "video/quicktime": ".mov",
        "application/octet-stream": ".mp4",
    }
    if clean_type in mapping:
        return mapping[clean_type]
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in {".mp4", ".mov", ".mpeg", ".webm"}:
        return suffix
    return ".mp4"


def _image_extension(content_type: str, url: str) -> str:
    clean_type = content_type.split(";")[0].strip().lower()
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    if clean_type in mapping:
        return mapping[clean_type]
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".png"


def download_video_asset(url: str, out_dir: Path, name: str) -> Dict[str, str]:
    _require_real_provider_enabled()
    request = urllib.request.Request(url, headers={"User-Agent": "product-creative-m5"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.URLError as exc:
        return _download_video_with_curl(url, out_dir, name, f"video download failed: {exc.reason}")
    extension = _video_extension(content_type, url)
    path = out_dir / f"{name}{extension}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "path": str(path),
        "mime_type": content_type.split(";")[0].strip() or "video/mp4",
        "bytes": str(len(data)),
    }


def _download_video_with_curl(url: str, out_dir: Path, name: str, original_error: str) -> Dict[str, str]:
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise RuntimeError(original_error)
    extension = _video_extension("", url)
    path = out_dir / f"{name}{extension}"
    path.parent.mkdir(parents=True, exist_ok=True)
    args = [curl, "-L", "--fail", "--silent", "--show-error", "--retry", "2", "--output", str(path), url]
    if os.name == "nt":
        args.insert(3, "--ssl-no-revoke")
    completed = subprocess.run(args, capture_output=True, text=True, timeout=300)
    if completed.returncode != 0:
        if path.exists():
            path.unlink()
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"{original_error}; curl fallback failed: {detail}")
    return {
        "path": str(path),
        "mime_type": "video/mp4",
        "bytes": str(path.stat().st_size),
    }


def download_image_asset(url: str, out_dir: Path, name: str) -> Dict[str, str]:
    _require_real_provider_enabled()
    request = urllib.request.Request(url, headers={"User-Agent": "product-creative-m0.6"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"image download failed: {exc.reason}") from exc
    extension = _image_extension(content_type, url)
    path = out_dir / f"{name}{extension}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "path": str(path),
        "mime_type": content_type.split(";")[0].strip() or "image/png",
        "bytes": str(len(data)),
    }
