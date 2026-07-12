"""Deterministic content generation and target catalog."""

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


SKILL_PATH = Path(__file__).resolve().parents[2] / "skills" / "product-copy-pack" / "SKILL.md"

TARGET_REGISTRY: Dict[str, Dict[str, Any]] = {
    "product-copy-pack": {
        "target": "product-copy-pack",
        "name": "Product Copy Pack",
        "description": "General product copy, ecommerce main-image copy, image prompt, and storyboard seeds.",
        "context_profile": "product-copy-pack",
        "artifact_type": "copy_pack",
        "artifact_folder": "copy",
        "artifact_prefix": "copy-pack",
        "feedback_evolution_allowed": True,
    },
    "ecommerce-main-image-copy": {
        "target": "ecommerce-main-image-copy",
        "name": "Ecommerce Main Image Copy",
        "description": "Channel-specific ecommerce main-image copy and prompt seed.",
        "context_profile": "ecommerce-main-image-copy",
        "artifact_type": "channel_content",
        "artifact_folder": "channel_content",
        "artifact_prefix": "ecommerce-main-image-copy",
        "feedback_evolution_allowed": True,
    },
    "xiaohongshu-seeding-note": {
        "target": "xiaohongshu-seeding-note",
        "name": "Xiaohongshu Seeding Note",
        "description": "Structured Xiaohongshu-style seeding note drafts.",
        "context_profile": "xiaohongshu-seeding-note",
        "artifact_type": "channel_content",
        "artifact_folder": "channel_content",
        "artifact_prefix": "xiaohongshu-note",
        "feedback_evolution_allowed": True,
    },
    "douyin-short-video-script": {
        "target": "douyin-short-video-script",
        "name": "Douyin Short Video Script",
        "description": "Structured short-video script and video brief seed drafts; no live video generation.",
        "context_profile": "douyin-short-video-script",
        "artifact_type": "channel_content",
        "artifact_folder": "channel_content",
        "artifact_prefix": "douyin-script",
        "feedback_evolution_allowed": True,
    },
}

def list_generation_targets() -> Dict[str, Any]:
    return {
        "success": True,
        "targets": list(TARGET_REGISTRY.values()),
    }

def _skill_text() -> str:
    if not SKILL_PATH.exists():
        return ""
    return SKILL_PATH.read_text(encoding="utf-8")

def _skill_metadata() -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "name": "product-copy-pack",
        "path": str(SKILL_PATH),
        "loaded": SKILL_PATH.exists(),
    }
    if not SKILL_PATH.exists():
        return meta
    text = _skill_text()
    match = re.match(r"^---\n(.*?)\n---", text, flags=re.DOTALL)
    if not match:
        return meta
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key in {"name", "description", "version", "author"}:
            meta[key] = value
    return meta

def _preference_phrase(state: Dict[str, Any]) -> str:
    learning = state.get("learning", {})
    prefs = list(learning.get("feedback_preferences", []) or [])
    prefs.extend(learning.get("channel_preferences", []) or [])
    prefs.extend(learning.get("image_generation_preferences", []) or [])
    prefs.extend(learning.get("video_script_preferences", []) or [])
    prefs.extend(learning.get("material_preferences", []) or [])
    if not prefs:
        return "保持清晰可信，避免夸张表达。"
    return "；".join(str(p) for p in prefs[-3:])

def _variant_style(index: int) -> str:
    styles = ["理性清晰型", "场景代入型", "高级质感型", "轻促销转化型", "社交种草型"]
    return styles[(index - 1) % len(styles)]

def _generation_state(state: Dict[str, Any]) -> Dict[str, Any]:
    safe = state.get("generation_safe") if isinstance(state.get("generation_safe"), dict) else {}
    has_safe = isinstance(state.get("generation_safe"), dict)
    raw_basic = state.get("basic") if isinstance(state.get("basic"), dict) else {}
    raw_learning = state.get("learning") if isinstance(state.get("learning"), dict) else {}
    safe_learning = safe.get("learning") if isinstance(safe.get("learning"), dict) else {}
    merged_learning = {
        **raw_learning,
        **{key: value for key, value in safe_learning.items() if value},
    }
    return {
        **state,
        "name": safe.get("product_name") or state.get("name") or state.get("product_id"),
        "basic": {**raw_basic, "brief": safe.get("brief") if has_safe else raw_basic.get("brief", "")},
        "selling_points": safe.get("selling_points") if has_safe else state.get("selling_points") or [],
        "learning": merged_learning,
    }

def _build_copy_pack(state: Dict[str, Any], variant: int) -> Dict[str, Any]:
    state = _generation_state(state)
    name = state.get("name") or state.get("product_id") or "产品"
    brief = state.get("basic", {}).get("brief") or f"{name} 的产品资料仍需补充。"
    points = state.get("selling_points") or ["核心卖点待补充", "用户价值待确认", "使用场景待明确"]
    style = _variant_style(variant)
    preference = _preference_phrase(state)
    top_points = points[:3]
    headline_point = top_points[0] if top_points else brief[:40]
    selling_phrase = "、".join(top_points[:3])

    return {
        "variant": variant,
        "style": style,
        "product_one_liner": f"{name}，主打{selling_phrase}，适合重视品质与真实体验的用户。",
        "core_selling_points": top_points,
        "ecommerce_main_image_copy": {
            "headline": f"{name}｜{headline_point}",
            "subheadline": f"{selling_phrase}，一眼看懂为什么值得选。",
            "supporting_labels": top_points,
            "visual_direction": f"{style}；画面主体明确，背景干净，突出产品质感和使用结果。",
        },
        "image_generation_prompt": (
            f"为{name}设计一张电商主图。主体是产品本身，画面风格为{style}，"
            f"需要突出：{selling_phrase}。构图清晰，光线自然，背景简洁，"
            f"中文卖点文案可读。偏好约束：{preference}"
        ),
        "short_video_storyboard": [
            {
                "shot": 1,
                "duration": "0-3s",
                "description": f"用一个真实使用场景引出问题，让用户意识到{name}解决的痛点。",
                "caption": f"你是不是也遇到过：{headline_point}？",
            },
            {
                "shot": 2,
                "duration": "3-8s",
                "description": f"展示产品主体和第一核心卖点：{headline_point}。",
                "caption": headline_point,
            },
            {
                "shot": 3,
                "duration": "8-15s",
                "description": f"连续展示其他卖点：{'、'.join(top_points[1:] or top_points)}。",
                "caption": "细节决定体验。",
            },
            {
                "shot": 4,
                "duration": "15-22s",
                "description": "展示使用前后对比或场景结果，降低广告感。",
                "caption": "好产品应该让选择变简单。",
            },
            {
                "shot": 5,
                "duration": "22-30s",
                "description": "收束到产品记忆点和行动引导。",
                "caption": f"记住{name}，下次就选它。",
            },
        ],
        "generation_notes": {
            "basis": brief[:300],
            "preference": preference,
            "requires_human_review": True,
        },
    }

def _product_basics(state: Dict[str, Any]) -> Tuple[str, str, List[str], str, str, str]:
    state = _generation_state(state)
    name = state.get("name") or state.get("product_id") or "产品"
    brief = state.get("basic", {}).get("brief") or f"{name} 的产品资料仍需补充。"
    points = state.get("selling_points") or ["核心卖点待补充", "用户价值待确认", "使用场景待明确"]
    top_points = [str(item) for item in points[:3]]
    headline_point = top_points[0] if top_points else brief[:40]
    selling_phrase = "、".join(top_points[:3])
    preference = _preference_phrase(state)
    return name, brief, top_points, headline_point, selling_phrase, preference

def _avoid_claims() -> List[str]:
    return [
        "避免使用未在 Product State 中出现的认证、检测、功效、配料、包装细节。",
        "避免把使用场景扩写成未证实的产品事实。",
    ]

def _build_ecommerce_main_image_copy(state: Dict[str, Any], variant: int) -> Dict[str, Any]:
    name, brief, top_points, headline_point, selling_phrase, preference = _product_basics(state)
    style = _variant_style(variant)
    return {
        "variant": variant,
        "style": style,
        "main_title": f"{name}｜{headline_point}",
        "subtitle": f"{selling_phrase}，一眼看懂核心价值。",
        "selling_point_lines": top_points,
        "image_text_suggestions": [
            headline_point,
            *(top_points[1:3] if len(top_points) > 1 else top_points[:1]),
        ],
        "visual_prompt_seed": (
            f"电商主图，主体为{name}，{style}，背景干净，构图清晰，突出{selling_phrase}。"
            f"偏好约束：{preference}"
        ),
        "avoid_claims": _avoid_claims(),
        "generation_notes": {
            "basis": brief[:300],
            "preference": preference,
            "requires_human_review": True,
        },
    }

def _build_xiaohongshu_seeding_note(state: Dict[str, Any], variant: int) -> Dict[str, Any]:
    name, brief, top_points, headline_point, selling_phrase, preference = _product_basics(state)
    style = _variant_style(variant)
    title_tail = ["真实体验", "日常分享", "选择理由", "轻松种草", "使用感受"][(variant - 1) % 5]
    body_lines = [
        f"最近在整理日常好物时，我会优先看一个产品是不是足够清楚、真实、好理解。",
        f"{name}给我的第一印象是：{selling_phrase}。",
        f"如果你也在意{headline_point}，这个方向值得认真看一眼。",
        f"整体表达保持克制，不靠夸张话术，而是把产品本身讲明白。",
    ]
    return {
        "variant": variant,
        "style": style,
        "title_options": [
            f"{name}｜我会关注的{title_tail}",
            f"为什么我会记住{name}",
            f"{headline_point}，这点很打动我",
        ],
        "opening_hook": f"不是所有产品都需要说得很满，{name}更适合把真实卖点讲清楚。",
        "body": "\n".join(body_lines),
        "selling_point_mapping": [f"{idx + 1}. {point}" for idx, point in enumerate(top_points)],
        "tone": f"{style}；偏好约束：{preference}",
        "hashtags": [f"#{name}", "#好物分享", "#真实体验"],
        "avoid_claims": _avoid_claims(),
        "generation_notes": {
            "basis": brief[:300],
            "preference": preference,
            "requires_human_review": True,
        },
    }

def _build_douyin_short_video_script(state: Dict[str, Any], variant: int) -> Dict[str, Any]:
    name, brief, top_points, headline_point, selling_phrase, preference = _product_basics(state)
    style = _variant_style(variant)
    return {
        "variant": variant,
        "style": style,
        "hook_0_3s": f"如果你正在找一个{headline_point}的选择，先看{name}这几个点。",
        "shots": [
            {
                "shot": 1,
                "duration": "0-3s",
                "visual": f"快速展示{name}主体，画面干净，直接给出核心问题。",
                "voiceover": f"选{name}，我先看这一点：{headline_point}。",
                "caption": headline_point,
            },
            {
                "shot": 2,
                "duration": "3-8s",
                "visual": f"切到产品细节或使用场景，突出{selling_phrase}。",
                "voiceover": f"它的重点是{selling_phrase}。",
                "caption": selling_phrase,
            },
            {
                "shot": 3,
                "duration": "8-15s",
                "visual": "用一个真实场景承接产品价值，减少叫卖感。",
                "voiceover": "好的产品表达，不需要堆很多夸张词。",
                "caption": "把重点讲清楚。",
            },
            {
                "shot": 4,
                "duration": "15-22s",
                "visual": f"回到{name}完整主体，收束记忆点。",
                "voiceover": f"记住{name}，重点就是{headline_point}。",
                "caption": f"记住{name}",
            },
        ],
        "product_exposure_points": top_points,
        "cta": "想看更完整的产品方案，可以继续对比下一版。",
        "video_brief_seed": (
            f"抖音短视频脚本，{style}，围绕{name}，突出{selling_phrase}。"
            f"镜头节奏清晰，商品露出明确，偏好约束：{preference}"
        ),
        "avoid_claims": _avoid_claims(),
        "generation_notes": {
            "basis": brief[:300],
            "preference": preference,
            "requires_human_review": True,
        },
    }

def _build_channel_content(state: Dict[str, Any], target: str, variant: int) -> Dict[str, Any]:
    if target == "ecommerce-main-image-copy":
        return _build_ecommerce_main_image_copy(state, variant)
    if target == "xiaohongshu-seeding-note":
        return _build_xiaohongshu_seeding_note(state, variant)
    if target == "douyin-short-video-script":
        return _build_douyin_short_video_script(state, variant)
    raise ValueError(f"unsupported generation target '{target}'")
