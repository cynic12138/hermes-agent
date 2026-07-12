"""Capability-owned workflow argument templates for product."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_create_product(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {"product_id": product_id, "name": "<product-name>"}

def plan_ingest_product_source(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {"product_id": product_id, "text": "<product description>", "images": []}

PLAN_TEMPLATES = {
    "create_product": plan_create_product,
    "ingest_product_source": plan_ingest_product_source,
}
