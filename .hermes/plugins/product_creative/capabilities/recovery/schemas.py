"""Public Hermes/CLI schemas for controlled M9 recovery commands."""

from __future__ import annotations

from ...schema_common import PRODUCT_ID_PARAM


_CONFIRMATION = {
    "confirmed": {"type": "boolean", "default": False},
    "confirmation_id": {"type": "string", "description": "Pending confirmation id returned by the first request."},
    "reason": {"type": "string", "description": "Human reason recorded in the audit trail."},
    "actor": {"type": "string", "default": "user"},
}


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {"product_id": PRODUCT_ID_PARAM, **properties, **_CONFIRMATION},
            "required": ["product_id", *required],
            "additionalProperties": False,
        },
    }


PRODUCT_PROPOSAL_DECIDE_SCHEMA = _schema(
    "product_proposal_decide", "Accept or reject a Product Brain proposal through controlled confirmation.",
    {"proposal_id": {"type": "string"}, "decision": {"type": "string", "enum": ["accept", "reject"]}, "expected_version": {"type": "integer", "minimum": 1}},
    ["proposal_id", "decision", "expected_version"],
)
PRODUCT_BRAIN_ROLLBACK_SCHEMA = _schema(
    "product_brain_rollback", "Create a new Product Brain version from a prior version.",
    {"target_version": {"type": "integer", "minimum": 1}, "expected_version": {"type": "integer", "minimum": 1}},
    ["target_version", "expected_version"],
)
PRODUCT_WORKFLOW_RETRY_SCHEMA = _schema(
    "product_workflow_retry", "Retry the current recoverable workflow step.",
    {"workflow_id": {"type": "string"}, "expected_version": {"type": "integer", "minimum": 1}}, ["workflow_id", "expected_version"],
)
PRODUCT_WORKFLOW_CANCEL_SCHEMA = _schema(
    "product_workflow_cancel", "Cancel an unfinished durable workflow.",
    {"workflow_id": {"type": "string"}, "expected_version": {"type": "integer", "minimum": 1}}, ["workflow_id", "expected_version"],
)
PRODUCT_PROVIDER_TASK_REFRESH_SCHEMA = _schema(
    "product_provider_task_refresh", "Refresh the durable status projection of an existing provider task.",
    {"provider_task_id": {"type": "string"}}, ["provider_task_id"],
)
PRODUCT_RULE_REVOKE_SCHEMA = _schema(
    "product_rule_revoke", "Revoke a learned rule without deleting its history.",
    {"rule_id": {"type": "string"}}, ["rule_id"],
)
