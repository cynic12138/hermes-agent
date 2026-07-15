"""Capability-owned tool schemas."""



from __future__ import annotations



from ...contracts.actions import ACTION_NAMES

from ...schema_common import PRODUCT_ID_PARAM



WORKFLOW_ACTION_ENUM = sorted(ACTION_NAMES)

CHANNEL_TARGET_ENUM = [
    "ecommerce-main-image-copy",
    "xiaohongshu-seeding-note",
    "douyin-short-video-script",
]



PRODUCT_CREATE_SCHEMA = {
    "name": "product_create",
    "description": "Create a Product Creative workspace with initial Product Wiki and Product State.",
    "parameters": {
        "type": "object",
        "properties": {"product_id": PRODUCT_ID_PARAM, "name": {"type": "string"}},
        "required": ["product_id", "name"],
        "additionalProperties": False,
    },
}

PRODUCT_INGEST_SCHEMA = {
    "name": "product_ingest",
    "description": "Ingest product text and optional image paths into raw sources, then refresh draft Product State.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "text": {"type": "string", "description": "Literal text or a local file path."},
            "images": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_CONTEXT_SCHEMA = {
    "name": "product_context_pack",
    "description": "Return the context pack for a product generation target.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "target": {"type": "string", "default": "product-copy-pack"},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_WORKSPACE_RESOLVE_SCHEMA = {
    "name": "product_workspace_resolve",
    "description": (
        "Resolve a user-facing product name or phrase to a local Product Creative "
        "product_id. Use this before product_workflow_run when the user says a "
        "product name but does not know the internal product_id. It may create a "
        "new workspace only when create_if_missing is true and the user clearly "
        "asked to start a new product."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Product name, alias, or user phrase to resolve."},
            "create_if_missing": {"type": "boolean", "default": False},
            "suggested_id": {"type": "string", "description": "Optional ASCII product id to use when creating."},
            "name": {"type": "string", "description": "Human-readable product name when creating."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
        },
        "additionalProperties": False,
    },
}

PRODUCT_WORKFLOW_STATUS_SCHEMA = {
    "name": "product_workflow_status",
    "description": "Return the current Product Creative workflow state without mutating Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_WORKFLOW_NEXT_SCHEMA = {
    "name": "product_workflow_next",
    "description": "Return the recommended next workflow action and mutation/confirmation contract.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_WORKFLOW_SUMMARY_SCHEMA = {
    "name": "product_workflow_summary",
    "description": "Return a compact workflow summary for agent or user handoff.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_ACTION_GUARD_SCHEMA = {
    "name": "product_action_guard",
    "description": "Check whether a workflow action is allowed before execution, including confirmation and Product Brain mutation rules.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "action": {"type": "string", "enum": WORKFLOW_ACTION_ENUM},
            "proposal_id": {"type": "string", "description": "Optional proposal id for apply_evolution_proposal."},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id", "action"],
        "additionalProperties": False,
    },
}

PRODUCT_WORKFLOW_PLAN_SCHEMA = {
    "name": "product_workflow_plan",
    "description": "Build a guarded execution plan for the current or requested workflow action without executing tools.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "action": {"type": "string", "enum": WORKFLOW_ACTION_ENUM},
            "proposal_id": {"type": "string"},
            "target": {"type": "string", "enum": CHANNEL_TARGET_ENUM},
            "variants": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_CONVERSATION_ADAPTER_SCHEMA = {
    "name": "product_conversation_adapter",
    "description": "Translate a user message into a guarded workflow plan without executing tools.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "message": {"type": "string"},
            "proposal_id": {"type": "string"},
            "target": {"type": "string", "enum": CHANNEL_TARGET_ENUM},
            "variants": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["product_id", "message"],
        "additionalProperties": False,
    },
}

PRODUCT_WORKFLOW_EXECUTE_SCHEMA = {
    "name": "product_workflow_execute",
    "description": "Execute one ready guarded workflow plan step, or return a non-executed blocked plan.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "action": {"type": "string", "enum": WORKFLOW_ACTION_ENUM},
            "message": {"type": "string"},
            "proposal_id": {"type": "string"},
            "target": {"type": "string", "enum": CHANNEL_TARGET_ENUM},
            "variants": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
            "confirmed": {"type": "boolean", "default": False},
            "name": {"type": "string", "description": "Required only when executing create_product."},
            "text": {"type": "string", "description": "Required only when executing ingest_product_source."},
            "images": {"type": "array", "items": {"type": "string"}},
            "note": {"type": "string", "description": "Optional feedback note override."},
            "path": {"type": "string", "description": "Local image path for register_material_asset."},
            "role": {
                "type": "string",
                "enum": [
                    "current_main_image",
                    "product_photo",
                    "detail_image",
                    "style_reference",
                    "video_first_frame",
                    "generated_candidate",
                    "reference_image",
                ],
            },
            "description": {"type": "string", "description": "Optional material description."},
            "usage": {"type": "array", "items": {"type": "string"}},
            "asset": {"type": "string", "description": "Material id for analyze_material_image."},
            "provider": {"type": "string", "description": "Provider for analyze_material_image. Non-mock providers require explicit confirmation."},
            "analysis": {"type": "string", "description": "Image analysis id for align_visual_analysis."},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_WORKFLOW_RUN_SCHEMA = {
    "name": "product_workflow_run",
    "description": (
        "Primary natural-language entry point for Product Creative. Use when "
        "the user asks to create or continue a product workspace, ingest product "
        "information or materials, generate channel copy, image briefs, video "
        "briefs, register/analyze product images, record feedback, or continue "
        "the next product workflow step. Executes safe ready steps and stops at "
        "guard boundaries such as Product Brain mutation, live external provider "
        "calls, or required human confirmation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **PRODUCT_WORKFLOW_EXECUTE_SCHEMA["parameters"]["properties"],
            "product_query": {
                "type": "string",
                "description": "Optional user-facing product name/alias. Prefer product_workspace_resolve first when product_id is unknown.",
            },
            "create_if_missing": {
                "type": "boolean",
                "default": False,
                "description": "Create a product workspace only when the user explicitly asked to start a new product.",
            },
            "suggested_id": {
                "type": "string",
                "description": "Optional ASCII product id when creating from product_query.",
            },
            "max_steps": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            "task_id": {
                "type": "string",
                "description": "Continue an existing recoverable Creative Task.",
            },
            "autonomy_mode": {
                "type": "string",
                "enum": ["adaptive", "preview_first", "direct"],
                "default": "adaptive",
            },
            "authorization_id": {
                "type": "string",
                "description": "Optional authorization bound to this Creative Task; it never authorizes Product Brain writeback.",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
}

PRODUCT_WIKI_UPGRADE_SCHEMA = {
    "name": "product_wiki_upgrade",
    "description": "Upgrade a product wiki to the M1 canonical Product Brain schema without adding product-specific claims.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_WIKI_LINT_SCHEMA = {
    "name": "product_wiki_lint",
    "description": "Lint Product Wiki schema, frontmatter, sources, and cross-product isolation.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_STATE_EXPORT_SCHEMA = {
    "name": "product_state_export",
    "description": "Export structured Product State from the current product wiki.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

PRODUCT_FINGERPRINT_SCHEMA = {
    "name": "product_fingerprint",
    "description": "Build or refresh a product fingerprint used by cross-product guardrails.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

