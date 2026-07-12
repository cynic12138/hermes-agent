"""Capability-owned tool schemas."""



from __future__ import annotations



from ...schema_common import PRODUCT_ID_PARAM



MATERIAL_ROLE_ENUM = [
    "current_main_image",
    "product_photo",
    "detail_image",
    "style_reference",
    "video_first_frame",
    "generated_candidate",
    "reference_image",
]

TASK_MATERIAL_PACK_TASK_ENUM = [
    "video_brief",
    "image_brief",
    "channel_content",
    "provider_payload",
]

PRODUCT_TASK_MATERIAL_PACK_SCHEMA = {
    "name": "product_task_material_pack",
    "description": "Prepare a task-specific M3 material pack by reading local material cards and lightweight feedback.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "task": {"type": "string", "enum": TASK_MATERIAL_PACK_TASK_ENUM, "default": "channel_content"},
            "channel": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}



PRODUCT_ASSET_REGISTER_SCHEMA = {
    "name": "product_asset_register",
    "description": "Register a local image as a role-tagged product material asset without writing visual conclusions to Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "path": {"type": "string", "description": "Local image path."},
            "role": {"type": "string", "enum": MATERIAL_ROLE_ENUM, "default": "product_photo"},
            "description": {"type": "string"},
            "usage": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["product_id", "path"],
        "additionalProperties": False,
    },
}

PRODUCT_ASSET_BIND_URL_SCHEMA = {
    "name": "product_asset_bind_url",
    "description": "Bind a provider-accessible remote URL to a registered material asset for external video/image model calls.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "asset": {"type": "string", "description": "Material id or product-relative stored path."},
            "url": {"type": "string", "description": "Provider-accessible http(s) URL."},
            "usage": {"type": "string", "default": "video_reference"},
            "note": {"type": "string"},
        },
        "required": ["product_id", "asset", "url"],
        "additionalProperties": False,
    },
}

PRODUCT_ASSET_LIST_SCHEMA = {
    "name": "product_asset_list",
    "description": "List registered product material assets.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "role": {"type": "string", "enum": MATERIAL_ROLE_ENUM},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_PROVIDER_CAPABILITY_MATRIX_SCHEMA = {
    "name": "product_provider_capability_matrix",
    "description": "Return M6 provider media input capabilities such as data-url, remote URL, and asset URL support.",
    "parameters": {
        "type": "object",
        "properties": {
            "provider": {"type": "string", "description": "Optional provider name. Omit to return the default matrix."},
        },
        "additionalProperties": False,
    },
}

PRODUCT_MATERIAL_RESOLVE_SCHEMA = {
    "name": "product_material_resolve",
    "description": "Resolve a local material asset into a provider execution input without changing Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "material_id": {"type": "string", "description": "Material asset id."},
            "provider": {"type": "string", "default": "volcengine-ark-image"},
            "role": {"type": "string", "default": "reference_image"},
            "usage": {"type": "string", "default": "provider_payload"},
        },
        "required": ["product_id", "material_id"],
        "additionalProperties": False,
    },
}

PRODUCT_MATERIAL_MANIFEST_SCHEMA = {
    "name": "product_material_manifest",
    "description": "Rebuild the structured material library manifest from registered material asset artifacts.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_MATERIAL_COMPAT_SCHEMA = {
    "name": "product_material_compat",
    "description": "Check whether M2 material assets have image analysis and visual alignment artifacts for M3 material cards.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_MATERIAL_CARD_REBUILD_SCHEMA = {
    "name": "product_material_card_rebuild",
    "description": "Rebuild AI-readable M3 material cards from M2 material, image analysis, and visual alignment artifacts.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_MATERIAL_LIBRARY_MAP_SCHEMA = {
    "name": "product_material_library_map",
    "description": "Rebuild the file-readable M3 material library map grouped by role, usage, and readiness.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_MATERIAL_USAGE_SCHEMA = {
    "name": "product_material_usage",
    "description": "Record which local materials were used by a generated artifact without mutating Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "task": {"type": "string"},
            "channel": {"type": "string"},
            "task_material_pack_id": {"type": "string"},
            "artifact_id": {"type": "string"},
            "material_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_MATERIAL_FEEDBACK_SCHEMA = {
    "name": "product_material_feedback",
    "description": "Record lightweight feedback on a material selection; it remains reviewable evidence and does not write Product Brain directly.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "material_id": {"type": "string"},
            "note": {"type": "string"},
            "task": {"type": "string"},
            "channel": {"type": "string"},
            "selected": {"type": "boolean", "default": False},
            "rejected": {"type": "boolean", "default": False},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["product_id", "material_id", "note"],
        "additionalProperties": False,
    },
}

PRODUCT_IMAGE_ANALYZE_SCHEMA = {
    "name": "product_image_analyze",
    "description": "Create an image analysis artifact for a registered material asset. Use mock-vision for local metadata or a VLM provider for real multimodal understanding.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "asset": {"type": "string", "description": "Material id or product-relative stored path."},
            "provider": {"type": "string", "default": "mock-vision"},
        },
        "required": ["product_id", "asset"],
        "additionalProperties": False,
    },
}

PRODUCT_VISUAL_ALIGN_SCHEMA = {
    "name": "product_visual_align",
    "description": "Align an image analysis artifact with Product Brain and produce reviewable visual learning suggestions without applying them.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "analysis": {"type": "string", "description": "Image analysis id or product-relative path."},
            "note": {"type": "string", "description": "Optional user note for the visual learning proposal."},
        },
        "required": ["product_id", "analysis"],
        "additionalProperties": False,
    },
}

