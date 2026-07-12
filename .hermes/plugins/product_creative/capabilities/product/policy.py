"""Capability-owned guard policies for product."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_create_product(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    if current == "no_product":
                return _allow(result, "Product workspace does not exist; creation is allowed with user-provided product name.")
    return _block(result, f"Product already exists; create_product is not allowed from status '{current}'.")

def guard_ingest_product_source(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    if current in {"product_initialized", "ready_for_channel_run", "brain_updated"}:
                return _allow(result, "Adding product source evidence is allowed for the current product state.")
    return _block(result, f"Ingest is blocked while workflow status is '{current}'; resolve the pending workflow step first.")

GUARD_POLICIES = {
    "create_product": guard_create_product,
    "ingest_product_source": guard_ingest_product_source,
}
