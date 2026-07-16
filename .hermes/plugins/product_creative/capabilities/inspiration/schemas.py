"""Capability-owned tool schemas."""



from __future__ import annotations



from ...schema_common import PRODUCT_ID_PARAM



PRODUCT_EXTERNAL_SOURCE_COLLECT_SCHEMA = {
    "name": "product_external_source_collect",
    "description": (
        "Collect or import a small external source snapshot for creative inspiration. "
        "External data is saved as not_product_fact and never mutates Product Brain."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "provider": {
                "type": "string",
                "enum": ["manual", "manual-import", "generic-web", "xiaohongshu-sidecar", "douyin-sidecar"],
                "default": "manual",
            },
            "query": {"type": "string", "default": ""},
            "channel": {"type": "string", "default": ""},
            "mode": {"type": "string", "enum": ["dry_run", "import", "live"], "default": "dry_run"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            "import_path": {"type": "string", "default": ""},
            "text": {"type": "string", "default": ""},
            "url": {"type": "string", "default": ""},
            "sidecar_url": {"type": "string", "default": ""},
            "wait_seconds": {"type": "integer", "minimum": 5, "maximum": 600, "default": 90},
            "transcribe_limit": {"type": "integer", "minimum": 0, "maximum": 5, "default": 1},
            "analyze_first5_limit": {"type": "integer", "minimum": 0, "maximum": 5, "default": 1},
            "auto_browser_cookie": {"type": "boolean", "default": False},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_INSPIRATION_CANDIDATES_SCHEMA = {
    "name": "product_inspiration_candidates",
    "description": "Mine product-relevant inspiration candidates from an external source snapshot without mutating Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "snapshot_id": {"type": "string", "description": "External source snapshot id or path."},
            "goal": {"type": "string", "default": ""},
            "max_candidates": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
        "required": ["product_id", "snapshot_id"],
        "additionalProperties": False,
    },
}

PRODUCT_INSPIRATION_PACK_SCHEMA = {
    "name": "product_inspiration_pack",
    "description": "Create a task inspiration pack from selected or latest candidates for copy/image/video brief generation.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "candidate_ids": {"type": "array", "items": {"type": "string"}, "default": []},
            "goal": {"type": "string", "default": ""},
            "target": {
                "type": "string",
                "enum": ["", "product-copy-pack", "ecommerce-main-image-copy", "xiaohongshu-seeding-note", "douyin-short-video-script", "image_brief", "video_brief"],
                "default": "",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_LLM_INSPIRATION_PACK_SCHEMA = {
    "name": "product_llm_inspiration_pack",
    "description": (
        "Use Hermes ctx.llm to deeply summarize external platform snapshots into a review-required "
        "LLM inspiration pack. This never mutates Product Brain or the reusable inspiration library."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "snapshot_ids": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "External source snapshot ids. Omit to use the latest relevant snapshots.",
            },
            "goal": {"type": "string", "default": ""},
            "target": {
                "type": "string",
                "enum": ["", "product-copy-pack", "ecommerce-main-image-copy", "xiaohongshu-seeding-note", "douyin-short-video-script", "image_brief", "video_brief"],
                "default": "",
            },
            "channel": {"type": "string", "enum": ["", "xiaohongshu", "douyin", "web", "manual"], "default": ""},
            "max_items": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
            "provider": {"type": "string", "default": "", "description": "Optional Hermes provider override if plugin policy allows it."},
            "model": {"type": "string", "default": "", "description": "Optional Hermes model override if plugin policy allows it."},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_INSPIRATION_LIBRARY_CONFIRM_SCHEMA = {
    "name": "product_inspiration_library_confirm",
    "description": (
        "After the user reviews an LLM inspiration pack, confirm it into the reusable inspiration library. "
        "This still does not mutate Product Brain; it only makes the inspiration available to future generation context."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "pack_id": {"type": "string", "description": "LLM inspiration pack id or local path."},
            "note": {"type": "string", "default": ""},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id", "pack_id"],
        "additionalProperties": False,
    },
}

