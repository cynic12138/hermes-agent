"""Trusted user-plugin API adapter for the native M9 Desktop console."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT.parent))

from product_creative.application.command_bus import command_bus
from product_creative.application.console_queries import ProductCreativeConsoleQueries
from product_creative.contracts.durable import CommandEnvelope
from product_creative.contracts.errors import OptimisticVersionConflict
from product_creative.workspace import resolve_workspace_root, workspace_scope


router = APIRouter(prefix="/v1", tags=["product-creative"])
queries = ProductCreativeConsoleQueries()


async def _workspace(x_hermes_workspace_root: str = Header(..., alias="X-Hermes-Workspace-Root")) -> Iterator[Path]:
    try:
        root = resolve_workspace_root(x_hermes_workspace_root)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with workspace_scope(root):
        yield root


def _read(call):
    try:
        return call()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _dispatch(command: str, product_id: str, payload: Dict[str, Any]):
    try:
        result = command_bus().dispatch(CommandEnvelope(
            command=command, product_id=product_id,
            workflow_id=str(payload.get("workflow_id") or ""),
            trace_id=str(payload.get("trace_id") or f"desktop-{uuid.uuid4().hex}"),
            idempotency_key=str(payload.get("idempotency_key") or ""),
            confirmed=bool(payload.get("confirmed")), payload=payload,
        ))
    except OptimisticVersionConflict as exc:
        raise HTTPException(status_code=409, detail={"code": "STALE_STATE", "message": str(exc)}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "INVALID_STATE", "message": str(exc)}) from exc
    status = 428 if result.error_code == "CONFIRMATION_REQUIRED" else 400 if not result.success else 200
    return JSONResponse(status_code=status, content=result.model_dump(mode="json"))


@router.get("/health")
def health(_root: Path = Depends(_workspace)):
    return {"ok": True, "workspace": str(_root), "version": "9.0.0"}


@router.get("/products")
def products(_root: Path = Depends(_workspace)):
    return {"products": _read(queries.products)}


@router.get("/products/{product_id}/snapshot")
def snapshot(product_id: str, _root: Path = Depends(_workspace)):
    return _read(lambda: queries.snapshot(product_id))


@router.get("/products/{product_id}/review-queue")
def review_queue(product_id: str, _root: Path = Depends(_workspace)):
    return _read(lambda: queries.review_queue(product_id))


@router.get("/products/{product_id}/workflows")
def workflows(product_id: str, _root: Path = Depends(_workspace)):
    return {"workflows": _read(lambda: queries.workflows(product_id))}


@router.get("/workflows/{workflow_id}")
def workflow(workflow_id: str, _root: Path = Depends(_workspace)):
    payload = _read(lambda: queries.workflow(workflow_id))
    if not payload:
        raise HTTPException(status_code=404, detail="workflow not found")
    return payload


@router.get("/products/{product_id}/assets")
def assets(product_id: str, _root: Path = Depends(_workspace)):
    return _read(lambda: queries.assets(product_id))


@router.get("/products/{product_id}/learning")
def learning(product_id: str, _root: Path = Depends(_workspace)):
    return _read(lambda: queries.learning(product_id))


@router.get("/media/{record_id}")
def media(record_id: str, _root: Path = Depends(_workspace)):
    descriptor = _read(lambda: queries.media(record_id))
    return FileResponse(descriptor["path"], headers={"Cache-Control": "no-store"})


@router.post("/proposals/{proposal_id}/decision")
def proposal_decision(proposal_id: str, body: Dict[str, Any] = Body(...), _root: Path = Depends(_workspace)):
    payload = {**body, "proposal_id": proposal_id}
    return _dispatch("product_proposal_decide", str(body.get("product_id") or ""), payload)


@router.post("/products/{product_id}/brain/rollback")
def brain_rollback(product_id: str, body: Dict[str, Any] = Body(...), _root: Path = Depends(_workspace)):
    return _dispatch("product_brain_rollback", product_id, {**body, "product_id": product_id})


def _workflow_command(workflow_id: str, operation: str, body: Dict[str, Any]):
    detail = _read(lambda: queries.workflow(workflow_id))
    if not detail:
        raise HTTPException(status_code=404, detail="workflow not found")
    product_id = str(detail["workflow"]["product_id"])
    return _dispatch(f"product_workflow_{operation}", product_id, {**body, "product_id": product_id, "workflow_id": workflow_id})


@router.post("/workflows/{workflow_id}/retry")
def workflow_retry(workflow_id: str, body: Dict[str, Any] = Body(...), _root: Path = Depends(_workspace)):
    return _workflow_command(workflow_id, "retry", body)


@router.post("/workflows/{workflow_id}/cancel")
def workflow_cancel(workflow_id: str, body: Dict[str, Any] = Body(...), _root: Path = Depends(_workspace)):
    return _workflow_command(workflow_id, "cancel", body)


@router.post("/provider-tasks/{task_id}/refresh")
def provider_refresh(task_id: str, body: Dict[str, Any] = Body(...), _root: Path = Depends(_workspace)):
    return _dispatch("product_provider_task_refresh", str(body.get("product_id") or ""), {**body, "provider_task_id": task_id})


@router.post("/rules/{rule_id}/revoke")
def rule_revoke(rule_id: str, body: Dict[str, Any] = Body(...), _root: Path = Depends(_workspace)):
    return _dispatch("product_rule_revoke", str(body.get("product_id") or ""), {**body, "rule_id": rule_id})
