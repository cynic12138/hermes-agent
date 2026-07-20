"""Configurable provider gateway used by workflow action adapters."""

from __future__ import annotations

import os
from typing import Any, Dict

from .provider_ports import GenerationProviderGateway


class DefaultGenerationProviderGateway:
    @staticmethod
    def _require_mock(provider: str, mode: str = "") -> None:
        is_mock = (
            provider.lower().startswith("mock")
            or provider.lower() == "local-fixture"
            or mode.lower() in {"mock", "fixture"}
        )
        if not is_mock and os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") != "1":
            raise PermissionError("Real provider execution is disabled; use mock mode/provider.")

    def check_live_readiness(self, product_id: str, provider: str, kind: str, payload_id: str) -> Dict[str, Any]:
        from .provider_readiness import check_live_readiness

        return check_live_readiness(product_id, provider, kind, payload_id)

    def check_video_reference_readiness(self, product_id: str, payload_id: str) -> Dict[str, Any]:
        from .provider_readiness import check_video_reference_readiness

        return check_video_reference_readiness(product_id, payload_id)

    def create_video_execution_policy(
        self, product_id: str, payload_id: str, provider: str, mode: str, confirmed: bool, note: str
    ) -> Dict[str, Any]:
        from .provider_readiness import create_video_execution_policy

        return create_video_execution_policy(product_id, payload_id, provider, mode, confirmed, note)

    def prepare_payload(
        self,
        product_id: str,
        brief_id: str,
        provider: str,
        kind: str,
        production_bible: str = "",
    ) -> Dict[str, Any]:
        from .provider_payloads import prepare_provider_payload

        return prepare_provider_payload(
            product_id,
            brief_id,
            provider,
            kind,
            production_bible,
        )

    def submit_image(self, product_id: str, payload_id: str, provider: str, mode: str, count: int) -> Dict[str, Any]:
        self._require_mock(provider, mode)
        from .capabilities.image.generation_service import create_image_generation_run

        return create_image_generation_run(product_id, payload_id, provider, mode, count)

    def submit_video(
        self, product_id: str, payload_id: str, provider: str, mode: str, execution_policy_id: str
    ) -> Dict[str, Any]:
        self._require_mock(provider, mode)
        from .provider_generation import create_generation_job

        return create_generation_job(product_id, payload_id, provider, mode, execution_policy_id)

    def check_video_task(self, product_id: str, task_id: str, provider: str, download: bool) -> Dict[str, Any]:
        self._require_mock(provider)
        from .provider_video_tasks import check_video_task_status

        return check_video_task_status(product_id, task_id, provider, download)

    def import_video_result(
        self, product_id: str, task_id: str, url: str, provider: str, note: str, download: bool
    ) -> Dict[str, Any]:
        self._require_mock(provider)
        from .provider_video_tasks import import_video_result

        return import_video_result(product_id, task_id, url, provider, note, download)

    def prepare_media_shot(
        self,
        product_id: str,
        plan_id: str,
        shot_id: str,
        provider: str,
        media_kind: str,
    ) -> Dict[str, Any]:
        from .provider_shots import prepare_media_shot

        return prepare_media_shot(
            product_id,
            plan_id,
            shot_id,
            provider,
            media_kind,
        )

    def submit_media_shot(
        self,
        product_id: str,
        payload_id: str,
        provider: str,
        mode: str,
        execution_policy_id: str = "",
    ) -> Dict[str, Any]:
        self._require_mock(provider, mode)
        from .provider_shots import submit_media_shot

        return submit_media_shot(
            product_id,
            payload_id,
            provider,
            mode,
            execution_policy_id,
        )


_gateway: GenerationProviderGateway = DefaultGenerationProviderGateway()


def configure_generation_provider_gateway(gateway: GenerationProviderGateway) -> None:
    global _gateway
    _gateway = gateway


def generation_provider_gateway() -> GenerationProviderGateway:
    return _gateway
