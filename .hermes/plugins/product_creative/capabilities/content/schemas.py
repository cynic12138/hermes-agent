"""Capability-owned tool schemas."""



from __future__ import annotations



from ...schema_common import PRODUCT_ID_PARAM



PRODUCT_TARGET_LIST_SCHEMA = {
    "name": "product_target_list",
    "description": "List supported Product Creative generation targets.",
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

PRODUCT_GENERATE_SCHEMA = {
    "name": "product_generate",
    "description": "Generate product creative artifacts from Product Brain context.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "target": {
                "type": "string",
                "enum": [
                    "product-copy-pack",
                    "ecommerce-main-image-copy",
                    "xiaohongshu-seeding-note",
                    "douyin-short-video-script",
                ],
            },
            "variants": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_CHANNEL_EVALUATE_SCHEMA = {
    "name": "product_channel_evaluate",
    "description": "Evaluate a generated channel content artifact without mutating Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "artifact_id": {"type": "string", "description": "Artifact id or path to a channel content JSON file."},
        },
        "required": ["product_id", "artifact_id"],
        "additionalProperties": False,
    },
}

PRODUCT_CHANNEL_REVIEW_PACKAGE_SCHEMA = {
    "name": "product_channel_review_package",
    "description": "Create a human-readable review package from channel content and optional channel evaluation.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "artifact_id": {"type": "string", "description": "Channel content artifact id or path."},
            "evaluation_id": {"type": "string", "description": "Optional channel evaluation id or path."},
        },
        "required": ["product_id", "artifact_id"],
        "additionalProperties": False,
    },
}

PRODUCT_CHANNEL_REVIEW_RUN_SCHEMA = {
    "name": "product_channel_review_run",
    "description": "Run generate, channel evaluation, and channel review package creation for one product channel target.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "target": {
                "type": "string",
                "enum": [
                    "ecommerce-main-image-copy",
                    "xiaohongshu-seeding-note",
                    "douyin-short-video-script",
                ],
            },
            "variants": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
        },
        "required": ["product_id", "target"],
        "additionalProperties": False,
    },
}

PRODUCT_BRIEF_SCHEMA = {
    "name": "product_brief",
    "description": "Export provider-agnostic image/video briefs from a product-copy-pack artifact.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "artifact_id": {"type": "string", "description": "Artifact id or path to a copy-pack JSON file."},
            "variant": {"type": "integer", "minimum": 1},
            "kind": {"type": "string", "enum": ["all", "image", "video"], "default": "all"},
            "preset": {
                "type": "string",
                "enum": ["default", "taobao-main-image", "douyin-9x16", "xiaohongshu-cover"],
                "default": "default",
            },
            "assets": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["product_id", "artifact_id"],
        "additionalProperties": False,
    },
}

PRODUCT_CREATIVE_RUN_SCHEMA = {
    "name": "product_creative_run",
    "description": "Run the image creative pipeline from copy pack to brief, payload, job, review, QA, and comparison artifacts.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "artifact_id": {"type": "string", "description": "Copy-pack artifact id or path."},
            "variant": {"type": "integer", "minimum": 1, "default": 1},
            "preset": {
                "type": "string",
                "enum": ["default", "taobao-main-image", "douyin-9x16", "xiaohongshu-cover"],
                "default": "xiaohongshu-cover",
            },
            "provider": {"type": "string", "default": "generic"},
            "mode": {"type": "string", "enum": ["dry_run", "mock", "live"], "default": "mock"},
            "count": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1},
        },
        "required": ["product_id", "artifact_id"],
        "additionalProperties": False,
    },
}

PRODUCT_COMPARISON_PACKAGE_SCHEMA = {
    "name": "product_comparison_package",
    "description": "Create a human comparison package from two or more generation jobs.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "job_ids": {"type": "array", "items": {"type": "string"}, "minItems": 2},
        },
        "required": ["product_id", "job_ids"],
        "additionalProperties": False,
    },
}

