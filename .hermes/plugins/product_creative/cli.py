"""Schema-driven CLI adapter for Product Creative commands."""

from __future__ import annotations

import argparse
from typing import Any, Callable, Dict

from .capabilities.registry import command_descriptors
from .cli_dispatch import dispatch_product_command
from .common import json_text
from .tools import invoke_product_tool


CLI_COMMAND_NAMES = (
    "create", "ingest", "workspace-resolve", "target-list", "generate", "evaluate",
    "channel-evaluate", "channel-review-package", "channel-review-run", "brief",
    "image-generate", "image-intent", "image-brief", "image-brief-review",
    "image-brief-revise", "batch-policy", "image-provider-payload", "image-run",
    "selected-image-asset", "video-generate", "provider-list", "provider-validate",
    "generation-job", "artifact-manifest", "review-package", "result-feedback",
    "result-review-package", "result-evaluate", "task-overview-package", "exact-main-video",
    "channel-feedback", "video-brief-feedback", "live-readiness",
    "video-reference-readiness", "video-execution-policy", "video-task-status",
    "video-result-import", "wiki-upgrade", "wiki-lint", "state-export", "fingerprint",
    "creative-run", "image-qa", "comparison-package", "feedback", "evolve", "context",
    "workflow-status", "workflow-next", "workflow-summary", "action-guard", "workflow-plan",
    "conversation-adapter", "workflow-execute", "workflow-run", "asset-register",
    "asset-bind-url", "asset-list", "provider-capability", "material-resolve",
    "external-source", "inspiration-candidates", "inspiration-pack", "llm-inspiration-pack",
    "inspiration-library-confirm", "material-manifest", "material-compat",
    "material-card-rebuild", "material-library-map", "task-material-pack", "material-usage",
    "material-feedback", "image-analyze", "visual-align", "video-intent", "video-brief",
    "video-brief-review", "video-brief-revise",
)

CLI_TOOL_OVERRIDES = {
    "image-brief-review": "product_image_brief_review_package",
    "batch-policy": "product_batch_generation_policy",
    "image-run": "product_image_generation_run",
    "feedback": "product_feedback_record",
    "context": "product_context_pack",
    "provider-capability": "product_provider_capability_matrix",
    "external-source": "product_external_source_collect",
    "video-brief-review": "product_video_brief_review_package",
}

_FLAG_ALIASES = {
    "product_id": "id",
    "artifact_id": "artifact",
    "evaluation_id": "evaluation",
    "brief_id": "brief",
    "intent_id": "intent",
    "patch_id": "patch",
    "batch_policy_id": "batch-policy",
    "payload_id": "payload",
    "result_id": "result",
    "task_id": "task",
    "material_id": "material",
    "analysis_id": "analysis",
    "execution_policy_id": "execution-policy",
    "snapshot_ids": "snapshot",
    "images": "image",
    "assets": "asset",
    "issues": "issue",
    "like_reasons": "like-reason",
    "dislike_reasons": "dislike-reason",
}


def _tool_name(command: str) -> str:
    return CLI_TOOL_OVERRIDES.get(command, f"product_{command.replace('-', '_')}")


def _argument_type(schema: Dict[str, Any]):
    return {"integer": int, "number": float, "string": str}.get(schema.get("type"), str)


def _add_schema_argument(parser: argparse.ArgumentParser, name: str, schema: Dict[str, Any], required: bool) -> None:
    flag_name = _FLAG_ALIASES.get(name, name.replace("_", "-"))
    kwargs: Dict[str, Any] = {"dest": name, "required": required}
    description = schema.get("description")
    if description:
        kwargs["help"] = description
    if schema.get("type") == "boolean":
        kwargs.pop("required", None)
        default = bool(schema.get("default", False))
        kwargs["action"] = "store_false" if default else "store_true"
        kwargs["default"] = default
        option = f"--no-{flag_name}" if default else f"--{flag_name}"
        parser.add_argument(option, **kwargs)
        return
    if schema.get("type") == "array":
        kwargs["action"] = "append"
        kwargs["default"] = list(schema.get("default") or [])
        kwargs["type"] = _argument_type(schema.get("items") or {})
        if (schema.get("items") or {}).get("enum"):
            kwargs["choices"] = list(schema["items"]["enum"])
    else:
        kwargs["type"] = _argument_type(schema)
        if "default" in schema:
            kwargs["default"] = schema["default"]
        if schema.get("enum"):
            kwargs["choices"] = list(schema["enum"])
    parser.add_argument(f"--{flag_name}", **kwargs)


def register_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="product_command")
    descriptors = command_descriptors()
    for command in CLI_COMMAND_NAMES:
        descriptor = descriptors[_tool_name(command)]
        schema = descriptor.schema
        parser = subs.add_parser(command, help=str(schema.get("description") or ""))
        parameters = schema.get("parameters") or {}
        required = set(parameters.get("required") or [])
        for name, property_schema in (parameters.get("properties") or {}).items():
            _add_schema_argument(parser, name, property_schema, name in required)
    subparser.set_defaults(func=product_command)


def _print_result(result: Dict[str, Any]) -> int:
    print(json_text(result))
    return 0 if result.get("success") else 1


def _cli_tool_handler(tool_name: str) -> Callable[[argparse.Namespace], Dict[str, Any]]:
    def invoke(args: argparse.Namespace) -> Dict[str, Any]:
        return invoke_product_tool(tool_name, dict(vars(args)))

    return invoke


CLI_COMMAND_HANDLERS = {
    command: _cli_tool_handler(_tool_name(command))
    for command in CLI_COMMAND_NAMES
}


def product_command(args: argparse.Namespace) -> int:
    return dispatch_product_command(args, CLI_COMMAND_HANDLERS, _print_result)
