"""HTTP transport helpers for Product Creative provider adapters."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict


def _require_real_provider_enabled() -> None:
    if os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") != "1":
        raise PermissionError("Real provider HTTP execution is disabled until explicitly enabled.")


def post_json(endpoint: str, body: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    _require_real_provider_enabled()
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"provider HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"provider request failed: {exc.reason}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"provider returned non-JSON response: {raw[:500]}") from exc


def get_json(endpoint: str, api_key: str) -> Dict[str, Any]:
    _require_real_provider_enabled()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"provider HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"provider request failed: {exc.reason}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"provider returned non-JSON response: {raw[:500]}") from exc
