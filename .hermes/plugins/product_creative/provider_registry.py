"""Provider registry and environment resolution for Product Creative."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from .common import read_json


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def registry_path() -> Path:
    return Path(__file__).with_name("provider_registry.json")


def load_registry() -> Dict[str, Any]:
    registry = read_json(registry_path(), {})
    providers = registry.get("providers")
    if not isinstance(providers, list):
        return {"schema_version": "product_creative.provider_registry.v0.5.1", "providers": []}
    return registry


def provider_entry(provider: str) -> Dict[str, Any]:
    name = provider or "generic"
    for item in load_registry().get("providers", []):
        if item.get("name") == name:
            return item
    raise ValueError(f"provider '{name}' is not registered")


def env_value(key: str) -> str:
    value = os.environ.get(key)
    if value:
        return value
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
            stored, _ = winreg.QueryValueEx(env_key, key)
            return str(stored)
    except Exception:
        return ""


def list_providers(kind: str | None = None) -> Dict[str, Any]:
    registry = load_registry()
    providers = []
    for item in registry.get("providers", []):
        supported = _list(item.get("supported_types"))
        if kind and kind not in supported:
            continue
        providers.append(item)
    return {
        "success": True,
        "schema_version": registry.get("schema_version", ""),
        "kind": kind or "",
        "count": len(providers),
        "providers": providers,
    }
