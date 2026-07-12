"""Workspace, channel-content, and Product Brain action adapters."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .api import create_product, ingest_product
from ..models import ActionRuntimeDefinition
from ..execution_helpers import items, text


def _create_product(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_product(text(args.get("product_id")), text(args.get("name")))


def _ingest_product(args: Dict[str, Any]) -> Dict[str, Any]:
    return ingest_product(text(args.get("product_id")), args.get("text"), items(args.get("images")))


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("create_product", _create_product),
        ActionRuntimeDefinition("ingest_product_source", _ingest_product),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
