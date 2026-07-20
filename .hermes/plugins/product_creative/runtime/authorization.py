"""Task-bound authorization for external research and billable generation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..common import ensure_product, now_iso, write_json
from ..contracts.models import (
    CreativeTaskRecord,
    TaskAuthorizationRecord,
    TaskAuthorizationRequest,
)
from ..ports.runtime_repositories import artifacts


def task_authorization_scope(task: CreativeTaskRecord) -> dict:
    """Return the exact external and paid-operation scope needed by a task."""

    sources = []
    message = task.request.raw_message
    explicit_platform_research = any(
        marker in message
        for marker in ("搜索", "抓取", "搜集", "查找", "参考帖子", "爆款灵感")
    )
    if task.request.requires_fresh_inspiration:
        sources.append("web")
    if explicit_platform_research and "小红书" in message:
        sources.append("xiaohongshu")
    if explicit_platform_research and "抖音" in message:
        sources.append("douyin")
    media_deliverables = set(task.request.deliverables)
    # A video task may require generated backgrounds/first frames before the
    # video provider is invoked. Exact packaging is composited locally and
    # does not replace the dynamic video-provider stage.
    needs_paid_image = bool(media_deliverables.intersection({"image", "video"}))
    needs_paid_video = "video" in media_deliverables
    return {
        "data_sources": sources,
        "allow_browser_cookies": any(
            item in sources for item in ("xiaohongshu", "douyin")
        ),
        "allow_paid_image": needs_paid_image,
        "allow_paid_video": needs_paid_video,
        "max_image_calls": 5 if needs_paid_image else 0,
        "max_video_calls": 5 if needs_paid_video else 0,
    }


def expire_pending_task_authorization_requests(
    product_id: str,
    task_id: str,
    *,
    keep_request_id: str = "",
) -> list[str]:
    """Expire superseded pending authorization projections for one task."""

    base = ensure_product(product_id)
    expired: list[str] = []
    for payload in artifacts().list(base.name, "task_authorization_requests"):
        try:
            request = TaskAuthorizationRequest.model_validate(payload)
        except (TypeError, ValueError):
            continue
        if (
            request.task_id != task_id
            or request.request_id == keep_request_id
            or request.status != "PENDING"
        ):
            continue
        request.status = "EXPIRED"
        write_json(Path(request.artifact_path), request.model_dump(mode="json"))
        expired.append(request.request_id)
    return expired


def create_task_authorization_request(task: CreativeTaskRecord) -> TaskAuthorizationRequest:
    base = ensure_product(task.product_id)
    expire_pending_task_authorization_requests(base.name, task.task_id)
    scope = task_authorization_scope(task)
    request_id = f"authorization-request-{uuid.uuid4().hex}"
    path = base / "artifacts" / "task_authorization_requests" / f"{request_id}.json"
    request = TaskAuthorizationRequest(
        request_id=request_id,
        task_id=task.task_id,
        product_id=task.product_id,
        **scope,
        created_at=now_iso(),
        artifact_path=str(path),
    )
    write_json(path, request.model_dump(mode="json"))
    return request


def approve_task_authorization(
    product_id: str,
    task_id: str,
    request_id: str,
    *,
    confirmed: bool,
) -> TaskAuthorizationRecord:
    if not confirmed:
        raise PermissionError("task authorization requires explicit user confirmation")
    base = ensure_product(product_id)
    payload = artifacts().get(base.name, request_id)
    request = TaskAuthorizationRequest.model_validate(payload)
    if request.product_id != base.name or request.task_id != task_id:
        raise ValueError("authorization request belongs to a different task or product")
    existing = next(
        (
            TaskAuthorizationRecord.model_validate(item)
            for item in artifacts().list(base.name, "task_authorizations")
            if item.get("request_id") == request_id and item.get("task_id") == task_id
        ),
        None,
    )
    if existing is not None:
        return existing
    authorization_id = f"authorization-{uuid.uuid4().hex}"
    path = base / "artifacts" / "task_authorizations" / f"{authorization_id}.json"
    authorization = TaskAuthorizationRecord(
        authorization_id=authorization_id,
        request_id=request.request_id,
        task_id=request.task_id,
        product_id=request.product_id,
        data_sources=list(request.data_sources),
        allow_browser_cookies=request.allow_browser_cookies,
        allow_paid_image=request.allow_paid_image,
        allow_paid_video=request.allow_paid_video,
        max_image_calls=request.max_image_calls,
        max_video_calls=request.max_video_calls,
        created_at=now_iso(),
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=8)).replace(microsecond=0).isoformat(),
        artifact_path=str(path),
    )
    write_json(path, authorization.model_dump(mode="json"))
    request.status = "APPROVED"
    write_json(Path(request.artifact_path), request.model_dump(mode="json"))
    return authorization


def load_task_authorization(product_id: str, authorization_id: str) -> TaskAuthorizationRecord:
    base = ensure_product(product_id)
    payload = artifacts().get(base.name, authorization_id)
    if not payload:
        raise FileNotFoundError(f"task authorization '{authorization_id}' does not exist")
    authorization = TaskAuthorizationRecord.model_validate(payload)
    if authorization.product_id != base.name:
        raise ValueError("task authorization belongs to a different product")
    return authorization


def consume_task_authorization(
    authorization: TaskAuthorizationRecord,
    action: str,
) -> TaskAuthorizationRecord:
    if not authorization_allows(authorization, action):
        raise PermissionError(f"task authorization does not allow '{action}'")
    if action == "submit_image_generation_job":
        authorization.used_image_calls += 1
    elif action == "submit_video_generation_task":
        authorization.used_video_calls += 1
    if (
        authorization.used_image_calls >= authorization.max_image_calls
        and authorization.used_video_calls >= authorization.max_video_calls
    ):
        authorization.status = "CONSUMED"
    write_json(Path(authorization.artifact_path), authorization.model_dump(mode="json"))
    return authorization


def authorization_allows(
    authorization: TaskAuthorizationRecord,
    action: str,
    *,
    source: str = "",
) -> bool:
    if authorization.status not in {"ACTIVE", "CONSUMED"}:
        return False
    if datetime.fromisoformat(authorization.expires_at) <= datetime.now(timezone.utc):
        return False
    # Status checks do not create another paid generation. They remain allowed
    # after the one-shot submit allowance has been consumed so an async video
    # task can be recovered to a terminal state.
    if action == "check_video_task_status":
        return bool(authorization.allow_paid_video)
    if authorization.status != "ACTIVE":
        return False
    if action == "apply_evolution_proposal":
        return False
    if action == "collect_external_source_snapshot":
        return bool(source and source in authorization.data_sources)
    if action == "submit_image_generation_job":
        return bool(
            authorization.allow_paid_image
            and authorization.used_image_calls < authorization.max_image_calls
        )
    if action == "submit_video_generation_task":
        return bool(
            authorization.allow_paid_video
            and authorization.used_video_calls < authorization.max_video_calls
        )
    return True
