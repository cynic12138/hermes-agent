"""Stable Hermes tool facade for Product Creative."""

from __future__ import annotations

from .application.command_bus import command_bus
from .tool_handlers import product_tool_handlers, register_tools


def invoke_product_tool(name, args):
    return command_bus().invoke(name, args)

__all__ = ["invoke_product_tool", "product_tool_handlers", "register_tools"]
