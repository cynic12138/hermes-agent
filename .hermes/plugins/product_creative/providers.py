"""Provider facade for Product Creative generation workflows."""

from __future__ import annotations

from .provider_adapters import PROMPT_ADAPTER_SCHEMA_VERSION, VIDEO_PROMPT_ADAPTER_SCHEMA_VERSION
from .provider_contracts import (
    GENERATION_JOB_SCHEMA_VERSION,
    GENERATION_RESULT_SCHEMA_VERSION,
    LIVE_READINESS_SCHEMA_VERSION,
    PROVIDER_PAYLOAD_SCHEMA_VERSION,
    PROVIDER_VALIDATION_SCHEMA_VERSION,
    VIDEO_EXECUTION_POLICY_SCHEMA_VERSION,
    VIDEO_REFERENCE_READINESS_SCHEMA_VERSION,
    VIDEO_TASK_SCHEMA_VERSION,
    VIDEO_TASK_STATUS_SCHEMA_VERSION,
)
from .provider_generation import create_generation_job
from .provider_payloads import prepare_provider_payload
from .provider_readiness import check_live_readiness, check_video_reference_readiness, create_video_execution_policy
from .provider_registry import list_providers
from .provider_validation import validate_provider_payload
from .provider_video_tasks import check_video_task_status, import_video_result


__all__ = [
    "GENERATION_JOB_SCHEMA_VERSION",
    "GENERATION_RESULT_SCHEMA_VERSION",
    "LIVE_READINESS_SCHEMA_VERSION",
    "PROMPT_ADAPTER_SCHEMA_VERSION",
    "PROVIDER_PAYLOAD_SCHEMA_VERSION",
    "PROVIDER_VALIDATION_SCHEMA_VERSION",
    "VIDEO_EXECUTION_POLICY_SCHEMA_VERSION",
    "VIDEO_PROMPT_ADAPTER_SCHEMA_VERSION",
    "VIDEO_REFERENCE_READINESS_SCHEMA_VERSION",
    "VIDEO_TASK_SCHEMA_VERSION",
    "VIDEO_TASK_STATUS_SCHEMA_VERSION",
    "check_live_readiness",
    "check_video_reference_readiness",
    "check_video_task_status",
    "create_generation_job",
    "create_video_execution_policy",
    "import_video_result",
    "list_providers",
    "prepare_provider_payload",
    "validate_provider_payload",
]
