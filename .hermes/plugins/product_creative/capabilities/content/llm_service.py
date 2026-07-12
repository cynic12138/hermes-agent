"""Hermes LLM content generation service."""

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

from .fallback_service import TARGET_REGISTRY, _generation_state, _skill_text
from .grounding_service import _evidence_text_from_state, _forbidden_terms_for_state

_LLM: Any = None

def configure_llm(llm: Any) -> None:
    global _LLM
    _LLM = llm

def _json_for_prompt(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)

def _copy_pack_contract() -> Dict[str, Any]:
    return {
        "variants": [
            {
                "variant": 1,
                "style": "理性清晰型",
                "product_one_liner": "",
                "core_selling_points": [],
                "ecommerce_main_image_copy": {
                    "headline": "",
                    "subheadline": "",
                    "supporting_labels": [],
                    "visual_direction": "",
                },
                "image_generation_prompt": "",
                "short_video_storyboard": [
                    {
                        "shot": 1,
                        "duration": "0-3s",
                        "description": "",
                        "caption": "",
                    }
                ],
                "generation_notes": {
                    "basis": "",
                    "preference": "",
                    "requires_human_review": True,
                },
            }
        ]
    }

def _channel_contract(target: str) -> Dict[str, Any]:
    if target == "ecommerce-main-image-copy":
        return {
            "variants": [
                {
                    "variant": 1,
                    "style": "理性清晰型",
                    "main_title": "",
                    "subtitle": "",
                    "selling_point_lines": [],
                    "image_text_suggestions": [],
                    "visual_prompt_seed": "",
                    "avoid_claims": [],
                    "generation_notes": {
                        "basis": "",
                        "preference": "",
                        "requires_human_review": True,
                    },
                }
            ]
        }
    if target == "xiaohongshu-seeding-note":
        return {
            "variants": [
                {
                    "variant": 1,
                    "style": "社交种草型",
                    "title_options": [],
                    "opening_hook": "",
                    "body": "",
                    "selling_point_mapping": [],
                    "tone": "",
                    "hashtags": [],
                    "avoid_claims": [],
                    "generation_notes": {
                        "basis": "",
                        "preference": "",
                        "requires_human_review": True,
                    },
                }
            ]
        }
    if target == "douyin-short-video-script":
        return {
            "variants": [
                {
                    "variant": 1,
                    "style": "场景代入型",
                    "hook_0_3s": "",
                    "shots": [
                        {
                            "shot": 1,
                            "duration": "0-3s",
                            "visual": "",
                            "voiceover": "",
                            "caption": "",
                        }
                    ],
                    "product_exposure_points": [],
                    "cta": "",
                    "video_brief_seed": "",
                    "avoid_claims": [],
                    "generation_notes": {
                        "basis": "",
                        "preference": "",
                        "requires_human_review": True,
                    },
                }
            ]
        }
    raise ValueError(f"unsupported generation target '{target}'")

def _build_llm_instructions(context: Dict[str, Any], variants: int, target: str) -> str:
    state = _generation_state(apply_generation_safe_state(context.get("state") or {}))
    prompt_context = {
        **context,
        "state": state,
        "pages": {},
        "pages_omitted_for_generation_safety": True,
    }
    forbidden_terms = _forbidden_terms_for_state(state)
    target_spec = TARGET_REGISTRY[target]
    contract = _copy_pack_contract() if target == "product-copy-pack" else _channel_contract(target)
    creative_brief = context.get("task_creative_brief") or {}
    return (
        f"你是 product_creative 插件内的 {target} 生成器。"
        "只基于 Product Wiki、Product State、Material Context 和明确标记为 not_product_fact 的 Inspiration Context 输出内容；"
        "不得把灵感内容当成产品事实，不得编造未提供的产品事实。\n\n"
        f"生成目标：{target_spec['name']}。{target_spec['description']}\n"
        f"请生成 exactly {variants} 个中文内容方案。输出必须是单个 JSON object，"
        "不要包含 Markdown、解释文字或代码围栏。\n\n"
        "事实边界要求：\n"
        "- 只允许使用 Evidence facts 中已经出现的事实。\n"
        "- 可以创造表达风格、画面构图和场景节奏，但不能创造产品事实。\n"
        "- 关于添加剂、催熟、包装形式、检测报告、认证、溯源、配料、工厂、果园、枝头/树上成熟等事实，"
        "如果证据中没有明确出现，必须完全省略，不要用暗示性表达。\n"
        "- 不要把“送礼”扩写成礼盒、包装、丝带、布袋、麻绳等具体包装形式，除非证据中明确出现。\n"
        "- 如果证据只有“送礼/分享”，只能用递给对方、一起享用、放在桌面等行为表达，不得创造任何包装容器或包装动作。\n"
        "- 口感/气味只能使用证据中已有的词，不要把“清甜”扩写成回甘、不腻、甜润、软糯等新感官事实。\n"
        "- Forbidden terms 是硬约束；除非以“无/不要/禁止/避免/不出现”作为负向约束，否则这些词不得出现在任何输出字段。\n"
        "- 如果某个卖点很适合营销但证据不足，放弃这个卖点，不要写“如有”“可查”“待确认”到正式文案里。\n\n"
        "Turn-scoped creative brief (follow as creative direction, never treat it as a product fact):\n"
        f"{_json_for_prompt(creative_brief)}\n\n"
        "Evidence facts:\n"
        f"{_evidence_text_from_state(state)}\n\n"
        "Forbidden terms when absent from evidence:\n"
        f"{_json_for_prompt(forbidden_terms)}\n\n"
        "必须匹配这个结构：\n"
        f"{_json_for_prompt(contract)}\n\n"
        "Skill rules:\n"
        f"{_skill_text()}\n\n"
        "Product context:\n"
        f"{_json_for_prompt(prompt_context)}"
    )

def _usage_payload(usage: Any) -> Dict[str, Any]:
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
        "cache_read_tokens": getattr(usage, "cache_read_tokens", 0),
        "cache_write_tokens": getattr(usage, "cache_write_tokens", 0),
        "cost_usd": getattr(usage, "cost_usd", None),
    }

def _as_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"LLM output missing text field: {field}")
    return value.strip()

def _as_text_list(value: Any, field: str) -> List[str]:
    if not isinstance(value, list):
        raise ValueError(f"LLM output missing list field: {field}")
    items = [str(item).strip() for item in value if str(item).strip()]
    if not items:
        raise ValueError(f"LLM output has empty list field: {field}")
    return items

def _optional_text(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback

def _normalize_storyboard(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("LLM output missing short_video_storyboard")
    shots = []
    for idx, item in enumerate(value, 1):
        if not isinstance(item, dict):
            raise ValueError("LLM storyboard shot must be an object")
        description = _as_text(item.get("description"), "short_video_storyboard.description")
        duration = item.get("duration")
        if not isinstance(duration, str) or not duration.strip():
            duration = f"{max(0, (idx - 1) * 3)}-{idx * 3}s"
        caption = item.get("caption")
        if not isinstance(caption, str) or not caption.strip():
            caption = description
        shots.append(
            {
                "shot": int(item.get("shot") or idx),
                "duration": duration.strip(),
                "description": description,
                "caption": caption.strip(),
            }
        )
    return shots

def _normalize_copy_pack(item: Any, index: int) -> Dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("LLM variant must be an object")
    main_copy = item.get("ecommerce_main_image_copy")
    if not isinstance(main_copy, dict):
        raise ValueError("LLM output missing ecommerce_main_image_copy")
    notes = item.get("generation_notes")
    if not isinstance(notes, dict):
        raise ValueError("LLM output missing generation_notes")

    return {
        "variant": int(item.get("variant") or index),
        "style": _as_text(item.get("style"), "style"),
        "product_one_liner": _as_text(item.get("product_one_liner"), "product_one_liner"),
        "core_selling_points": _as_text_list(item.get("core_selling_points"), "core_selling_points"),
        "ecommerce_main_image_copy": {
            "headline": _as_text(main_copy.get("headline"), "ecommerce_main_image_copy.headline"),
            "subheadline": _as_text(main_copy.get("subheadline"), "ecommerce_main_image_copy.subheadline"),
            "supporting_labels": _as_text_list(
                main_copy.get("supporting_labels"),
                "ecommerce_main_image_copy.supporting_labels",
            ),
            "visual_direction": _as_text(
                main_copy.get("visual_direction"),
                "ecommerce_main_image_copy.visual_direction",
            ),
        },
        "image_generation_prompt": _as_text(item.get("image_generation_prompt"), "image_generation_prompt"),
        "short_video_storyboard": _normalize_storyboard(item.get("short_video_storyboard")),
        "generation_notes": {
            "basis": _optional_text(notes.get("basis"), "Product State evidence."),
            "preference": _optional_text(notes.get("preference"), "Follow Product State preferences."),
            "requires_human_review": bool(notes.get("requires_human_review", True)),
        },
    }

def _normalize_notes(value: Any) -> Dict[str, Any]:
    notes = value if isinstance(value, dict) else {}
    return {
        "basis": _optional_text(notes.get("basis"), "Product State evidence."),
        "preference": _optional_text(notes.get("preference"), "Follow Product State preferences."),
        "requires_human_review": bool(notes.get("requires_human_review", True)),
    }

def _normalize_shots(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("LLM output missing shots")
    shots = []
    for idx, item in enumerate(value, 1):
        if not isinstance(item, dict):
            raise ValueError("LLM shot must be an object")
        duration = item.get("duration")
        if not isinstance(duration, str) or not duration.strip():
            duration = f"{max(0, (idx - 1) * 3)}-{idx * 3}s"
        visual = _as_text(item.get("visual"), "shots.visual")
        voiceover = item.get("voiceover")
        if not isinstance(voiceover, str) or not voiceover.strip():
            voiceover = visual
        caption = item.get("caption")
        if not isinstance(caption, str) or not caption.strip():
            caption = voiceover
        shots.append(
            {
                "shot": int(item.get("shot") or idx),
                "duration": duration.strip(),
                "visual": visual,
                "voiceover": voiceover.strip(),
                "caption": caption.strip(),
            }
        )
    return shots

def _normalize_channel_content(item: Any, index: int, target: str) -> Dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("LLM variant must be an object")
    base = {
        "variant": int(item.get("variant") or index),
        "style": _as_text(item.get("style"), "style"),
    }
    if target == "ecommerce-main-image-copy":
        return {
            **base,
            "main_title": _as_text(item.get("main_title"), "main_title"),
            "subtitle": _as_text(item.get("subtitle"), "subtitle"),
            "selling_point_lines": _as_text_list(item.get("selling_point_lines"), "selling_point_lines"),
            "image_text_suggestions": _as_text_list(item.get("image_text_suggestions"), "image_text_suggestions"),
            "visual_prompt_seed": _as_text(item.get("visual_prompt_seed"), "visual_prompt_seed"),
            "avoid_claims": _as_text_list(item.get("avoid_claims"), "avoid_claims"),
            "generation_notes": _normalize_notes(item.get("generation_notes")),
        }
    if target == "xiaohongshu-seeding-note":
        return {
            **base,
            "title_options": _as_text_list(item.get("title_options"), "title_options"),
            "opening_hook": _as_text(item.get("opening_hook"), "opening_hook"),
            "body": _as_text(item.get("body"), "body"),
            "selling_point_mapping": _as_text_list(item.get("selling_point_mapping"), "selling_point_mapping"),
            "tone": _as_text(item.get("tone"), "tone"),
            "hashtags": _as_text_list(item.get("hashtags"), "hashtags"),
            "avoid_claims": _as_text_list(item.get("avoid_claims"), "avoid_claims"),
            "generation_notes": _normalize_notes(item.get("generation_notes")),
        }
    if target == "douyin-short-video-script":
        return {
            **base,
            "hook_0_3s": _as_text(item.get("hook_0_3s"), "hook_0_3s"),
            "shots": _normalize_shots(item.get("shots")),
            "product_exposure_points": _as_text_list(item.get("product_exposure_points"), "product_exposure_points"),
            "cta": _as_text(item.get("cta"), "cta"),
            "video_brief_seed": _as_text(item.get("video_brief_seed"), "video_brief_seed"),
            "avoid_claims": _as_text_list(item.get("avoid_claims"), "avoid_claims"),
            "generation_notes": _normalize_notes(item.get("generation_notes")),
        }
    raise ValueError(f"unsupported generation target '{target}'")

def _normalize_llm_payload(payload: Any, variants: int, target: str) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("LLM output must be a JSON object")
    raw_variants = payload.get("variants")
    if not isinstance(raw_variants, list) or not raw_variants:
        raise ValueError("LLM output must include non-empty variants")
    if target == "product-copy-pack":
        return [_normalize_copy_pack(item, idx) for idx, item in enumerate(raw_variants[:variants], 1)]
    return [
        _normalize_channel_content(item, idx, target)
        for idx, item in enumerate(raw_variants[:variants], 1)
    ]

def _generate_with_llm(
    base: Path,
    target: str,
    variants: int,
    material_context: Dict[str, Any] | None = None,
    creative_brief: Dict[str, Any] | None = None,
) -> Tuple[Optional[List[Dict[str, Any]]], Dict[str, Any]]:
    if os.environ.get("PRODUCT_CREATIVE_ENABLE_LLM") != "1" or os.environ.get("PRODUCT_CREATIVE_DISABLE_LLM") == "1":
        return None, {"llm_attempted": False, "fallback_reason": "llm_disabled"}
    if _LLM is None:
        return None, {"llm_attempted": False, "fallback_reason": "llm_not_configured"}
    try:
        from ..product.context_service import context_pack

        context = context_pack(base.name, target)
        if material_context:
            context["material_context"] = material_context
        if creative_brief:
            context["task_creative_brief"] = creative_brief
        result = _LLM.complete_structured(
            instructions=_build_llm_instructions(context, variants, target),
            input=[{"type": "text", "text": f"Generate the {target} JSON now."}],
            json_mode=True,
            temperature=0.1,
            max_tokens=4000,
            timeout=120,
            purpose=target,
        )
        if result.parsed is None:
            return None, {
                "llm_attempted": True,
                "fallback_reason": "llm_non_json_output",
                "raw_model_output": result.text,
                "llm": {
                    "provider": result.provider,
                    "model": result.model,
                    "agent_id": result.agent_id,
                    "usage": _usage_payload(result.usage),
                    "content_type": result.content_type,
                },
            }
        try:
            packs = _normalize_llm_payload(result.parsed, variants, target)
        except Exception as exc:
            return None, {
                "llm_attempted": True,
                "fallback_reason": f"{type(exc).__name__}: {exc}",
                "raw_model_output": result.text,
                "llm": {
                    "provider": result.provider,
                    "model": result.model,
                    "agent_id": result.agent_id,
                    "usage": _usage_payload(result.usage),
                    "content_type": result.content_type,
                },
            }
        return packs, {
            "llm_attempted": True,
            "llm": {
                "provider": result.provider,
                "model": result.model,
                "agent_id": result.agent_id,
                "usage": _usage_payload(result.usage),
                "content_type": result.content_type,
            },
        }
    except Exception as exc:
        return None, {
            "llm_attempted": True,
            "fallback_reason": f"{type(exc).__name__}: {exc}",
        }
