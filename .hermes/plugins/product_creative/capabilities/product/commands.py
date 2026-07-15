"""Capability-owned Hermes command adapters for product."""

from __future__ import annotations
from typing import Any, Dict
from ...common import TOOLSET, json_text
from ...runtime.agent import product_agent_turn
from ...runtime.errors import classify_exception, error_result, record_runtime_error
from .api import (
    build_product_fingerprint,
    context_pack,
    create_product,
    export_product_state_from_wiki,
    ingest_product,
    resolve_product_workspace,
    wiki_lint_product,
    wiki_upgrade_product,
)
from ...workflow import action_guard, conversation_adapter, workflow_execute, workflow_next, workflow_plan, workflow_status, workflow_summary
from ..models import CommandDescriptor
from . import schemas

def _tool_ok(fn, args: Dict[str, Any]) -> str:
    try:
        return json_text(fn(args))
    except Exception as exc:
        error = classify_exception(
            exc,
            "hermes_tool_adapter",
            str(args.get("product_id") or args.get("id") or ""),
            str(args.get("action") or ""),
        )
        error["diagnostic_path"] = record_runtime_error(error)
        return json_text(error_result(error) | {"diagnostic_path": error["diagnostic_path"]})

def _handle_product_create(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: create_product(a.get("product_id") or a.get("id"), a.get("name") or ""), args)

def _handle_product_ingest(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: ingest_product(
            a.get("product_id") or a.get("id"),
            a.get("text"),
            a.get("images") or a.get("image") or [],
        ),
        args,
    )

def _handle_product_context_pack(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: context_pack(a.get("product_id") or a.get("id"), a.get("target") or "product-copy-pack"),
        args,
    )

def _handle_product_workspace_resolve(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: resolve_product_workspace(
            a.get("query") or a.get("product_query") or "",
            bool(a.get("create_if_missing")),
            a.get("suggested_id") or "",
            a.get("name") or "",
            int(a.get("limit") or 10),
        ),
        args,
    )

def _handle_product_workflow_status(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: workflow_status(a.get("product_id") or a.get("id")), args)

def _handle_product_workflow_next(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: workflow_next(a.get("product_id") or a.get("id")), args)

def _handle_product_workflow_summary(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: workflow_summary(a.get("product_id") or a.get("id")), args)

def _handle_product_action_guard(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: action_guard(
            a.get("product_id") or a.get("id"),
            a.get("action") or "",
            bool(a.get("confirmed")),
            a.get("proposal_id") or a.get("proposal") or "",
        ),
        args,
    )

def _handle_product_workflow_plan(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: workflow_plan(
            a.get("product_id") or a.get("id"),
            a.get("action") or "",
            bool(a.get("confirmed")),
            a.get("proposal_id") or a.get("proposal") or "",
            a.get("target") or "",
            int(a.get("variants") or 3),
        ),
        args,
    )

def _handle_product_conversation_adapter(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: conversation_adapter(
            a.get("product_id") or a.get("id"),
            a.get("message") or "",
            bool(a.get("confirmed")),
            a.get("proposal_id") or a.get("proposal") or "",
            a.get("target") or "",
            int(a.get("variants") or 3),
        ),
        args,
    )

def _handle_product_workflow_execute(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: workflow_execute(
            a.get("product_id") or a.get("id"),
            a.get("action") or "",
            a.get("message") or "",
            bool(a.get("confirmed")),
            a.get("proposal_id") or a.get("proposal") or "",
            a.get("target") or "",
            int(a.get("variants") or 3),
            a.get("name") or "",
            a.get("text") or "",
            a.get("images") or a.get("image") or [],
            a.get("note") or "",
            a.get("path") or "",
            a.get("role") or "",
            a.get("description") or "",
            a.get("usage") or [],
            a.get("asset") or a.get("material_id") or "",
            a.get("provider") or "",
            a.get("analysis") or a.get("analysis_id") or "",
        ),
        args,
    )

def _handle_product_workflow_run(args: Dict[str, Any], **_kw: Any) -> str:
    def _run(a: Dict[str, Any]) -> Dict[str, Any]:
        return product_agent_turn(
            a.get("product_id") or a.get("id") or "",
            a.get("product_query") or a.get("query") or "",
            bool(a.get("create_if_missing")),
            a.get("suggested_id") or "",
            a.get("name") or "",
            a.get("action") or "",
            a.get("message") or "",
            bool(a.get("confirmed")),
            a.get("proposal_id") or a.get("proposal") or "",
            a.get("target") or "",
            int(a.get("variants") or 3),
            a.get("text") or "",
            a.get("images") or a.get("image") or [],
            a.get("note") or "",
            a.get("path") or "",
            a.get("role") or "",
            a.get("description") or "",
            a.get("usage") or [],
            a.get("asset") or a.get("material_id") or "",
            a.get("provider") or "",
            a.get("analysis") or a.get("analysis_id") or "",
            int(a.get("max_steps") or 5),
            a.get("task_id") or "",
            a.get("autonomy_mode") or "adaptive",
            a.get("authorization_id") or "",
        )

    return _tool_ok(
        _run,
        args,
    )

def _handle_product_wiki_upgrade(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: wiki_upgrade_product(a.get("product_id") or a.get("id")), args)

def _handle_product_wiki_lint(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: wiki_lint_product(a.get("product_id") or a.get("id")), args)

def _handle_product_state_export(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: export_product_state_from_wiki(a.get("product_id") or a.get("id")), args)

def _handle_product_fingerprint(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: build_product_fingerprint(a.get("product_id") or a.get("id")), args)

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_create", schemas.PRODUCT_CREATE_SCHEMA, _handle_product_create, "product", "_handle_product_create"),
        CommandDescriptor("product_ingest", schemas.PRODUCT_INGEST_SCHEMA, _handle_product_ingest, "product", "_handle_product_ingest"),
        CommandDescriptor("product_context_pack", schemas.PRODUCT_CONTEXT_SCHEMA, _handle_product_context_pack, "product", "_handle_product_context_pack"),
        CommandDescriptor("product_workspace_resolve", schemas.PRODUCT_WORKSPACE_RESOLVE_SCHEMA, _handle_product_workspace_resolve, "product", "_handle_product_workspace_resolve"),
        CommandDescriptor("product_workflow_status", schemas.PRODUCT_WORKFLOW_STATUS_SCHEMA, _handle_product_workflow_status, "product", "_handle_product_workflow_status"),
        CommandDescriptor("product_workflow_next", schemas.PRODUCT_WORKFLOW_NEXT_SCHEMA, _handle_product_workflow_next, "product", "_handle_product_workflow_next"),
        CommandDescriptor("product_workflow_summary", schemas.PRODUCT_WORKFLOW_SUMMARY_SCHEMA, _handle_product_workflow_summary, "product", "_handle_product_workflow_summary"),
        CommandDescriptor("product_action_guard", schemas.PRODUCT_ACTION_GUARD_SCHEMA, _handle_product_action_guard, "product", "_handle_product_action_guard"),
        CommandDescriptor("product_workflow_plan", schemas.PRODUCT_WORKFLOW_PLAN_SCHEMA, _handle_product_workflow_plan, "product", "_handle_product_workflow_plan"),
        CommandDescriptor("product_conversation_adapter", schemas.PRODUCT_CONVERSATION_ADAPTER_SCHEMA, _handle_product_conversation_adapter, "product", "_handle_product_conversation_adapter"),
        CommandDescriptor("product_workflow_execute", schemas.PRODUCT_WORKFLOW_EXECUTE_SCHEMA, _handle_product_workflow_execute, "product", "_handle_product_workflow_execute"),
        CommandDescriptor("product_workflow_run", schemas.PRODUCT_WORKFLOW_RUN_SCHEMA, _handle_product_workflow_run, "product", "_handle_product_workflow_run"),
        CommandDescriptor("product_wiki_upgrade", schemas.PRODUCT_WIKI_UPGRADE_SCHEMA, _handle_product_wiki_upgrade, "product", "_handle_product_wiki_upgrade"),
        CommandDescriptor("product_wiki_lint", schemas.PRODUCT_WIKI_LINT_SCHEMA, _handle_product_wiki_lint, "product", "_handle_product_wiki_lint"),
        CommandDescriptor("product_state_export", schemas.PRODUCT_STATE_EXPORT_SCHEMA, _handle_product_state_export, "product", "_handle_product_state_export"),
        CommandDescriptor("product_fingerprint", schemas.PRODUCT_FINGERPRINT_SCHEMA, _handle_product_fingerprint, "product", "_handle_product_fingerprint"),
    )
