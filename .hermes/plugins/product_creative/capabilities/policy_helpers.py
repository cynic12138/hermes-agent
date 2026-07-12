"""Shared result helpers for capability-owned guard policies."""
from __future__ import annotations
from typing import Any, Dict


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def allow(result: Dict[str, Any], reason: str) -> Dict[str, Any]:
    result.update({"allowed": True, "reason": reason})
    return result


def block(result: Dict[str, Any], reason: str) -> Dict[str, Any]:
    result.update({"allowed": False, "reason": reason})
    return result
