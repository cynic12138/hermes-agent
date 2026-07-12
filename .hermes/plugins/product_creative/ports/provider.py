"""Provider task port used by the outbox worker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class ProviderRequest:
    provider: str
    kind: str
    idempotency_key: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResponse:
    status: str
    payload: Dict[str, Any] = field(default_factory=dict)
    external_task_id: str = ""


class ProviderTaskGateway(Protocol):
    def execute(self, request: ProviderRequest) -> ProviderResponse: ...
