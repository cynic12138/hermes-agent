"""Capability-owned tool schemas."""



from __future__ import annotations



from ...schema_common import PRODUCT_ID_PARAM



PRODUCT_IMAGE_GENERATE_SCHEMA = {
    "name": "product_image_generate",
    "description": "Build a dry-run provider payload from an image brief. M0.5 does not call external providers.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string", "description": "Brief id or path to an image brief JSON file."},
            "provider": {"type": "string", "default": "generic"},
        },
        "required": ["product_id", "brief_id"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_INTENT_SCHEMA = {
    "name": "product_image_intent",
    "description": "Resolve a user image generation request into an M4 image intent using Product Brain and M3 material packs.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "message": {"type": "string"},
            "target": {
                "type": "string",
                "enum": ["ecommerce-main-image-copy", "xiaohongshu-seeding-note", "douyin-short-video-script"],
            },
            "count": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
            "style": {"type": "string"},
            "provider": {"type": "string", "default": "volcengine-ark-image"},
        },
        "required": ["product_id", "message"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_BRIEF_FROM_INTENT_SCHEMA = {
    "name": "product_image_brief",
    "description": "Create image brief draft(s) from an M4 image intent.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "intent_id": {"type": "string"},
            "artifact_id": {"type": "string"},
            "variant": {"type": "integer", "minimum": 1},
        },
        "required": ["product_id", "intent_id"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_BRIEF_REVIEW_PACKAGE_SCHEMA = {
    "name": "product_image_brief_review_package",
    "description": "Create an M4 review package and editable patch for an image brief.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string"},
        },
        "required": ["product_id", "brief_id"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_BRIEF_REVISE_SCHEMA = {
    "name": "product_image_brief_revise",
    "description": "Revise or confirm an M4 image brief before provider payload generation.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string"},
            "patch_id": {"type": "string"},
            "note": {"type": "string"},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id", "brief_id"],
        "additionalProperties": False,
    },
}

PRODUCT_BATCH_GENERATION_POLICY_SCHEMA = {
    "name": "product_batch_generation_policy",
    "description": "Create a confirmed M4 batch generation policy so multiple image prompt variations can run without per-brief confirmation.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "intent_id": {"type": "string"},
            "brief_id": {"type": "string"},
            "provider": {"type": "string", "default": "volcengine-ark-image"},
            "mode": {"type": "string", "enum": ["dry_run", "mock", "live"], "default": "mock"},
            "count": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
            "note": {"type": "string"},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_PROVIDER_PAYLOAD_SCHEMA = {
    "name": "product_image_provider_payload",
    "description": "Build a gated M4 image provider payload from a confirmed image brief or active batch policy.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "brief_id": {"type": "string"},
            "provider": {"type": "string", "default": "volcengine-ark-image"},
            "batch_policy_id": {"type": "string"},
        },
        "required": ["product_id", "brief_id"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_GENERATION_RUN_SCHEMA = {
    "name": "product_image_generation_run",
    "description": "Run M4 image generation from a gated provider payload and create review/QA/comparison artifacts.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "payload_id": {"type": "string"},
            "provider": {"type": "string", "default": "generic"},
            "mode": {"type": "string", "enum": ["dry_run", "mock", "live"], "default": "mock"},
            "count": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1},
        },
        "required": ["product_id", "payload_id"],
        "additionalProperties": False,
    },
}

PRODUCT_SELECTED_IMAGE_ASSET_SCHEMA = {
    "name": "product_selected_image_asset",
    "description": "Register a selected generated image back into the material library, defaulting to generated_candidate.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "result_id": {"type": "string"},
            "role": {"type": "string", "enum": ["generated_candidate", "current_main_image", "product_photo", "style_reference", "reference_image"], "default": "generated_candidate"},
            "description": {"type": "string"},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id", "result_id"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_QA_SCHEMA = {
    "name": "product_image_qa",
    "description": "Run local QA checks against a generated image result artifact.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "result_id": {"type": "string", "description": "Image result id or path."},
        },
        "required": ["product_id", "result_id"],
        "additionalProperties": False,
    },
}

