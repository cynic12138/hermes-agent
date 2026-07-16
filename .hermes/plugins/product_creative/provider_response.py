"""Provider response traversal helpers for Product Creative."""

from __future__ import annotations

from typing import Any, List
from urllib.parse import urlsplit, urlunsplit


__all__ = ["find_first_key", "find_urls", "redact_url_credentials", "sanitize_urls"]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def find_urls(value: Any) -> List[str]:
    urls: List[str] = []
    if isinstance(value, str):
        if value.startswith("http://") or value.startswith("https://"):
            urls.append(value)
        return urls
    if isinstance(value, list):
        for item in value:
            urls.extend(find_urls(item))
        return urls
    if isinstance(value, dict):
        for key in ["url", "image_url", "result_url", "download_url"]:
            urls.extend(find_urls(value.get(key)))
        for key, item in value.items():
            if key not in {"url", "image_url", "result_url", "download_url"}:
                urls.extend(find_urls(item))
        return urls
    return urls


def find_first_key(value: Any, keys: set[str]) -> str:
    if isinstance(value, dict):
        for key in keys:
            found = _text(value.get(key))
            if found:
                return found
        for item in value.values():
            found = find_first_key(item, keys)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_first_key(item, keys)
            if found:
                return found
    return ""


def redact_url_credentials(value: Any) -> str:
    """Remove transient query credentials before persisting provider URLs."""

    url = _text(value)
    if not (url.startswith("http://") or url.startswith("https://")):
        return url
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def sanitize_urls(value: Any) -> Any:
    """Copy a provider response while redacting query credentials from URLs."""

    if isinstance(value, str):
        return redact_url_credentials(value)
    if isinstance(value, list):
        return [sanitize_urls(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_urls(item) for key, item in value.items()}
    return value
