"""Small helpers shared by capability-owned argument binders."""

from __future__ import annotations

from typing import Any, Dict


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def set_text(args: Dict[str, Any], key: str, value: Any) -> None:
    clean = text(value)
    if clean:
        args[key] = clean


def bind_fields(context: Dict[str, Any], mapping: Dict[str, str]) -> bool:
    args = context["args"]
    for source, target in mapping.items():
        set_text(args, target, context.get(source))
    return True


def feedback(context: Dict[str, Any], *, variant: bool = False, rejected: bool = False) -> bool:
    args = context["args"]
    message = text(context.get("message"))
    if not message:
        return True
    args["note"] = message
    for key in ("rating", "selected", "allow_evolve"):
        value = context.get(key)
        if value is not None and value is not False:
            args[key] = value
    if variant and context.get("variant") is not None:
        args["variant"] = context["variant"]
    if rejected and context.get("rejected"):
        args["rejected"] = True
    context["remove_missing_input"]("note")
    return True
