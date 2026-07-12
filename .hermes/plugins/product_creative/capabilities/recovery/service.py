"""Controlled recovery use cases; all entry points are policy-gated actions."""

from __future__ import annotations

from typing import Any, Dict

from ...ports.runtime_repositories import recovery
from ..learning.writeback_service import evolve_product


def _audit(args: Dict[str, Any], subject_id: str, decision: str, result: Dict[str, Any]) -> Dict[str, Any]:
    store = recovery()
    store.record_confirmation(
        str(args.get("confirmation_id") or ""), decision=decision,
        actor=str(args.get("actor") or "user"), reason=str(args.get("reason") or ""),
        expected_version=args.get("expected_version"), result=result,
    )
    store.audit(
        str(args.get("product_id") or result.get("product_id") or ""), str(args.get("command") or ""),
        subject_id, decision, str(args.get("actor") or "user"), str(args.get("reason") or ""), result,
        str(args.get("trace_id") or ""),
    )
    return result


def proposal_decide(args: Dict[str, Any]) -> Dict[str, Any]:
    product_id, proposal_id = str(args["product_id"]), str(args["proposal_id"])
    decision = str(args.get("decision") or "reject")
    if decision == "accept":
        result = evolve_product(product_id, proposal_id, expected_version=int(args["expected_version"]))
    elif decision == "reject":
        result = {"success": True, "product_id": product_id, "proposal": recovery().reject_proposal(product_id, proposal_id, str(args.get("reason") or ""))}
    else:
        raise ValueError("proposal decision must be accept or reject")
    return _audit({**args, "command": "product_proposal_decide"}, proposal_id, decision, result)


def brain_rollback(args: Dict[str, Any]) -> Dict[str, Any]:
    result = recovery().rollback_brain(str(args["product_id"]), int(args["target_version"]), int(args["expected_version"]))
    payload = {"success": True, "product_id": args["product_id"], "brain_version": result}
    return _audit({**args, "command": "product_brain_rollback"}, str(args["target_version"]), "rollback", payload)


def rule_revoke(args: Dict[str, Any]) -> Dict[str, Any]:
    result = recovery().revoke_rule(str(args["product_id"]), str(args["rule_id"]), str(args.get("reason") or ""))
    payload = {"success": True, "product_id": args["product_id"], "rule": result}
    return _audit({**args, "command": "product_rule_revoke"}, str(args["rule_id"]), "revoke", payload)


def workflow_recover(args: Dict[str, Any], operation: str) -> Dict[str, Any]:
    result = recovery().recover_workflow(str(args["workflow_id"]), operation=operation, expected_version=int(args["expected_version"]))
    payload = {"success": True, **result}
    return _audit({**args, "command": f"product_workflow_{operation}"}, str(args["workflow_id"]), operation, payload)


def provider_refresh(args: Dict[str, Any]) -> Dict[str, Any]:
    result = recovery().refresh_provider_task(str(args["provider_task_id"]))
    payload = {"success": True, **result}
    return _audit({**args, "command": "product_provider_task_refresh"}, str(args["provider_task_id"]), "refresh", payload)
