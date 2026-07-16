"""External inspiration action adapters."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .api import (
    collect_external_source_snapshot,
    confirm_llm_inspiration_pack,
    create_inspiration_candidates,
    create_inspiration_pack,
    create_llm_inspiration_pack,
)
from ..models import ActionRuntimeDefinition
from ..execution_helpers import items, text


def _collect(args: Dict[str, Any]) -> Dict[str, Any]:
    return collect_external_source_snapshot(
        text(args.get("product_id")),
        text(args.get("provider")) or "manual",
        text(args.get("query")),
        text(args.get("channel")),
        text(args.get("mode")) or "dry_run",
        int(args.get("limit") or 3),
        text(args.get("import_path")),
        text(args.get("text")),
        text(args.get("url")),
        text(args.get("sidecar_url")),
        int(args.get("wait_seconds") or 90),
        int(args.get("transcribe_limit") or 1),
        bool(args.get("auto_browser_cookie")),
        int(args.get("analyze_first5_limit") or 1),
    )


def _candidates(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_inspiration_candidates(
        text(args.get("product_id")),
        text(args.get("snapshot")),
        text(args.get("goal")),
        int(args.get("max_candidates") or 5),
    )


def _pack(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_inspiration_pack(
        text(args.get("product_id")),
        items(args.get("candidates")),
        text(args.get("goal")),
        text(args.get("target")),
        int(args.get("limit") or 3),
    )


def _llm_pack(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_llm_inspiration_pack(
        text(args.get("product_id")),
        items(args.get("snapshots")),
        text(args.get("goal")),
        text(args.get("target")),
        text(args.get("channel")),
        int(args.get("max_items") or 8),
        text(args.get("provider")),
        text(args.get("model")),
    )


def _confirm(args: Dict[str, Any]) -> Dict[str, Any]:
    return confirm_llm_inspiration_pack(
        text(args.get("product_id")),
        text(args.get("pack")),
        text(args.get("note")),
        bool(args.get("confirmed")),
    )


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("collect_external_source_snapshot", _collect),
        ActionRuntimeDefinition("create_inspiration_candidates", _candidates, auto_advance=True),
        ActionRuntimeDefinition("create_inspiration_pack", _pack, auto_advance=True),
        ActionRuntimeDefinition("create_llm_inspiration_pack", _llm_pack),
        ActionRuntimeDefinition("confirm_inspiration_library_entry", _confirm, idempotency_fields=("pack",)),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
