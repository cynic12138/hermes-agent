"""Small coercion helpers for action adapters."""

from __future__ import annotations

from typing import Any, List


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def items(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def quality_scores(args: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: args.get(field) for field in fields}
