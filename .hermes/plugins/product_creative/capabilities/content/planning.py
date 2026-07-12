"""Capability-owned workflow argument templates for content."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_run_channel_review(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {
                "product_id": product_id,
                "target": target or "<channel-target>",
                "variants": max(1, min(int(variants or 3), 5)),
            }

PLAN_TEMPLATES = {
    "run_channel_review": plan_run_channel_review,
}
