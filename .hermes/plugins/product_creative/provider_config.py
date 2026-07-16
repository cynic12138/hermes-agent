"""Provider runtime configuration resolution for Product Creative."""

from __future__ import annotations

from typing import Any, Dict

from .provider_registry import env_value as _env_value


__all__ = ["provider_api_key", "provider_endpoint", "provider_model"]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def provider_endpoint(provider: Dict[str, Any]) -> str:
    endpoint = _text(provider.get("endpoint"))
    if endpoint:
        return endpoint
    endpoint_env = _text(provider.get("endpoint_env"))
    if endpoint_env:
        return _env_value(endpoint_env)
    return ""


def provider_model(provider: Dict[str, Any]) -> str:
    model = _text(provider.get("model"))
    if model:
        return model
    model_env = _text(provider.get("model_env"))
    if model_env:
        return _env_value(model_env)
    return ""


def provider_api_key(provider: Dict[str, Any]) -> str:
    auth_envs = [_text(provider.get("auth_env"))]
    fallbacks = provider.get("auth_env_fallbacks")
    if isinstance(fallbacks, list):
        auth_envs.extend(_text(item) for item in fallbacks)
    for auth_env in auth_envs:
        if not auth_env:
            continue
        value = _env_value(auth_env)
        if value:
            return value
    return ""


