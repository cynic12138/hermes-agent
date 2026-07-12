"""Capability-owned tool schemas."""



from __future__ import annotations



from ...schema_common import PRODUCT_ID_PARAM



PRODUCT_VIDEO_INTENT_SCHEMA = {
    "name": "product_video_intent",
    "description": "Resolve a user video request into a safe preparation plan using Product Brain, material assets, image analysis, and visual alignment.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "message": {"type": "string", "description": "User video request, such as 今日视频 or 用这张主图做视频."},
            "asset": {"type": "string", "description": "Optional material id or path to prefer."},
            "platform": {"type": "string", "enum": ["douyin", "xiaohongshu", "ecommerce"]},
            "theme": {"type": "string", "description": "Optional topic/theme override."},
        },
        "required": ["product_id", "message"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_BRIEF_SCHEMA = {
    "name": "product_video_brief",
    "description": "Create a provider-agnostic image-to-video brief from a ready M2.17 video intent.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "intent_id": {"type": "string", "description": "Video intent id or path."},
        },
        "required": ["product_id", "intent_id"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_GENERATE_SCHEMA = {
    "name": "product_video_generate",
    "description": "Build a provider payload from a confirmed video brief. This does not submit a live video task.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string", "description": "Brief id or path to a video brief JSON file."},
            "provider": {"type": "string", "default": "generic"},
        },
        "required": ["product_id", "brief_id"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_REFERENCE_READINESS_SCHEMA = {
    "name": "product_video_reference_readiness",
    "description": "Check whether video provider payload reference media URLs are ready for external video generation.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "payload_id": {"type": "string", "description": "Video provider payload id or path."},
        },
        "required": ["product_id", "payload_id"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_EXECUTION_POLICY_SCHEMA = {
    "name": "product_video_execution_policy",
    "description": "Create the explicit human-approved live video execution policy before submitting a video task.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "payload_id": {"type": "string", "description": "Video provider payload id or path."},
            "provider": {"type": "string", "default": "volcengine-ark-video"},
            "mode": {"type": "string", "enum": ["live"], "default": "live"},
            "confirmed": {"type": "boolean", "default": False},
            "note": {"type": "string", "default": ""},
        },
        "required": ["product_id", "payload_id"],
        "additionalProperties": False,
    },
}

PRODUCT_PROVIDER_LIST_SCHEMA = {
    "name": "product_provider_list",
    "description": "List registered image/video providers and their current adapter status.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["image", "video"]},
        },
        "additionalProperties": False,
    },
}

PRODUCT_PROVIDER_VALIDATE_SCHEMA = {
    "name": "product_provider_validate",
    "description": "Validate a provider payload against a registered provider without external execution.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "payload_id": {"type": "string", "description": "Payload id or path to a provider payload JSON file."},
            "provider": {"type": "string", "default": "generic"},
        },
        "required": ["product_id", "payload_id"],
        "additionalProperties": False,
    },
}

PRODUCT_GENERATION_JOB_SCHEMA = {
    "name": "product_generation_job",
    "description": "Create a dry-run, mock, or controlled live generation job from a provider payload. Live video requires an approved execution policy.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "payload_id": {"type": "string", "description": "Payload id or path to a provider payload JSON file."},
            "provider": {"type": "string", "default": "generic"},
            "mode": {"type": "string", "enum": ["dry_run", "mock", "live"], "default": "mock"},
            "execution_policy_id": {"type": "string", "description": "Required for live video task submission.", "default": ""},
        },
        "required": ["product_id", "payload_id"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_TASK_STATUS_SCHEMA = {
    "name": "product_video_task_status",
    "description": "Query a submitted async video task and import the generated video when the provider result is ready.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "task_id": {"type": "string", "description": "Video task id or path."},
            "provider": {"type": "string", "default": ""},
            "download": {"type": "boolean", "default": True},
        },
        "required": ["product_id", "task_id"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_RESULT_IMPORT_SCHEMA = {
    "name": "product_video_result_import",
    "description": "Manually import a generated video URL into the current product workspace when provider status polling is unavailable.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "task_id": {"type": "string", "description": "Video task id or path."},
            "url": {"type": "string", "description": "Generated video result URL."},
            "provider": {"type": "string", "default": ""},
            "note": {"type": "string", "default": ""},
            "download": {"type": "boolean", "default": True},
        },
        "required": ["product_id", "task_id", "url"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_BRIEF_REVIEW_PACKAGE_SCHEMA = {
    "name": "product_video_brief_review_package",
    "description": "Create a human-readable review package from a video brief before provider payload generation.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string", "description": "Video brief id or path."},
        },
        "required": ["product_id", "brief_id"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_BRIEF_REVISE_SCHEMA = {
    "name": "product_video_brief_revise",
    "description": "Create a revised and optionally confirmed video brief from an editable M2.28 review patch.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string", "description": "Source video brief id or path."},
            "patch_id": {"type": "string", "description": "Editable video brief patch id or path."},
            "note": {"type": "string", "description": "Human review note for the revision."},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id", "brief_id"],
        "additionalProperties": False,
    },
}

PRODUCT_EXACT_MAIN_VIDEO_SCHEMA = {
    "name": "product_exact_main_video",
    "description": "Compose a local product story video that keeps the registered main image as a fixed, unredrawn layer.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "asset_id": {"type": "string", "description": "Optional material id/path. Defaults to current_main_image."},
            "theme": {"type": "string", "description": "Optional video theme or story direction."},
            "template": {
                "type": "string",
                "enum": ["anime_story", "summer_refresh", "problem_solution", "three_claims", "festival_topic"],
                "default": "anime_story",
            },
            "duration": {"type": "integer", "minimum": 2, "maximum": 15, "default": 10},
            "fps": {"type": "integer", "minimum": 6, "maximum": 30, "default": 24},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_VIDEO_BRIEF_FEEDBACK_SCHEMA = {
    "name": "product_video_brief_feedback",
    "description": "Record feedback against a video brief/storyboard/prompt without waiting for generated video output.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string", "description": "Video brief id or path."},
            "note": {"type": "string"},
            "selected": {"type": "boolean"},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
            "allow_evolve": {"type": "boolean", "default": False},
            "issues": {"type": "array", "items": {"type": "string"}},
            "like_reasons": {"type": "array", "items": {"type": "string"}},
            "dislike_reasons": {"type": "array", "items": {"type": "string"}},
            "hook_strength": {"type": "integer", "minimum": 1, "maximum": 5},
            "storyboard_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "product_grounding": {"type": "integer", "minimum": 1, "maximum": 5},
            "prompt_specificity": {"type": "integer", "minimum": 1, "maximum": 5},
            "channel_fit": {"type": "integer", "minimum": 1, "maximum": 5},
            "factuality": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["product_id", "brief_id", "note"],
        "additionalProperties": False,
    },
}

