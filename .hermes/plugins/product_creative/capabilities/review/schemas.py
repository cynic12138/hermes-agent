"""Capability-owned tool schemas."""



from __future__ import annotations



from ...schema_common import PRODUCT_ID_PARAM



PRODUCT_EVALUATE_SCHEMA = {
    "name": "product_evaluate",
    "description": "Evaluate a generated product-copy-pack artifact without mutating Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "artifact_id": {"type": "string", "description": "Artifact id or path to a copy-pack JSON file."},
        },
        "required": ["product_id", "artifact_id"],
        "additionalProperties": False,
    },
}

PRODUCT_ARTIFACT_MANIFEST_SCHEMA = {
    "name": "product_artifact_manifest",
    "description": "Rebuild the unified artifact manifest for a product workspace.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_REVIEW_PACKAGE_SCHEMA = {
    "name": "product_review_package",
    "description": "Create a human-readable review package from a generation job.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "job_id": {"type": "string", "description": "Generation job id or path."},
        },
        "required": ["product_id", "job_id"],
        "additionalProperties": False,
    },
}

PRODUCT_RESULT_REVIEW_PACKAGE_SCHEMA = {
    "name": "product_result_review_package",
    "description": "Create a user-facing review package for a generated image or video result.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "result_id": {"type": "string", "description": "Generation result id or path."},
        },
        "required": ["product_id", "result_id"],
        "additionalProperties": False,
    },
}

PRODUCT_TASK_OVERVIEW_PACKAGE_SCHEMA = {
    "name": "product_task_overview_package",
    "description": "Create an M8 user-facing overview bundle for the latest or selected creative task.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "result_id": {"type": "string", "description": "Optional generated result id or path."},
            "workflow_run_id": {"type": "string", "description": "Optional workflow run id or path."},
            "title": {"type": "string", "description": "Optional review bundle title."},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_LIVE_READINESS_SCHEMA = {
    "name": "product_live_readiness",
    "description": "Check whether a provider is ready for live execution without calling external APIs.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "provider": {"type": "string", "default": "generic"},
            "kind": {"type": "string", "enum": ["image", "video"]},
            "payload_id": {"type": "string", "description": "Optional provider payload id or path."},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

