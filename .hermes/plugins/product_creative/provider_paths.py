"""Provider artifact path resolvers for Product Creative workspaces."""

from __future__ import annotations

from pathlib import Path


def resolve_brief_path(base: Path, brief: str) -> Path:
    if not brief:
        raise ValueError("brief id or path is required")
    candidate = Path(brief)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("brief path must stay inside the product workspace")
        return resolved

    name = brief if brief.endswith(".json") else f"{brief}.json"
    for folder in ["image_briefs", "video_scripts"]:
        path = base / "artifacts" / folder / name
        if path.exists():
            return path.resolve()
    raise FileNotFoundError(f"brief '{brief}' does not exist")


def resolve_payload_path(base: Path, payload: str) -> Path:
    if not payload:
        raise ValueError("provider payload id or path is required")
    candidate = Path(payload)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("provider payload path must stay inside the product workspace")
        return resolved

    name = payload if payload.endswith(".json") else f"{payload}.json"
    path = base / "artifacts" / "provider_payloads" / name
    if path.exists():
        return path.resolve()
    raise FileNotFoundError(f"provider payload '{payload}' does not exist")


def resolve_video_task_path(base: Path, task: str) -> Path:
    if not task:
        raise ValueError("video task id or path is required")
    candidate = Path(task)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("video task path must stay inside the product workspace")
        return resolved

    name = task if task.endswith(".json") else f"{task}.json"
    path = base / "artifacts" / "video_tasks" / name
    if path.exists():
        return path.resolve()
    raise FileNotFoundError(f"video task '{task}' does not exist")


def resolve_video_policy_path(base: Path, policy: str) -> Path:
    if not policy:
        raise ValueError("video execution policy id or path is required")
    candidate = Path(policy)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("video execution policy path must stay inside the product workspace")
        return resolved

    name = policy if policy.endswith(".json") else f"{policy}.json"
    path = base / "artifacts" / "video_execution_policies" / name
    if path.exists():
        return path.resolve()
    raise FileNotFoundError(f"video execution policy '{policy}' does not exist")


