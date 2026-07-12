"""Capability-owned guard policies for inspiration."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_collect_external_source_snapshot(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    return _allow(result, "External source collection is allowed as non-product-fact inspiration context for existing products.")

def guard_create_inspiration_candidates(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_snapshot = evidence.get("latest_external_source_snapshot") or {}
    if latest_snapshot:
                return _allow(result, "Latest external source snapshot can be mined into inspiration candidates.")
    return _block(result, "No external source snapshot is available for inspiration candidate mining.")

def guard_create_inspiration_pack(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_candidate = evidence.get("latest_inspiration_candidate") or {}
    if latest_candidate:
                return _allow(result, "Inspiration candidates can be packed into generation context without mutating Product Brain.")
    return _block(result, "No inspiration candidates are available for inspiration pack creation.")

def guard_create_llm_inspiration_pack(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_snapshot = evidence.get("latest_external_source_snapshot") or {}
    if latest_snapshot:
                return _allow(result, "Latest external source snapshot can be summarized by Hermes LLM into a review-required inspiration pack.")
    return _block(result, "No external source snapshot is available for LLM inspiration summarization.")

def guard_confirm_inspiration_library_entry(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_pack = evidence.get("latest_llm_inspiration_pack") or {}
    if not latest_pack:
                return _block(result, "No LLM inspiration pack is available for library confirmation.")
    if not confirmed:
                return _block(result, "Confirming an LLM inspiration pack into the reusable inspiration library requires explicit user confirmation.")
    return _allow(result, "User-confirmed LLM inspiration can be written to the reusable inspiration library without mutating Product Brain.")

GUARD_POLICIES = {
    "collect_external_source_snapshot": guard_collect_external_source_snapshot,
    "create_inspiration_candidates": guard_create_inspiration_candidates,
    "create_inspiration_pack": guard_create_inspiration_pack,
    "create_llm_inspiration_pack": guard_create_llm_inspiration_pack,
    "confirm_inspiration_library_entry": guard_confirm_inspiration_library_entry,
}
