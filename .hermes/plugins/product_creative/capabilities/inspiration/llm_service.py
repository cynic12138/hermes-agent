"""Hermes LLM inspiration synthesis service."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import artifacts

from .shared import _list, _rel, _safe_limit, _sanitize_string, _text
from .collection_service import _resolve_snapshot

LLM_INSPIRATION_PACK_SCHEMA_VERSION = "product_creative.llm_inspiration_pack.v6.11"

_LLM: Any = None

def configure_llm(llm: Any) -> None:
    global _LLM
    _LLM = llm

def _usage_payload(usage: Any) -> Dict[str, Any]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
        "completion_tokens": getattr(usage, "completion_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
    }

def _strings(value: Any, limit: int = 8, item_limit: int = 300) -> List[str]:
    if isinstance(value, list):
        return [_sanitize_string(item, item_limit) for item in value[:limit] if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [_sanitize_string(value, item_limit)]
    return []

def _dicts(value: Any, limit: int = 8) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value[:limit] if isinstance(item, dict)]

def _llm_output_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary_title": {"type": "string"},
            "executive_summary": {"type": "string"},
            "channel_insights": {"type": "array", "items": {"type": "string"}},
            "hooks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "why_it_works": {"type": "string"},
                        "rewrite_rule": {"type": "string"},
                    },
                    "required": ["text", "why_it_works", "rewrite_rule"],
                    "additionalProperties": True,
                },
            },
            "content_angles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "angle": {"type": "string"},
                        "consumer_moment": {"type": "string"},
                        "product_bridge": {"type": "string"},
                    },
                    "required": ["angle", "consumer_moment", "product_bridge"],
                    "additionalProperties": True,
                },
            },
            "script_or_note_structures": {"type": "array", "items": {"type": "string"}},
            "visual_or_scene_directions": {"type": "array", "items": {"type": "string"}},
            "generation_guidance": {
                "type": "object",
                "properties": {
                    "copy_prompt_addition": {"type": "string"},
                    "image_brief_prompt_addition": {"type": "string"},
                    "video_brief_prompt_addition": {"type": "string"},
                },
                "required": ["copy_prompt_addition", "image_brief_prompt_addition", "video_brief_prompt_addition"],
                "additionalProperties": True,
            },
            "product_connection": {
                "type": "object",
                "properties": {
                    "fit_level": {"type": "string"},
                    "how_to_use": {"type": "string"},
                    "do_not_claim": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["fit_level", "how_to_use", "do_not_claim"],
                "additionalProperties": True,
            },
            "risks": {"type": "array", "items": {"type": "string"}},
            "library_card": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "reusable_rules": {"type": "array", "items": {"type": "string"}},
                    "examples_to_avoid": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "tags", "reusable_rules", "examples_to_avoid"],
                "additionalProperties": True,
            },
        },
        "required": [
            "summary_title",
            "executive_summary",
            "channel_insights",
            "hooks",
            "content_angles",
            "script_or_note_structures",
            "visual_or_scene_directions",
            "generation_guidance",
            "product_connection",
            "risks",
            "library_card",
        ],
        "additionalProperties": True,
    }

def _parse_llm_json_text(text: str) -> Dict[str, Any]:
    clean = _text(text)
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        payload = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("LLM JSON output must be an object")
    return payload

def _snapshot_items_for_llm(base: Path, snapshot_ids: List[str], max_items: int) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    snapshots: List[Dict[str, Any]] = []
    items: List[Dict[str, Any]] = []
    for snapshot_id in snapshot_ids:
        source = _resolve_snapshot(base, snapshot_id)
        snapshots.append(
            {
                "snapshot_id": source.get("snapshot_id"),
                "provider": source.get("provider"),
                "channel": source.get("channel"),
                "query": source.get("query"),
                "status": source.get("status"),
                "items_count": source.get("items_count"),
            }
        )
        for item in _list(source.get("items")):
            if len(items) >= max_items:
                break
            if not isinstance(item, dict):
                continue
            copy_analysis = item.get("copy_analysis") if isinstance(item.get("copy_analysis"), dict) else {}
            items.append(
                {
                    "snapshot_id": source.get("snapshot_id"),
                    "channel": source.get("channel"),
                    "title": _sanitize_string(item.get("title"), 220),
                    "text": _sanitize_string(item.get("text"), 1200),
                    "stats": item.get("stats") if isinstance(item.get("stats"), dict) else {},
                    "hot_score": item.get("hot_score") or item.get("hot_value") or 0,
                    "transcript_status": _text(item.get("transcript_status")),
                    "copy_analysis": {
                        "opening_hook": copy_analysis.get("opening_hook"),
                        "pain_points": copy_analysis.get("pain_points"),
                        "selling_points": copy_analysis.get("selling_points"),
                        "calls_to_action": copy_analysis.get("calls_to_action"),
                        "replicable_formula": copy_analysis.get("replicable_formula"),
                    }
                    if copy_analysis
                    else {},
                    "not_product_fact": True,
                }
            )
    return snapshots, items

def _llm_inspiration_instructions(product_name: str, channel: str, target: str, goal: str) -> str:
    return f"""
你是 product_creative 的平台灵感分析智能体，当前任务是对真实平台素材做深度灵感总结。

产品：{product_name}
渠道：{channel or "unknown"}
目标：{target or "creative_generation"}
用户目标：{goal or "从外部素材中提炼可复用创作灵感"}

严格要求：
1. 外部素材只能作为创意表达、结构、场景、钩子和节奏参考，不能当作产品事实。
2. 不要复制平台原文，不要复刻竞品承诺，不要生成未经证实的功效、销量、口味、成分、价格等事实。
3. 输出要能服务文案、图片 brief、视频 brief 三条链路。
4. 要把“为什么这个灵感有用”和“如何改写到当前产品”讲清楚。
5. 如果素材和当前产品匹配度不高，要直接指出只能作为渠道表达灵感。
6. 必须输出 JSON，不要 Markdown，不要解释 JSON 之外的文字。
7. JSON 顶层必须严格包含这些字段：
summary_title, executive_summary, channel_insights, hooks, content_angles,
script_or_note_structures, visual_or_scene_directions, generation_guidance,
product_connection, risks, library_card。

字段结构：
hooks: [{{"text": "...", "why_it_works": "...", "rewrite_rule": "..."}}]
content_angles: [{{"angle": "...", "consumer_moment": "...", "product_bridge": "..."}}]
generation_guidance: {{"copy_prompt_addition": "...", "image_brief_prompt_addition": "...", "video_brief_prompt_addition": "..."}}
product_connection: {{"fit_level": "high|medium|low|format_only", "how_to_use": "...", "do_not_claim": ["..."]}}
library_card: {{"title": "...", "tags": ["..."], "reusable_rules": ["..."], "examples_to_avoid": ["..."]}}
""".strip()

def _coerce_llm_inspiration_payload(parsed: Dict[str, Any]) -> Dict[str, Any]:
    if all(key in parsed for key in ["summary_title", "executive_summary", "generation_guidance", "library_card"]):
        return parsed
    inspiration = parsed.get("inspiration") if isinstance(parsed.get("inspiration"), dict) else {}
    copywriting = inspiration.get("copywriting") if isinstance(inspiration.get("copywriting"), dict) else {}
    image_brief = inspiration.get("image_brief") if isinstance(inspiration.get("image_brief"), dict) else {}
    video_brief = inspiration.get("video_brief") if isinstance(inspiration.get("video_brief"), dict) else {}
    format_examples = _dicts(copywriting.get("format_examples"), 3)
    hooks = []
    for item in format_examples:
        hook = _sanitize_string(item.get("hook"), 160)
        if hook:
            hooks.append(
                {
                    "text": hook,
                    "why_it_works": _sanitize_string(copywriting.get("why_useful"), 240),
                    "rewrite_rule": _sanitize_string(copywriting.get("how_to_adapt"), 260),
                }
            )
    if not hooks:
        hooks = [
            {
                "text": _sanitize_string(parsed.get("summary_title") or "平台内容用强钩子降低进入门槛", 160),
                "why_it_works": _sanitize_string(copywriting.get("why_useful") or inspiration.get("overall"), 240),
                "rewrite_rule": _sanitize_string(copywriting.get("how_to_adapt") or "把平台表达改写为当前产品的真实使用场景。", 260),
            }
        ]
    return {
        "summary_title": _sanitize_string(parsed.get("summary_title") or "LLM external platform inspiration summary", 180),
        "executive_summary": _sanitize_string(parsed.get("executive_summary") or inspiration.get("overall") or str(parsed)[:1000], 1000),
        "channel_insights": [
            item
            for item in [
                _sanitize_string(copywriting.get("why_useful"), 360),
                _sanitize_string(image_brief.get("why_useful"), 360),
                _sanitize_string(video_brief.get("why_useful"), 360),
            ]
            if item
        ],
        "hooks": hooks,
        "content_angles": [
            {
                "angle": "把平台热门表达转成当前产品的真实使用场景",
                "consumer_moment": _sanitize_string(copywriting.get("why_useful") or "用户希望快速理解并复用一个看起来简单有效的方案。", 260),
                "product_bridge": _sanitize_string(copywriting.get("how_to_adapt") or "只借鉴表达结构，不复制外部产品事实。", 300),
            }
        ],
        "script_or_note_structures": _strings(video_brief.get("structure"), 8, 260)
        or ["开场钩子 -> 场景痛点 -> 产品事实锚定 -> 步骤/体验 -> 轻 CTA"],
        "visual_or_scene_directions": _strings(image_brief.get("visual_guidelines"), 8, 260)
        or [_sanitize_string(image_brief.get("how_to_adapt") or "用清晰步骤、局部特写和轻量文字标注呈现场景。", 260)],
        "generation_guidance": {
            "copy_prompt_addition": _sanitize_string(copywriting.get("how_to_adapt") or "使用平台灵感作为表达结构，不照抄外部文案。", 500),
            "image_brief_prompt_addition": _sanitize_string(image_brief.get("how_to_adapt") or "将灵感转成产品真实场景和可视化步骤。", 500),
            "video_brief_prompt_addition": _sanitize_string(video_brief.get("how_to_adapt") or "按钩子、过程、结果、CTA 组织短视频脚本。", 500),
        },
        "product_connection": {
            "fit_level": _sanitize_string(parsed.get("match_assessment") or "format_only", 80),
            "how_to_use": "Use as channel expression and creative structure only until the user confirms it fits the real product.",
            "do_not_claim": ["Do not copy external product facts.", "Do not claim unverified ingredients, efficacy, sales, or taste."],
        },
        "risks": ["not_product_fact", "Requires user review before reusable library storage."],
        "library_card": {
            "title": "LLM summarized platform inspiration",
            "tags": ["external_inspiration"],
            "reusable_rules": [
                _sanitize_string(copywriting.get("how_to_adapt") or "Borrow the structure, rewrite around Product Brain facts.", 260),
                "Keep external claims out of Product Brain unless separately verified.",
            ],
            "examples_to_avoid": ["Do not reproduce platform text verbatim."],
        },
    }

def _llm_pack_brief_context(parsed: Dict[str, Any]) -> str:
    lines = []
    summary = _sanitize_string(parsed.get("executive_summary"), 600)
    if summary:
        lines.append(f"LLM summary: {summary}")
    for hook in _dicts(parsed.get("hooks"), 4):
        text = _sanitize_string(hook.get("text"), 160)
        rule = _sanitize_string(hook.get("rewrite_rule"), 240)
        if text or rule:
            lines.append(f"Hook pattern: {text} -> {rule}")
    for angle in _dicts(parsed.get("content_angles"), 4):
        name = _sanitize_string(angle.get("angle"), 180)
        bridge = _sanitize_string(angle.get("product_bridge"), 260)
        if name or bridge:
            lines.append(f"Angle: {name}. Product bridge: {bridge}")
    guidance = parsed.get("generation_guidance") if isinstance(parsed.get("generation_guidance"), dict) else {}
    for key in ["copy_prompt_addition", "image_brief_prompt_addition", "video_brief_prompt_addition"]:
        value = _sanitize_string(guidance.get(key), 360)
        if value:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)

def _llm_pack_markdown(pack: Dict[str, Any]) -> str:
    parsed = pack.get("llm_summary") if isinstance(pack.get("llm_summary"), dict) else {}
    lines = [
        f"# {pack['pack_id']}",
        "",
        f"Status: {pack.get('status', '')}",
        f"Status reason: {pack.get('status_reason', '')}",
        f"Channel: {pack.get('channel', '')}",
        f"Target: {pack.get('target', '')}",
        f"Goal: {pack.get('goal', '')}",
        f"LLM call mode: {(pack.get('llm') or {}).get('call_mode', '') if isinstance(pack.get('llm'), dict) else ''}",
        f"Requires confirmation: {pack.get('requires_user_confirmation_for_library', True)}",
        "",
        "## Summary",
        "",
        _sanitize_string(parsed.get("executive_summary"), 1200),
        "",
        "## Channel Insights",
        "",
    ]
    lines.extend([f"- {item}" for item in _strings(parsed.get("channel_insights"), 8, 400)] or ["- None"])
    lines.extend(["", "## Hooks", ""])
    for item in _dicts(parsed.get("hooks"), 8):
        lines.append(f"- {item.get('text', '')}: {item.get('why_it_works', '')} / {item.get('rewrite_rule', '')}")
    if not _dicts(parsed.get("hooks"), 8):
        lines.append("- None")
    lines.extend(["", "## Content Angles", ""])
    for item in _dicts(parsed.get("content_angles"), 8):
        lines.append(f"- {item.get('angle', '')}: {item.get('consumer_moment', '')} / {item.get('product_bridge', '')}")
    if not _dicts(parsed.get("content_angles"), 8):
        lines.append("- None")
    lines.extend(["", "## Structures", ""])
    lines.extend([f"- {item}" for item in _strings(parsed.get("script_or_note_structures"), 8, 500)] or ["- None"])
    lines.extend(["", "## Visual Or Scene Directions", ""])
    lines.extend([f"- {item}" for item in _strings(parsed.get("visual_or_scene_directions"), 8, 500)] or ["- None"])
    lines.extend(["", "## Product Connection", ""])
    product_connection = parsed.get("product_connection") if isinstance(parsed.get("product_connection"), dict) else {}
    lines.append(f"Fit: {product_connection.get('fit_level', '')}")
    lines.append(f"How to use: {product_connection.get('how_to_use', '')}")
    lines.extend(["", "## Risks", ""])
    lines.extend([f"- {item}" for item in _strings(parsed.get("risks"), 8, 500)] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def create_llm_inspiration_pack(
    product_id: str,
    snapshots: List[str] | None = None,
    goal: str = "",
    target: str = "",
    channel: str = "",
    max_items: int = 8,
    provider: str = "",
    model: str = "",
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    if os.environ.get("PRODUCT_CREATIVE_ENABLE_LLM") != "1" or _LLM is None:
        return {
            "success": False,
            "schema_version": LLM_INSPIRATION_PACK_SCHEMA_VERSION,
            "product_id": base.name,
            "status": "blocked",
            "blocker": "llm_not_configured",
            "message": "This command must run inside Hermes Agent/plugin runtime so ctx.llm can use the active DeepSeek model.",
            "mutates_product_brain": False,
        }

    snapshot_ids = [str(item).strip() for item in (snapshots or []) if str(item).strip()]
    if not snapshot_ids:
        latest = []
        for payload in artifacts().list(base.name, "external_source_snapshots"):
            if channel and payload.get("channel") != channel:
                continue
            latest.append(payload)
        latest.sort(key=lambda item: _text(item.get("created_at")), reverse=True)
        snapshot_ids = [_text(item.get("snapshot_id")) for item in latest[:2] if _text(item.get("snapshot_id"))]
    if not snapshot_ids:
        raise FileNotFoundError("No source snapshots were provided or found for LLM inspiration summarization.")

    state = read_product_state(base)
    product_name = _text(state.get("name")) or base.name
    snapshots_meta, items = _snapshot_items_for_llm(base, snapshot_ids, _safe_limit(max_items, 8, 20))
    if not items:
        raise ValueError("Selected snapshots contain no source items.")
    clean_channel = _text(channel) or _text(snapshots_meta[0].get("channel"))
    clean_target = _text(target) or ("xiaohongshu-seeding-note" if clean_channel == "xiaohongshu" else "douyin-short-video-script" if clean_channel == "douyin" else "")
    clean_goal = _text(goal) or f"{clean_channel or 'external'} LLM inspiration summary"
    llm_input = {
        "product": {
            "product_id": base.name,
            "name": product_name,
            "selling_points": _list(state.get("selling_points"))[:8],
            "positioning": state.get("positioning") or state.get("description") or "",
        },
        "snapshots": snapshots_meta,
        "source_items": items,
        "target": clean_target,
        "channel": clean_channel,
        "goal": clean_goal,
        "source_policy": {
            "external_sources_are_not_product_facts": True,
            "must_require_user_confirmation_before_library_write": True,
        },
    }
    instructions = _llm_inspiration_instructions(product_name, clean_channel, clean_target, clean_goal)
    input_text = json.dumps(llm_input, ensure_ascii=False)
    try:
        result = _LLM.complete_structured(
            instructions=instructions,
            input=[{"type": "text", "text": input_text}],
            json_mode=True,
            temperature=0.2,
            max_tokens=4000,
            timeout=180,
            provider=_text(provider) or None,
            model=_text(model) or None,
            purpose="product_creative.llm_inspiration_pack",
        )
        parsed = result.parsed if isinstance(result.parsed, dict) else _parse_llm_json_text(result.text)
        parsed = _coerce_llm_inspiration_payload(parsed)
        content_type = result.content_type
        call_mode = "structured_json_mode"
    except Exception as exc:
        if "response_format" not in str(exc) and "json_object" not in str(exc):
            raise
        result = _LLM.complete(
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
            temperature=0.2,
            max_tokens=4000,
            timeout=180,
            provider=_text(provider) or None,
            model=_text(model) or None,
            purpose="product_creative.llm_inspiration_pack.text_json_fallback",
        )
        parsed = _coerce_llm_inspiration_payload(_parse_llm_json_text(result.text))
        content_type = "json_text_fallback"
        call_mode = "text_json_fallback"
    pack_id = f"llm-inspiration-pack-{timestamp()}"
    pack = {
        "schema_version": LLM_INSPIRATION_PACK_SCHEMA_VERSION,
        "pack_id": pack_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "review_required",
        "status_reason": "user_review_required_before_library_write",
        "summary_type": "llm_deep_inspiration_summary",
        "goal": clean_goal,
        "target": clean_target,
        "channel": clean_channel,
        "source_snapshot_ids": snapshot_ids,
        "source_item_count": len(items),
        "llm_summary": parsed,
        "brief_context": _llm_pack_brief_context(parsed),
        "llm": {
            "provider": result.provider,
            "model": result.model,
            "agent_id": result.agent_id,
            "usage": _usage_payload(result.usage),
            "content_type": content_type,
            "call_mode": call_mode,
        },
        "review_contract": {
            "must_be_reviewed_by_user": True,
            "may_be_written_to_inspiration_library_after_confirmation": True,
            "external_sources_are_not_product_facts": True,
            "does_not_update_product_brain": True,
        },
        "requires_user_confirmation_for_library": True,
        "confirmation_status": "pending",
        "not_product_fact": True,
        "mutates_product_brain": False,
    }
    out_dir = base / "artifacts" / "llm_inspiration_packs"
    json_path = out_dir / f"{pack_id}.json"
    md_path = out_dir / f"{pack_id}.md"
    write_json(json_path, pack)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_llm_pack_markdown(pack), encoding="utf-8")
    append_jsonl(
        base / "structured" / "llm_inspiration_pack_index.jsonl",
        {
            "pack_id": pack_id,
            "created_at": pack["created_at"],
            "status": pack["status"],
            "target": pack["target"],
            "channel": pack["channel"],
            "source_item_count": len(items),
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(
        base,
        "llm-inspiration-pack",
        pack_id,
        [f"Status: {pack['status']}", f"Channel: {clean_channel}", f"Items: {len(items)}", f"Model: {result.provider}/{result.model}"],
    )
    return {
        "success": True,
        "schema_version": LLM_INSPIRATION_PACK_SCHEMA_VERSION,
        "product_id": base.name,
        "pack_id": pack_id,
        "status": pack["status"],
        "requires_user_confirmation_for_library": True,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "llm": pack["llm"],
        "llm_inspiration_pack": pack,
    }

def _resolve_llm_pack(base: Path, value: str) -> Dict[str, Any]:
    clean = _text(value)
    path = base / "artifacts" / "llm_inspiration_packs" / f"{clean}.json"
    if path.exists():
        return read_json(path, {})
    candidate = Path(clean)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("LLM inspiration pack path must stay inside the product workspace")
        return read_json(resolved, {})
    raise FileNotFoundError(f"LLM inspiration pack '{value}' does not exist")
