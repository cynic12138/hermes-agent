"""LLM-backed intent decisions with deterministic fallback."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..contracts.actions import ACTION_CONTRACTS
from ..contracts.models import IntentDecision
from .decision import action_from_message, target_from_message


_LLM: Any = None


def configure_llm(llm: Any) -> None:
    global _LLM
    _LLM = llm


def _modality(action: str) -> str:
    contract = ACTION_CONTRACTS.get(action) or {}
    declared = str(contract.get("modality") or "")
    if declared:
        return declared
    return {
        "image": "image",
        "video": "video",
        "channel_content": "text",
        "product_brain": "brain",
        "material": "material",
        "inspiration": "inspiration",
        "review": "review",
        "learning": "learning",
    }.get(str(contract.get("domain") or ""), "unknown")


def _fallback_decision(
    product_id: str,
    message: str,
    fallback_action: str,
    explicit_action: str,
    target: str,
    reason: str = "",
) -> IntentDecision:
    action = explicit_action or action_from_message(message, fallback_action)
    return IntentDecision(
        product_id=product_id,
        action=action,
        goal=message.strip(),
        modality=_modality(action),
        target=target or target_from_message(message),
        constraints=[
            item
            for item in ("preserve_exact_main_image" if any(marker in message for marker in ["主图不能变", "主图固定", "不重绘主图"]) else "",)
            if item
        ],
        confidence=1.0 if explicit_action else 0.65,
        rationale=reason or ("explicit action" if explicit_action else "deterministic rule fallback"),
        source="explicit_action" if explicit_action else "rule_fallback",
    )


def _decision_context(status: Dict[str, Any]) -> Dict[str, Any]:
    evidence = status.get("evidence") if isinstance(status.get("evidence"), dict) else {}
    compact_evidence = {
        key: {
            "id": value.get("id", ""),
            "status": value.get("status", ""),
        }
        for key, value in evidence.items()
        if isinstance(value, dict) and value.get("id")
    }
    return {
        "workflow_status": status.get("status"),
        "product_state": status.get("product_state") or {},
        "available_evidence": compact_evidence,
    }


def _instructions() -> str:
    action_catalog = [
        {
            "action": action,
            "domain": contract.get("domain"),
            "requires_user_input": contract.get("requires_user_input"),
            "requires_explicit_confirmation": contract.get("requires_explicit_confirmation"),
            "mutates_product_brain": contract.get("mutates_confirmed_product_brain"),
        }
        for action, contract in sorted(ACTION_CONTRACTS.items())
    ]
    schema = IntentDecision.model_json_schema()
    return (
        "You are the Product Creative Runtime decision layer. Select exactly one next action "
        "that best advances the user's product-centered creative goal. Understand whether the "
        "user wants text, image, video, exact-main-image video, review, feedback, inspiration, "
        "learning, material management, or Product Brain work. Never claim that confirmation was "
        "given. Never bypass provider or Product Brain safety gates. Return only JSON matching the "
        f"schema. Allowed actions: {json.dumps(action_catalog, ensure_ascii=False)}. "
        f"Output schema: {json.dumps(schema, ensure_ascii=False)}"
    )


def decide_intent(
    product_id: str,
    message: str,
    status: Dict[str, Any],
    fallback_action: str,
    explicit_action: str = "",
    target: str = "",
) -> IntentDecision:
    if explicit_action:
        if explicit_action not in ACTION_CONTRACTS:
            raise ValueError(f"unknown Product Creative action '{explicit_action}'")
        return _fallback_decision(product_id, message, fallback_action, explicit_action, target)
    if (
        not message.strip()
        or os.environ.get("PRODUCT_CREATIVE_ENABLE_LLM") != "1"
        or os.environ.get("PRODUCT_CREATIVE_DISABLE_LLM") == "1"
        or _LLM is None
    ):
        return _fallback_decision(product_id, message, fallback_action, "", target)

    payload = {
        "product_id": product_id,
        "user_message": message,
        "requested_target": target,
        "recommended_fallback_action": fallback_action,
        "runtime_context": _decision_context(status),
    }
    try:
        response = _LLM.complete_structured(
            instructions=_instructions(),
            input=[{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
            json_mode=True,
            temperature=0.0,
            max_tokens=1800,
            timeout=90,
            purpose="product_creative.intent_decision",
        )
        parsed = response.parsed if isinstance(response.parsed, dict) else {}
        parsed.setdefault("product_id", product_id)
        parsed.setdefault("goal", message.strip())
        parsed.setdefault("source", "llm")
        parsed.setdefault("target", target or target_from_message(message))
        decision = IntentDecision.model_validate(parsed)
        if decision.action not in ACTION_CONTRACTS:
            raise ValueError(f"LLM selected unknown action '{decision.action}'")
        if not decision.modality or decision.modality == "unknown":
            decision.modality = _modality(decision.action)
        decision.source = "llm"
        return decision
    except Exception as exc:
        return _fallback_decision(
            product_id,
            message,
            fallback_action,
            "",
            target,
            reason=f"LLM decision fallback: {type(exc).__name__}: {exc}",
        )
