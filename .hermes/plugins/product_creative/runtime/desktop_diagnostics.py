"""Read-only diagnostics for the Product Creative Desktop pilot."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict

from ..common import now_iso
from ..provider_registry import env_value
from .media_dependencies import resolve_media_tool


_SIDECARS = {
    "xhs": "http://127.0.0.1:8787/api/health",
    "douyin": "http://127.0.0.1:8000/api/health",
}


def _configured(name: str) -> bool:
    return bool(env_value(name).strip())


def _check(
    check_id: str,
    category: str,
    label: str,
    status: str,
    detail: str,
    *,
    required: bool,
    action: str = "",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "id": check_id,
        "category": category,
        "label": label,
        "status": status,
        "required": required,
        "detail": detail,
        "action": action,
        "metadata": metadata or {},
    }


def _credential_check(
    check_id: str,
    label: str,
    env_name: str,
    *,
    required: bool,
    capabilities: list[str],
) -> Dict[str, Any]:
    configured = _configured(env_name)
    status = "READY" if configured else "ACTION_REQUIRED" if required else "OPTIONAL_OFFLINE"
    return _check(
        check_id,
        "model_credentials",
        label,
        status,
        (
            f"{env_name} is configured."
            if configured
            else f"Configure {env_name} before using these capabilities."
        ),
        required=required,
        action="open_hermes_settings" if not configured else "",
        metadata={
            "configured": configured,
            "environment_variable": env_name,
            "capabilities": capabilities,
        },
    )


def _default_probe_sidecar(_name: str, url: str) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=0.75) as response:
            raw = response.read(16_384).decode("utf-8", errors="replace")
    except (OSError, TimeoutError, urllib.error.URLError, urllib.error.HTTPError):
        return {"available": False, "detail": "Local sidecar is not running."}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"available": False, "detail": "Local sidecar returned an invalid health response."}
    if not isinstance(payload, dict):
        return {"available": False, "detail": "Local sidecar returned an invalid health response."}
    return {"available": True, "detail": "Local sidecar health endpoint is available."}


def _tool_check(name: str, value: str) -> Dict[str, Any]:
    available = bool(value)
    return _check(
        f"media-{name}",
        "media_runtime",
        name,
        "READY" if available else "ACTION_REQUIRED",
        (
            f"{name} is available for deterministic media processing."
            if available
            else f"{name} is required for local media production."
        ),
        required=True,
        action="install_media_dependency" if not available else "",
        metadata={
            "available": available,
            "executable": Path(value).name if value else "",
        },
    )


def collect_desktop_diagnostics(
    *,
    resolve_tool: Callable[[str], str] = resolve_media_tool,
    probe_sidecar: Callable[[str, str], Dict[str, Any]] = _default_probe_sidecar,
) -> Dict[str, Any]:
    """Return a redacted readiness report without invoking external providers."""

    checks: list[Dict[str, Any]] = [
        _check(
            "plugin-runtime",
            "runtime",
            "Product Creative plugin",
            "READY",
            "The authenticated Desktop plugin API is available.",
            required=True,
            metadata={"desktop_api_version": 1},
        ),
        _credential_check(
            "credential-doubao",
            "Doubao / Volcengine Ark",
            "DOUBAO_API_KEY",
            required=True,
            capabilities=["image", "image_analysis", "video"],
        ),
        _credential_check(
            "credential-deepseek",
            "DeepSeek hook analysis",
            "DEEPSEEK_API_KEY",
            required=False,
            capabilities=["douyin_hook_analysis"],
        ),
        _credential_check(
            "credential-siliconflow",
            "SiliconFlow transcription",
            "SILICONFLOW_API_KEY",
            required=False,
            capabilities=["douyin_transcription"],
        ),
    ]

    live_enabled = os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", "").strip() == "1"
    checks.append(
        _check(
            "real-provider-opt-in",
            "provider_runtime",
            "Real provider execution",
            "READY" if live_enabled else "ACTION_REQUIRED",
            (
                "Real provider execution is explicitly enabled."
                if live_enabled
                else "Real provider execution is disabled until explicitly enabled."
            ),
            required=True,
            action="enable_real_provider" if not live_enabled else "",
            metadata={"enabled": live_enabled},
        )
    )
    checks.extend(
        [
            _tool_check("ffmpeg", resolve_tool("ffmpeg")),
            _tool_check("ffprobe", resolve_tool("ffprobe")),
        ]
    )

    for name, url in _SIDECARS.items():
        result = probe_sidecar(name, url)
        available = bool(result.get("available"))
        checks.append(
            _check(
                f"sidecar-{name}",
                "optional_sources",
                "Xiaohongshu" if name == "xhs" else "Douyin",
                "READY" if available else "OPTIONAL_OFFLINE",
                str(result.get("detail") or "Local sidecar is not running."),
                required=False,
                action=f"start_{name}_sidecar" if not available else "",
                metadata={
                    "available": available,
                    "optional": True,
                    "endpoint_scope": "loopback",
                },
            )
        )

    blocking = [
        item
        for item in checks
        if item["required"] and item["status"] in {"ACTION_REQUIRED", "BLOCKED"}
    ]
    degraded = [
        item for item in checks if item["required"] and item["status"] == "DEGRADED"
    ]
    return {
        "schema_name": "product_creative.desktop_diagnostics.v1",
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "overall_status": (
            "ACTION_REQUIRED" if blocking else "DEGRADED" if degraded else "READY"
        ),
        "checks": checks,
        "safety": {
            "external_provider_called": False,
            "secret_values_returned": False,
            "sidecars_are_optional": True,
        },
    }


__all__ = ["collect_desktop_diagnostics"]
