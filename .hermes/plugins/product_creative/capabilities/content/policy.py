"""Capability-owned guard policies for content."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_run_channel_review(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    source_count = int(evidence.get("source_count") or 0)
    if current != "no_product" and source_count > 0:
        return _allow(result, "A new channel review workflow can start from any evidenced product state and will not mutate Product Brain.")
    return _block(result, "run_channel_review requires an existing product with at least one product evidence source.")

GUARD_POLICIES = {
    "run_channel_review": guard_run_channel_review,
}
