"""Provider ports consumed by Product Creative application services."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class GenerationProviderGateway(Protocol):
    def check_live_readiness(self, product_id: str, provider: str, kind: str, payload_id: str) -> Dict[str, Any]: ...

    def check_video_reference_readiness(self, product_id: str, payload_id: str) -> Dict[str, Any]: ...

    def create_video_execution_policy(
        self, product_id: str, payload_id: str, provider: str, mode: str, confirmed: bool, note: str
    ) -> Dict[str, Any]: ...

    def prepare_payload(self, product_id: str, brief_id: str, provider: str, kind: str) -> Dict[str, Any]: ...

    def submit_image(
        self, product_id: str, payload_id: str, provider: str, mode: str, count: int
    ) -> Dict[str, Any]: ...

    def submit_video(
        self, product_id: str, payload_id: str, provider: str, mode: str, execution_policy_id: str
    ) -> Dict[str, Any]: ...

    def check_video_task(
        self, product_id: str, task_id: str, provider: str, download: bool
    ) -> Dict[str, Any]: ...

    def import_video_result(
        self, product_id: str, task_id: str, url: str, provider: str, note: str, download: bool
    ) -> Dict[str, Any]: ...
