"""Channel-content capability executor."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .run_service import create_channel_review_run
from ..execution_helpers import text
from ..models import ActionRuntimeDefinition


def _run_channel_review(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_channel_review_run(
        text(args.get("product_id")),
        text(args.get("target")),
        int(args.get("variants") or 3),
        args.get("creative_brief") if isinstance(args.get("creative_brief"), dict) else None,
    )


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (ActionRuntimeDefinition("run_channel_review", _run_channel_review),)


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
