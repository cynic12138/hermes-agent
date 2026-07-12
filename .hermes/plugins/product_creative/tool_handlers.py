"""Compatibility surface for capability-owned Hermes command adapters."""

from __future__ import annotations

import json
from typing import Any, Dict

from .capabilities.registry import command_descriptors
from .common import TOOLSET


def product_tool_handlers() -> Dict[str, Any]:
    return {name: descriptor.handler for name, descriptor in command_descriptors().items()}


def invoke_product_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    handler = product_tool_handlers().get(name)
    if handler is None:
        raise KeyError(f"unknown Product Creative tool '{name}'")
    payload = json.loads(handler(dict(args)))
    if not isinstance(payload, dict):
        raise TypeError(f"Product Creative tool '{name}' returned a non-object payload")
    return payload


def register_tools(ctx) -> None:
    for descriptor in command_descriptors().values():
        ctx.register_tool(
            name=descriptor.name,
            toolset=TOOLSET,
            schema=descriptor.schema,
            handler=descriptor.handler,
            check_fn=lambda: True,
            emoji="",
        )
