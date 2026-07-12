"""Content grounding audit and repair service."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, today, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state
from ...contracts.models import CreativeTaskBrief
from ..inspiration.library_service import latest_inspiration_context
from ..material.pack_service import prepare_task_material_pack, record_material_usage
from .fallback_service import _generation_state


CLAIM_GUARD_TERMS = [
    "无添加",
    "不添加",
    "零添加",
    "不含",
    "无糖",
    "低糖",
    "有机",
    "认证",
    "检测报告",
    "检测证书",
    "可溯源",
    "溯源",
    "不催熟",
    "催熟剂",
    "非人工催熟",
    "树上",
    "枝头",
    "自然风干",
    "自然干燥",
    "包装",
    "独立包装",
    "小包装",
    "包装盒",
    "包装袋",
    "小袋",
    "布袋",
    "礼盒",
    "丝带",
    "麻绳",
    "内衬",
    "配料只有",
    "只有杏",
    "软糯",
    "不腻",
    "回甘",
    "甜润",
    "浓郁",
    "酸甜",
    "多汁",
    "厚实",
    "零负担",
    "低负担",
    "轻负担",
    "工厂",
    "果园",
    "杏林",
]

NEGATION_MARKERS = ["无", "不", "非", "禁止", "避免", "不要", "不出现"]

CLAUSE_BOUNDARIES = ["。", "；", ";", ".", "\n"]

SENSORY_REPLACEMENTS = {
    "不腻": "清甜",
    "回甘": "清甜",
    "甜润": "清甜",
    "软糯": "清甜",
    "浓郁": "有果香",
    "酸甜": "清甜",
    "多汁": "有果香",
    "厚实": "自然",
}

PACKAGING_REPLACEMENTS = {
    "包装": "呈现",
    "独立包装": "日常分享",
    "小包装": "日常分享",
    "包装盒": "分享场景",
    "包装袋": "分享场景",
    "小袋": "分享场景",
    "布袋": "分享场景",
    "礼盒": "分享场景",
    "丝带": "",
    "麻绳": "",
    "内衬": "",
}

def _evidence_text_from_state(state: Dict[str, Any]) -> str:
    state = _generation_state(state)
    evidence = {
        "brief": state.get("basic", {}).get("brief", ""),
        "selling_points": state.get("selling_points", []),
        "style_preferences": state.get("style_preferences", {}),
        "feedback_preferences": state.get("learning", {}).get("feedback_preferences", []),
        "channel_preferences": state.get("learning", {}).get("channel_preferences", []),
        "material_preferences": state.get("learning", {}).get("material_preferences", []),
    }
    return json.dumps(evidence, ensure_ascii=False, indent=2)

def _forbidden_terms_for_state(state: Dict[str, Any]) -> List[str]:
    evidence = _evidence_text_from_state(state)
    return [term for term in CLAIM_GUARD_TERMS if term not in evidence]

def _content_strings_from(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items: List[str] = []
        for child in value:
            items.extend(_content_strings_from(child))
        return items
    if isinstance(value, dict):
        items = []
        for key, child in value.items():
            if key == "generation_notes":
                continue
            items.extend(_content_strings_from(child))
        return items
    return []

def _has_unnegated_term(content: str, term: str) -> bool:
    for match in re.finditer(re.escape(term), content):
        if _is_negated_occurrence(content, match.start()):
            continue
        return True
    return False

def _is_negated_occurrence(content: str, start: int) -> bool:
    boundary = max(content.rfind(mark, 0, start) for mark in CLAUSE_BOUNDARIES)
    prefix = content[boundary + 1:start]
    return any(marker in prefix for marker in NEGATION_MARKERS)

def _audit_grounding(packs: List[Dict[str, Any]], state: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = _evidence_text_from_state(state)
    warnings: List[Dict[str, Any]] = []
    forbidden_terms = _forbidden_terms_for_state(state)
    for pack in packs:
        variant = pack.get("variant")
        content = "\n".join(_content_strings_from(pack))
        for term in forbidden_terms:
            if _has_unnegated_term(content, term):
                warnings.append(
                    {
                        "variant": variant,
                        "term": term,
                        "reason": "Term appears in generated content but not in Product State evidence.",
                    }
                )
    return warnings

def _replacement_for_term(term: str, state: Dict[str, Any]) -> str:
    evidence = _evidence_text_from_state(state)
    if term in SENSORY_REPLACEMENTS:
        replacement = SENSORY_REPLACEMENTS[term]
        if replacement in evidence:
            return replacement
        if "清甜" in evidence:
            return "清甜"
        if "果香" in evidence:
            return "有果香"
        return "自然"
    if term in PACKAGING_REPLACEMENTS:
        return PACKAGING_REPLACEMENTS[term]
    if term in {"树上", "枝头", "自然风干", "自然干燥", "不催熟", "催熟剂", "非人工催熟"}:
        return "自然成熟" if "自然成熟" in evidence else "自然"
    return ""

def _replace_unnegated_term(text: str, term: str, replacement: str) -> str:
    parts: List[str] = []
    cursor = 0
    for match in re.finditer(re.escape(term), text):
        parts.append(text[cursor:match.start()])
        if _is_negated_occurrence(text, match.start()):
            parts.append(match.group(0))
        else:
            parts.append(replacement)
        cursor = match.end()
    parts.append(text[cursor:])
    return "".join(parts)

def _repair_grounding_value(
    value: Any,
    state: Dict[str, Any],
    forbidden_terms: List[str],
    repairs: List[Dict[str, Any]],
    variant: Any,
    field_path: str,
) -> Any:
    if isinstance(value, str):
        updated = value
        for term in forbidden_terms:
            if not _has_unnegated_term(updated, term):
                continue
            replacement = _replacement_for_term(term, state)
            repaired = _replace_unnegated_term(updated, term, replacement)
            if repaired != updated:
                repairs.append(
                    {
                        "variant": variant,
                        "field": field_path,
                        "term": term,
                        "replacement": replacement,
                    }
                )
            updated = repaired
        return updated
    if isinstance(value, list):
        return [
            _repair_grounding_value(item, state, forbidden_terms, repairs, variant, f"{field_path}[{idx}]")
            for idx, item in enumerate(value)
        ]
    if isinstance(value, dict):
        repaired: Dict[str, Any] = {}
        for key, child in value.items():
            if key == "generation_notes":
                repaired[key] = child
            else:
                child_path = f"{field_path}.{key}" if field_path else str(key)
                repaired[key] = _repair_grounding_value(
                    child,
                    state,
                    forbidden_terms,
                    repairs,
                    variant,
                    child_path,
                )
        return repaired
    return value

def _repair_grounding(
    packs: List[Dict[str, Any]],
    state: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    forbidden_terms = _forbidden_terms_for_state(state)
    repairs: List[Dict[str, Any]] = []
    repaired_packs = []
    for pack in packs:
        repaired_packs.append(
            _repair_grounding_value(
                pack,
                state,
                forbidden_terms,
                repairs,
                pack.get("variant"),
                "",
            )
        )
    return repaired_packs, repairs
