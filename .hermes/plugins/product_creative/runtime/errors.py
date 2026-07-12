"""Structured Product Creative runtime errors and diagnostics."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict

from ..common import append_jsonl, now_iso, product_dir
from ..ports.errors import StoreCorruptionError


def _safe_message(value: Any) -> str:
    text = str(value or "")[:1200]
    text = re.sub(r"(?i)(authorization|api[-_ ]?key|token)\s*[:=]\s*[^\s,;]+", r"\1=<redacted>", text)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._-]+", "Bearer <redacted>", text)
    return text


def classify_exception(
    exc: Exception,
    stage: str,
    product_id: str = "",
    action: str = "",
    trace_id: str = "",
) -> Dict[str, Any]:
    if isinstance(exc, StoreCorruptionError):
        code, retryable = "STORE_CORRUPTION", False
    elif isinstance(exc, FileNotFoundError):
        code, retryable = "NOT_FOUND", False
    elif isinstance(exc, (ValueError, TypeError, KeyError)):
        code, retryable = "VALIDATION_ERROR", False
    elif isinstance(exc, TimeoutError):
        code, retryable = "TIMEOUT", True
    elif isinstance(exc, OSError):
        code, retryable = "IO_ERROR", True
    else:
        code, retryable = "INTERNAL_ERROR", False
    return {
        "error_id": f"error-{uuid.uuid4().hex}",
        "trace_id": trace_id or f"trace-{uuid.uuid4().hex}",
        "product_id": product_id,
        "action": action,
        "stage": stage,
        "error_code": code,
        "error_type": type(exc).__name__,
        "error_message": _safe_message(exc),
        "retryable": retryable,
        "created_at": now_iso(),
    }


def record_runtime_error(error: Dict[str, Any]) -> str:
    product_id = str(error.get("product_id") or "")
    path: Path
    if product_id:
        base = product_dir(product_id)
        if base.exists():
            path = base / "structured" / "runtime_errors.jsonl"
        else:
            path = Path.cwd() / ".hermes" / "product_creative" / "runtime_errors.jsonl"
    else:
        path = Path.cwd() / ".hermes" / "product_creative" / "runtime_errors.jsonl"
    append_jsonl(path, error)
    return str(path)


def error_result(error: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": False,
        "error_id": error.get("error_id"),
        "trace_id": error.get("trace_id"),
        "error_code": error.get("error_code"),
        "error": error.get("error_message"),
        "stage": error.get("stage"),
        "retryable": error.get("retryable"),
    }
