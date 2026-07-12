"""Capability-owned tool schemas."""



from __future__ import annotations



from ...schema_common import PRODUCT_ID_PARAM



PRODUCT_RESULT_FEEDBACK_SCHEMA = {
    "name": "product_result_feedback",
    "description": "Record feedback against a generated image/video result without mutating Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "result_id": {"type": "string", "description": "Generation result id or path."},
            "note": {"type": "string"},
            "selected": {"type": "boolean"},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
            "issues": {"type": "array", "items": {"type": "string"}},
            "allow_evolve": {"type": "boolean", "default": False},
            "subject_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "product_recognizability": {"type": "integer", "minimum": 1, "maximum": 5},
            "composition": {"type": "integer", "minimum": 1, "maximum": 5},
            "style_fit": {"type": "integer", "minimum": 1, "maximum": 5},
            "copy_fit": {"type": "integer", "minimum": 1, "maximum": 5},
            "packaging_fidelity": {"type": "integer", "minimum": 1, "maximum": 5},
            "text_control": {"type": "integer", "minimum": 1, "maximum": 5},
            "motion_quality": {"type": "integer", "minimum": 1, "maximum": 5},
            "scene_fit": {"type": "integer", "minimum": 1, "maximum": 5},
            "first_frame_consistency": {"type": "integer", "minimum": 1, "maximum": 5},
            "factuality": {"type": "integer", "minimum": 1, "maximum": 5},
            "like_reasons": {"type": "array", "items": {"type": "string"}},
            "dislike_reasons": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["product_id", "result_id", "note"],
        "additionalProperties": False,
    },
}

PRODUCT_RESULT_EVALUATE_SCHEMA = {
    "name": "product_result_evaluate",
    "description": "Evaluate a generated result and its latest or selected feedback into evidence-backed learning candidates.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "result_id": {"type": "string", "description": "Generation result id or path."},
            "feedback_id": {"type": "string", "description": "Optional result feedback id or path."},
            "provider": {"type": "string", "description": "Optional LLM provider override."},
            "model": {"type": "string", "description": "Optional LLM model override."},
        },
        "required": ["product_id", "result_id"],
        "additionalProperties": False,
    },
}

PRODUCT_CHANNEL_FEEDBACK_SCHEMA = {
    "name": "product_channel_feedback",
    "description": "Record feedback against a generated channel content artifact without directly mutating Product Brain.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "artifact_id": {"type": "string", "description": "Channel content artifact id or path."},
            "note": {"type": "string"},
            "selected": {"type": "boolean"},
            "variant": {"type": "integer", "minimum": 1},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
            "allow_evolve": {"type": "boolean", "default": False},
            "issues": {"type": "array", "items": {"type": "string"}},
            "like_reasons": {"type": "array", "items": {"type": "string"}},
            "dislike_reasons": {"type": "array", "items": {"type": "string"}},
            "channel_fit": {"type": "integer", "minimum": 1, "maximum": 5},
            "factuality": {"type": "integer", "minimum": 1, "maximum": 5},
            "tone_fit": {"type": "integer", "minimum": 1, "maximum": 5},
            "actionability": {"type": "integer", "minimum": 1, "maximum": 5},
            "impressions": {"type": "number", "minimum": 0},
            "views": {"type": "number", "minimum": 0},
            "clicks": {"type": "number", "minimum": 0},
            "likes": {"type": "number", "minimum": 0},
            "saves": {"type": "number", "minimum": 0},
            "shares": {"type": "number", "minimum": 0},
            "comments": {"type": "number", "minimum": 0},
            "conversions": {"type": "number", "minimum": 0},
            "spend": {"type": "number", "minimum": 0},
            "revenue": {"type": "number", "minimum": 0},
        },
        "required": ["product_id", "artifact_id", "note"],
        "additionalProperties": False,
    },
}

PRODUCT_FEEDBACK_SCHEMA = {
    "name": "product_feedback_record",
    "description": "Record user feedback for a generated product artifact.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "artifact_id": {"type": "string"},
            "note": {"type": "string"},
            "selected": {"type": "boolean"},
            "variant": {"type": "integer", "minimum": 1},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["product_id", "artifact_id", "note"],
        "additionalProperties": False,
    },
}

PRODUCT_EVOLVE_SCHEMA = {
    "name": "product_evolve",
    "description": "Create or apply a reviewable Product Brain evolution proposal.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": PRODUCT_ID_PARAM,
            "apply_id": {"type": "string", "description": "Proposal id to apply. Omit to create a new proposal."},
        },
        "required": ["product_id"],
        "additionalProperties": False,
    },
}

