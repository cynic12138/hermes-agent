"""CLI dispatch adapter for Product Creative commands."""

from __future__ import annotations

import argparse
from typing import Any, Callable, Dict

from .common import json_text
from .runtime.errors import classify_exception, error_result, record_runtime_error


CliHandler = Callable[[argparse.Namespace], Dict[str, Any]]
ResultPrinter = Callable[[Dict[str, Any]], int]


def usage_text(command_names: list[str]) -> str:
    return f"usage: hermes product {{{','.join(command_names)}}}"


def dispatch_product_command(
    args: argparse.Namespace,
    handlers: Dict[str, CliHandler],
    print_result: ResultPrinter,
) -> int:
    command = getattr(args, "product_command", None)
    handler = handlers.get(str(command or ""))
    if handler is None:
        print(usage_text(list(handlers)))
        return 2
    try:
        return print_result(handler(args))
    except Exception as exc:
        error = classify_exception(
            exc,
            "cli_adapter",
            str(getattr(args, "product_id", "") or ""),
            str(command or ""),
        )
        error["diagnostic_path"] = record_runtime_error(error)
        print(json_text(error_result(error) | {"diagnostic_path": error["diagnostic_path"]}))
        return 1
