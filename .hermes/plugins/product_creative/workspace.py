"""Request-scoped workspace resolution for CLI and Desktop plugin API calls."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator


_WORKSPACE_ROOT: ContextVar[Path | None] = ContextVar("product_creative_workspace_root", default=None)


def workspace_root() -> Path:
    return (_WORKSPACE_ROOT.get() or Path.cwd()).resolve()


def resolve_workspace_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace root must be an existing directory")
    return root


def resolve_within_workspace(value: str | Path, *, must_exist: bool = False) -> Path:
    root = workspace_root()
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve(strict=must_exist)
    if resolved != root and root not in resolved.parents:
        raise ValueError("path resolves outside the active workspace")
    return resolved


@contextmanager
def workspace_scope(value: str | Path) -> Iterator[Path]:
    root = resolve_workspace_root(value)
    token = _WORKSPACE_ROOT.set(root)
    try:
        yield root
    finally:
        _WORKSPACE_ROOT.reset(token)
