"""Generation-safe Product State helpers for Product Creative."""

from __future__ import annotations

import re
from typing import Any, Dict, List


SOURCE_MARKERS = [
    "http://",
    "https://",
    "www.",
    ".com",
    ".cn",
    "来源",
    "source",
    "url",
    "产品页",
    "商品页",
    "FoodTalks",
    "Yami",
    "Weee",
    "初始事实摘录",
    "初始产品资料",
    "本轮生成目标",
    "核心不是",
    "文案只作为",
]


LABEL_PREFIXES = [
    "产品名",
    "品类",
    "规格",
    "核心成分方向",
    "主要卖点",
    "适用人群",
    "使用场景",
    "卖点",
    "口味",
    "包装",
]


def text_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def clean_labeled_text(value: str) -> str:
    item = text_value(value)
    item = item.strip(" \t-•*0123456789.、，。；;:：")
    item = re.sub(r"^#+\s*", "", item).strip()
    for prefix in LABEL_PREFIXES:
        item = re.sub(rf"^{re.escape(prefix)}\s*[:：]\s*", "", item).strip()
    item = item.strip(" \t-•*0123456789.、，。；;:：")
    return item


def is_source_or_meta_text(value: Any) -> bool:
    item = text_value(value)
    if not item:
        return True
    lowered = item.lower()
    if any(marker.lower() in lowered for marker in SOURCE_MARKERS):
        return True
    if item.startswith(("#", "---", "```")):
        return True
    if re.search(r"[A-Za-z]:\\|[/\\](raw|wiki|artifacts|assets|structured)[/\\]", item):
        return True
    if re.search(r"\b\d{8}-\d{6}\b", item):
        return True
    return False


def generation_safe_text(value: Any, max_chars: int = 120) -> str:
    item = clean_labeled_text(text_value(value))
    if not item or is_source_or_meta_text(item):
        return ""
    if len(item) > max_chars:
        item = item[: max_chars - 3].rstrip() + "..."
    return item


def generation_safe_list(values: Any, limit: int = 5, max_chars: int = 80) -> List[str]:
    items = values if isinstance(values, list) else []
    result: List[str] = []
    for value in items:
        item = generation_safe_text(value, max_chars=max_chars)
        if item and item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return result


def generation_safe_material_preferences(values: Any, limit: int = 5) -> List[str]:
    cleaned = []
    for value in values if isinstance(values, list) else []:
        item = re.sub(r"material-\d{8}-\d{6}-[A-Za-z0-9]+", "当前素材", text_value(value))
        item = re.sub(r"素材\s+当前素材", "当前素材", item)
        cleaned.append(item)
    return generation_safe_list(cleaned, limit=limit, max_chars=180)


def generation_safe_brief(value: Any, max_chars: int = 260) -> str:
    text = text_value(value)
    if not text:
        return ""
    safe_parts: List[str] = []
    for raw in re.split(r"[。\n]+", text):
        item = generation_safe_text(raw, max_chars=120)
        if item and item not in safe_parts:
            safe_parts.append(item)
        if len("。".join(safe_parts)) >= max_chars:
            break
    return "。".join(safe_parts)[:max_chars]


def build_generation_safe_state(state: Dict[str, Any]) -> Dict[str, Any]:
    basic = state.get("basic") if isinstance(state.get("basic"), dict) else {}
    learning = state.get("learning") if isinstance(state.get("learning"), dict) else {}
    safe_points = generation_safe_list(state.get("selling_points"), limit=6)
    if not safe_points:
        safe_points = generation_safe_list(re.split(r"[，,。；;、]+", text_value(basic.get("brief"))), limit=6)
    safe_learning = {
        "image_generation_preferences": generation_safe_list(learning.get("image_generation_preferences"), limit=5, max_chars=160),
        "video_script_preferences": generation_safe_list(learning.get("video_script_preferences"), limit=5, max_chars=160),
        "channel_preferences": generation_safe_list(learning.get("channel_preferences"), limit=5, max_chars=160),
        "successful_patterns": generation_safe_list(learning.get("successful_patterns"), limit=5, max_chars=160),
        "failed_patterns": generation_safe_list(learning.get("failed_patterns"), limit=5, max_chars=160),
        "material_preferences": generation_safe_material_preferences(learning.get("material_preferences"), limit=5),
    }
    return {
        "schema_version": "product_creative.generation_safe_context.v7.1",
        "product_name": generation_safe_text(state.get("name"), max_chars=80),
        "brief": generation_safe_brief(basic.get("brief")),
        "selling_points": safe_points,
        "learning": safe_learning,
        "excluded_source_markers": SOURCE_MARKERS,
    }


def apply_generation_safe_state(state: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(state)
    updated["generation_safe"] = build_generation_safe_state(updated)
    return updated
