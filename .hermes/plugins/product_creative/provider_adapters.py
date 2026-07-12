"""Provider prompt adapters and request builders for Product Creative."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .capabilities.material.resolver_service import resolve_material_execution_input


PROMPT_ADAPTER_SCHEMA_VERSION = "product_creative.prompt_adapter.v0.6.5"
VIDEO_PROMPT_ADAPTER_SCHEMA_VERSION = "product_creative.video_prompt_adapter.v2.20"

__all__ = [
    "PROMPT_ADAPTER_SCHEMA_VERSION",
    "VIDEO_PROMPT_ADAPTER_SCHEMA_VERSION",
    "adapt_image_prompt",
    "adapt_video_prompt",
    "duration_seconds",
    "image_request",
    "is_data_url",
    "is_http_url",
    "video_reference_url",
    "video_request",
]


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def adapt_image_prompt(
    brief: Dict[str, Any],
    provider: Dict[str, Any],
    product_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    contract = brief.get("generation_contract") or {}
    target = brief.get("target") or {}
    state = product_state or {}
    learning = state.get("learning") or {}
    style_preferences = state.get("style_preferences") or {}
    source_prompt = _text(contract.get("prompt"))
    provider_name = provider.get("name", "generic")
    rules = [
        "Keep all product facts grounded in Product State and source brief.",
        "Do not invent packaging, certifications, medical effects, awards, or unavailable product details.",
        "Preserve the requested canvas/aspect direction when possible.",
        "Use realistic product photography and a clean, commercially usable composition.",
        "Avoid relying on generated text inside the image; text overlays should be rendered later by design tooling.",
        "Use applied Product Brain learning when available.",
    ]
    aspect_ratio = _text(target.get("default_aspect_ratio")) or "1:1"
    preference_lines = []
    visual_tone = _text(style_preferences.get("visual_tone"))
    promotion_intensity = _text(style_preferences.get("promotion_intensity"))
    if visual_tone:
        preference_lines.append(f"已确认视觉偏好：{visual_tone}。")
    if promotion_intensity:
        preference_lines.append(f"促销强度偏好：{promotion_intensity}。")
    for item in _list(learning.get("image_generation_preferences"))[-3:]:
        if str(item).strip():
            preference_lines.append(f"图片生成偏好：{item}")
    for item in _list(learning.get("successful_patterns"))[-3:]:
        if str(item).strip():
            preference_lines.append(f"历史成功模式：{item}")
    for item in _list(learning.get("failed_patterns"))[-3:]:
        if str(item).strip():
            preference_lines.append(f"需要避免的历史失败模式：{item}")

    adapted_prompt = source_prompt
    if provider_name in {"volcengine-ark-image", "generic-http-image"}:
        adapted_prompt = "\n".join(
            item for item in [
                source_prompt,
                f"画面比例/构图方向：{aspect_ratio}。",
                "真实产品摄影质感，主体清晰，背景干净，电商可用。",
                "不要虚构产品包装、认证、医疗功效、奖项或未在产品资料中出现的信息。",
                "不要把主标题和卖点文字直接生成在图片内，文字留给后期版式叠加。",
                *preference_lines,
            ] if item
        )
    return {
        "schema_version": PROMPT_ADAPTER_SCHEMA_VERSION,
        "status": "adapted",
        "provider": provider_name,
        "adapter": provider.get("adapter", "generic"),
        "source": "image_brief.generation_contract.prompt",
        "source_prompt": source_prompt,
        "adapted_prompt": adapted_prompt,
        "rules": rules,
        "learning_snapshot": {
            "visual_tone": visual_tone,
            "promotion_intensity": promotion_intensity,
            "image_generation_preferences": _list(learning.get("image_generation_preferences"))[-3:],
            "successful_patterns": _list(learning.get("successful_patterns"))[-3:],
            "failed_patterns": _list(learning.get("failed_patterns"))[-3:],
        },
        "notes": [
            "M0.6.9 keeps prompt adaptation deterministic and grounded in applied Product Brain learning.",
            "Future versions should optimize prompt adapters per provider after collecting result feedback.",
        ],
    }


def image_request(
    brief: Dict[str, Any],
    provider: Dict[str, Any],
    product_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    visual = brief.get("visual") or {}
    contract = brief.get("generation_contract") or {}
    copy = brief.get("copy") or {}
    adapter = adapt_image_prompt(brief, provider, product_state)
    return {
        "prompt": adapter["adapted_prompt"],
        "base_prompt": _text(contract.get("prompt")),
        "prompt_adapter": adapter,
        "negative_prompt": "\n".join(str(item) for item in _list(visual.get("negative_constraints"))),
        "aspect_ratio": brief.get("target", {}).get("default_aspect_ratio", "1:1"),
        "text_to_render": _list(copy.get("text_to_render")),
        "reference_assets": _list(brief.get("source_assets")),
        "must_preserve": _list(contract.get("must_preserve")),
        "must_not_invent": _list(contract.get("must_not_invent")),
    }


def duration_seconds(value: str) -> int:
    numbers = [int(item) for item in re.findall(r"\d+", value or "")]
    if numbers:
        return max(1, numbers[-1])
    return 10


def is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def is_data_url(value: str) -> bool:
    return value.startswith("data:")


def video_reference_url(asset: Dict[str, Any]) -> str:
    for key in ["remote_url", "url", "source", "stored"]:
        value = _text(asset.get(key))
        if is_http_url(value):
            return value
    for item in _list(asset.get("remote_urls")):
        if isinstance(item, dict):
            value = _text(item.get("url"))
            if is_http_url(value):
                return value
    return ""


def _asset_local_reference(asset: Dict[str, Any]) -> str:
    return _text(asset.get("stored")) or _text(asset.get("source")) or _text(asset.get("asset_id"))


def adapt_video_prompt(
    brief: Dict[str, Any],
    provider: Dict[str, Any],
    product_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    story = brief.get("story") or {}
    contract = brief.get("generation_contract") or {}
    state = product_state or {}
    learning = state.get("learning") or {}
    target = brief.get("target") or {}
    source_prompt = _text(contract.get("prompt"))
    provider_name = provider.get("name", "generic")
    aspect_ratio = _text(target.get("default_aspect_ratio")) or "9:16"
    duration = duration_seconds(_text(story.get("estimated_duration")))
    reference_assets = _list(brief.get("source_assets"))
    lines = [source_prompt]
    if provider.get("adapter") == "async-video-task":
        lines.extend(
            [
                f"视频比例：{aspect_ratio}。",
                f"建议时长：约 {duration} 秒。",
                "如使用参考图，必须保持产品主体、包装外观和画面核心识别一致。",
                "镜头按分镜顺序推进，不要新增未确认的包装文字、认证、产地、功效或奖项。",
                "默认不生成复杂旁白；如生成声音，口播只复述 brief 中已给出的产品事实和字幕。",
            ]
        )
    for item in _list(learning.get("successful_patterns"))[-2:]:
        if str(item).strip():
            lines.append(f"历史成功模式：{item}")
    video_preferences = _list(learning.get("video_script_preferences")) or _list(learning.get("video_generation_preferences"))
    for item in video_preferences[-3:]:
        if str(item).strip():
            lines.append(f"视频脚本偏好：{item}")
    for item in _list(learning.get("failed_patterns"))[-2:]:
        if str(item).strip():
            lines.append(f"需要避免的历史失败模式：{item}")
    return {
        "schema_version": VIDEO_PROMPT_ADAPTER_SCHEMA_VERSION,
        "status": "adapted" if provider.get("adapter") == "async-video-task" else "direct_mapping",
        "provider": provider_name,
        "adapter": provider.get("adapter", "generic"),
        "source": "video_brief.generation_contract.prompt",
        "source_prompt": source_prompt,
        "adapted_prompt": "\n".join(item for item in lines if item),
        "aspect_ratio": aspect_ratio,
        "duration_seconds": duration,
        "reference_asset_count": len(reference_assets),
        "rules": [
            "Keep all product facts grounded in Product State and video brief.",
            "Use selected material assets only as references through provider-ready handles.",
            "Do not invent packaging text, certifications, awards, origin details, or medical/functional claims.",
            "Require human review before live video task creation.",
        ],
    }


def _ark_video_content(
    product_id: str,
    provider_name: str,
    prompt: str,
    reference_assets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    unresolved = []
    execution_inputs = []
    for asset in reference_assets:
        resolved = resolve_material_execution_input(
            product_id,
            asset,
            provider=provider_name,
            role="reference_image",
            usage="video_provider_payload",
            persist=True,
        )
        if resolved.get("ready_for_provider") and _text(resolved.get("provider_value")):
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": resolved["provider_value"]},
                    "role": "reference_image",
                }
            )
            execution_inputs.append(
                {
                    "asset_id": _text(asset.get("asset_id")) or _text(asset.get("material_id")),
                    "execution_input_id": resolved.get("execution_input_id", ""),
                    "input_kind": resolved.get("input_kind", ""),
                    "value_ref": resolved.get("value_ref", ""),
                }
            )
            continue
        unresolved.append(
            {
                "asset_id": _text(asset.get("asset_id")),
                "role": _text(asset.get("role")),
                "local_reference": _asset_local_reference(asset),
                "required_provider_input": "image_url",
                "required_role": "reference_image",
                "reason": "; ".join(_list(resolved.get("blockers"))) or "MaterialResolver could not prepare a provider input.",
            }
        )
        placeholder = f"<public-url-for-{_text(asset.get('asset_id')) or 'reference-image'}>"
        content.append({"type": "image_url", "image_url": {"url": placeholder}, "role": "reference_image"})
    return {"content": content, "unresolved_reference_assets": unresolved, "material_execution_inputs": execution_inputs}


def _ark_video_request_draft(
    brief: Dict[str, Any],
    provider: Dict[str, Any],
    adapter: Dict[str, Any],
    reference_assets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    defaults = provider.get("request_defaults") or {}
    content_bundle = _ark_video_content(brief.get("product_id", ""), provider.get("name", "generic"), adapter["adapted_prompt"], reference_assets)
    ratio = _text(defaults.get("ratio")) or adapter["aspect_ratio"]
    duration = int(defaults.get("duration") or adapter["duration_seconds"])
    body = {
        "model": provider.get("model") or f"env:{provider.get('model_env')}",
        "content": content_bundle["content"],
        "generate_audio": bool(defaults.get("generate_audio", False)),
        "ratio": ratio,
        "duration": duration,
        "watermark": bool(defaults.get("watermark", False)),
    }
    unresolved = content_bundle["unresolved_reference_assets"]
    return {
        "schema_version": "product_creative.ark_video_task_payload.v2.20",
        "api_family": "volcengine_ark_contents_generations_tasks",
        "method": "POST",
        "endpoint": provider.get("endpoint") or f"env:{provider.get('endpoint_env')}",
        "auth": "bearer_env" if provider.get("auth_env") else "none",
        "body": body,
        "body_ready_for_live": len(unresolved) == 0,
        "unresolved_reference_assets": unresolved,
        "material_execution_inputs": content_bundle.get("material_execution_inputs", []),
        "upload_requirements": [
            "Local product images may be passed through MaterialResolver when the provider accepts data URLs.",
            "Reference asset roles should remain reference_image unless the provider-specific flow says otherwise.",
        ],
    }


def video_request(
    brief: Dict[str, Any],
    provider: Dict[str, Any],
    product_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    story = brief.get("story") or {}
    contract = brief.get("generation_contract") or {}
    adapter = adapt_video_prompt(brief, provider, product_state)
    reference_assets = _list(brief.get("source_assets"))
    request = {
        "prompt": adapter["adapted_prompt"],
        "base_prompt": _text(contract.get("prompt")),
        "prompt_adapter": adapter,
        "aspect_ratio": brief.get("target", {}).get("default_aspect_ratio", "9:16"),
        "estimated_duration": _text(story.get("estimated_duration")),
        "duration_seconds": adapter["duration_seconds"],
        "pacing": _text(story.get("pacing")),
        "audio_plan": _list(story.get("audio_plan")),
        "caption_plan": _text(story.get("caption_plan")),
        "editing_rules": _list(story.get("editing_rules")),
        "storyboard": _list(story.get("storyboard")),
        "reference_assets": reference_assets,
        "must_preserve": _list(contract.get("must_preserve")),
        "must_not_invent": _list(contract.get("must_not_invent")),
    }
    if provider.get("adapter") == "async-video-task":
        request["provider_request_draft"] = _ark_video_request_draft(brief, provider, adapter, reference_assets)
    return request


