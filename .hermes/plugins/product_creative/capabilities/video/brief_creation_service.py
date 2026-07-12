"""Video brief creation service."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state, generation_safe_list
from ..inspiration.library_service import latest_inspiration_context
from ..material.pack_service import record_material_usage

from .brief_shared import _find_artifact_by_id, _list, _rel, _resolve_artifact, _state_hash, _text

VIDEO_BRIEF_SCHEMA_VERSION = "product_creative.video_brief.v2.18"

def _target(platform: str) -> Dict[str, Any]:
    clean = _text(platform) or "douyin"
    labels = {
        "douyin": "Douyin short video",
        "xiaohongshu": "Xiaohongshu video note",
        "ecommerce": "Commerce product video",
    }
    return {
        "platform": clean,
        "channel": clean,
        "asset_type": "image_to_video_storyboard",
        "default_aspect_ratio": "9:16",
        "estimated_duration_seconds": 10,
        "canvas_hint": labels.get(clean, "Short product video"),
        "provider_agnostic": True,
    }

def _selling_points(state: Dict[str, Any]) -> List[str]:
    safe = state.get("generation_safe") if isinstance(state.get("generation_safe"), dict) else {}
    safe_points = generation_safe_list(safe.get("selling_points"), limit=5, max_chars=80)
    if safe_points:
        return safe_points
    if isinstance(state.get("generation_safe"), dict):
        return []
    points = [str(item).strip() for item in _list(state.get("selling_points")) if str(item).strip()]
    return generation_safe_list(points, limit=5, max_chars=80) or points[:5]

def _theme(intent: Dict[str, Any]) -> str:
    hint = _text((intent.get("intent") or {}).get("theme_hint"))
    if hint and hint != "today_theme_required":
        return hint
    intent_type = _text((intent.get("intent") or {}).get("type"))
    if intent_type == "today_video":
        return "今日产品内容"
    return "产品短视频"

def _caption(value: str, fallback: str) -> str:
    text = _text(value) or fallback
    return text[:18]

def _set_provider_prompt_segment(shot: Dict[str, Any]) -> None:
    shot["provider_prompt_segment"] = (
        f"镜头{shot.get('shot')}（{shot.get('duration')}）：{shot.get('scene')}。"
        f"动作：{shot.get('action')} 机位：{shot.get('camera')}。"
        f"镜头运动：{shot.get('motion')}。构图：{shot.get('composition')}。"
        f"产品要求：{shot.get('product_visibility')}。字幕：{shot.get('caption')}。"
        f"声音：{shot.get('audio')}。转场：{shot.get('transition')}。"
        f"避免：{shot.get('negative_prompt')}。"
    )

def _source_assets(base: Path, intent: Dict[str, Any], material: Dict[str, Any]) -> List[Dict[str, Any]]:
    selected = intent.get("selected_material") if isinstance(intent.get("selected_material"), dict) else {}
    stored = _text(material.get("stored_path")) or _text(selected.get("stored_path"))
    source = _text(material.get("source_path"))
    remote_url = _text(material.get("remote_url"))
    return [
        {
            "asset_id": _text(material.get("material_id")) or _text(selected.get("material_id")),
            "role": _text(material.get("role")) or _text(selected.get("role")),
            "source": source,
            "stored": stored,
            "remote_url": remote_url,
            "remote_urls": _list(material.get("remote_urls")),
            "material_card_id": _text(selected.get("material_card_id")),
            "task_material_pack_id": _text(selected.get("task_material_pack_id")),
            "missing": not bool(stored and (base / stored).exists()),
            "description": _text(material.get("description")) or "Selected product material for image-to-video generation.",
            "use_as": "first_frame_or_reference_image",
        }
    ]

def _storyboard(product_name: str, theme: str, selling_points: List[str], material_role: str, platform: str) -> List[Dict[str, Any]]:
    point_1 = selling_points[0] if selling_points else "核心卖点"
    point_2 = selling_points[1] if len(selling_points) > 1 else point_1
    point_3 = selling_points[2] if len(selling_points) > 2 else point_2
    platform_hint = "抖音" if platform == "douyin" else "小红书" if platform == "xiaohongshu" else "电商"
    reference = f"用户已选{material_role or '产品图'}"
    shots = [
        {
            "shot": 1,
            "duration": "0-1.5s",
            "purpose": "3秒内建立产品识别和观看理由",
            "scene": "干净明亮的近景产品开场，背景保持低干扰",
            "action": f"以{reference}作为首帧参考，产品主体先静止清晰出现，再做轻微推进。",
            "camera": "竖屏近景，镜头轻微 push-in",
            "motion": "主体稳定，背景轻微景深变化，避免快速乱切",
            "composition": "产品居中略偏上，保留底部字幕空间",
            "product_visibility": "产品主体全程清晰可见，不遮挡包装/轮廓",
            "lighting": "自然清爽高光，避免过暗或强促销色",
            "transition": "干净切入到卖点近景",
            "audio": "轻快开场音效，可有清脆开瓶/入杯声",
            "caption": _caption(f"{product_name}｜{theme}", product_name),
            "visual_prompt": f"{product_name}，参考首帧，主体清晰，真实产品质感，竖屏近景",
            "negative_prompt": "不要改变产品主体，不要新增包装文字，不要出现无关品牌",
            "key_message": "产品识别",
            "reference_usage": "first_frame_or_primary_reference",
        },
        {
            "shot": 2,
            "duration": "1.5-3.5s",
            "purpose": "把核心卖点转成可见动作",
            "scene": "产品细节近景或使用前准备场景",
            "action": f"围绕“{point_1}”设计一个可视化动作，例如打开、倒出、拿起、靠近镜头展示；只表达已确认卖点。",
            "camera": "近景/特写，镜头稳定跟随动作",
            "motion": "动作干净利落，节奏贴合短视频前段",
            "composition": "手部或道具不遮挡产品主体，卖点动作占画面中心",
            "product_visibility": "每个动作结束时回到产品清晰可识别画面",
            "lighting": "保留真实质感，不使用夸张滤镜",
            "transition": "用动作方向自然转场到使用场景",
            "audio": "匹配动作的轻声效，旁白可只说卖点短句",
            "caption": _caption(point_1, "核心卖点"),
            "visual_prompt": f"{product_name}，近景动作，突出 {point_1}，真实自然",
            "negative_prompt": "不要把卖点夸大成功效，不要生成未确认认证或奖项",
            "key_message": point_1,
            "reference_usage": "visual_consistency",
        },
        {
            "shot": 3,
            "duration": "3.5-6.5s",
            "purpose": "把产品带入用户场景，形成代入感",
            "scene": f"{platform_hint}适合的真实使用/消费场景，画面生活化但不杂乱",
            "action": f"展示用户拿起、使用或享用产品，表达“{point_2}”；如同时出现“{point_3}”，只作为感受补充。",
            "camera": "中近景切到手持/桌面场景",
            "motion": "轻微横移或跟随，保持主体稳定",
            "composition": "产品、手部、场景三者关系清楚，背景只辅助氛围",
            "product_visibility": "产品至少在镜头前半段和结尾各清晰出现一次",
            "lighting": "自然日光或柔和室内光，保持可信",
            "transition": "用场景动作转到收尾定格",
            "audio": "环境音轻，旁白避免复杂长句",
            "caption": _caption(point_2 if point_2 == point_3 else f"{point_2}，{point_3}", point_2),
            "visual_prompt": f"{product_name}，真实使用场景，{point_2}，{point_3}，生活化",
            "negative_prompt": "不要出现与产品不匹配的人群、场景或过度广告牌",
            "key_message": point_2,
            "reference_usage": "product_identity_lock",
        },
        {
            "shot": 4,
            "duration": "6.5-8.5s",
            "purpose": "强化记忆点并给出轻行动引导",
            "scene": "回到产品主体和一个干净的使用后状态",
            "action": "产品回到画面中心，做短暂停顿或轻微举起，形成可截图的尾帧。",
            "camera": "近景定格，轻微拉近",
            "motion": "动作收住，不再新增复杂信息",
            "composition": "产品主体清晰，字幕不压住主体",
            "product_visibility": "尾帧产品清晰完整",
            "lighting": "清爽干净，保留质感",
            "transition": "尾帧停留，适合平台封面截取",
            "audio": "音乐收束，可保留轻口播",
            "caption": "今天就试试这一口",
            "visual_prompt": f"{product_name}，产品主体定格，清晰干净，短视频尾帧",
            "negative_prompt": "不要新增价格、功效承诺或夸张促销文案",
            "key_message": "行动引导",
            "reference_usage": "final_identity_frame",
        },
    ]
    for shot in shots:
        _set_provider_prompt_segment(shot)
    return shots

def _non_use_storyboard(product_name: str, theme: str) -> List[Dict[str, Any]]:
    shots = [
        {
            "shot": 1,
            "duration": "0-2s",
            "purpose": "从可信产品参考图建立品牌识别",
            "scene": "黄色半透明云朵/花朵产品包装保持未打开，置于温暖明亮的桌面",
            "action": "产品静止清晰出现，只做轻微镜头推进，不改变包装结构或文字",
            "camera": "9:16 竖屏产品近景",
            "motion": "缓慢 push-in，主体稳定",
            "composition": "产品位于下方三分之一，保留上方暖色留白",
            "product_visibility": "使用已登记参考图锁定包装身份，产品完整可见",
            "lighting": "自然暖光，真实商业摄影",
            "transition": "柔和光影溶解到人物场景",
            "audio": "轻柔器乐与自然室内环境音，无功效口播",
            "caption": _caption(product_name, product_name),
            "visual_prompt": "可信产品参考图，未打开的黄色半透明云朵/花朵包装，暖光桌面",
            "negative_prompt": "不要打开产品，不要改变包装，不要新增包装文字，不要展示使用",
            "key_message": "产品识别",
            "reference_usage": "first_frame_or_primary_reference",
        },
        {
            "shot": 2,
            "duration": "2-5s",
            "purpose": "尊重地看见成年孕妇这一女性身份",
            "scene": "约30岁的成年孕妇在窗边自然站立，神态平静自信，桌面远处可见未打开产品",
            "action": "她轻抚腹部后望向窗外，不触碰、不拿取、不使用产品",
            "camera": "中景侧面轮廓，人物主体完整自然",
            "motion": "缓慢横移，动作克制",
            "composition": "人物为主体，产品是小比例礼物场景元素",
            "product_visibility": "产品保持未打开且不与身体或使用动作建立因果关系",
            "lighting": "温暖窗光，不病态化、不幼态化",
            "transition": "人物转身动作衔接女性群像",
            "audio": "轻柔器乐，无医疗或孕期安全旁白",
            "caption": "每一种女性身份",
            "visual_prompt": "成年孕妇，尊重、自信、温暖窗光，产品只作远处未打开礼物元素",
            "negative_prompt": "不要展示产品使用、饮用或打开，不要暗示孕期适用、安全或健康功效",
            "key_message": "看见女性身份",
            "reference_usage": "background_product_identity",
        },
        {
            "shot": 3,
            "duration": "5-8s",
            "purpose": "扩展到不同女性身份的平等群像",
            "scene": "不同年龄与职业气质的成年女性自然相聚，孕妇作为平等成员处于群像中",
            "action": "女性们自然对视微笑，桌面产品保持未打开，无人拿取",
            "camera": "竖屏中广角群像",
            "motion": "轻微环绕，稳定真实",
            "composition": "人物关系清楚，产品小比例位于前景桌面",
            "product_visibility": "产品仅作为礼物静物，不展示使用",
            "lighting": "现代、明亮、克制的商业摄影",
            "transition": "花束前景擦过镜头进入收尾",
            "audio": "音乐稍抬升，无促销口播",
            "caption": "都值得被看见",
            "visual_prompt": "多元成年女性群像，孕妇自然融入，未打开产品静置前景",
            "negative_prompt": "不要医疗化、标签化或刻板化，不要展示产品使用",
            "key_message": theme,
            "reference_usage": "visual_consistency",
        },
        {
            "shot": 4,
            "duration": "8-10s",
            "purpose": "以妇女节主题和产品礼物静物收束",
            "scene": "回到未打开产品与淡粉花束的桌面，背景保留孕妇温柔轮廓",
            "action": "镜头轻微拉近后定格，产品与人物无使用互动",
            "camera": "产品近景与人物轮廓同框",
            "motion": "轻微拉近并停留",
            "composition": "产品清晰但不夸大，人物轮廓表达陪伴与尊重",
            "product_visibility": "包装依据参考图，不新增或改写包装文字",
            "lighting": "暖光收束，保留真实质感",
            "transition": "自然淡出",
            "audio": "音乐温柔收束",
            "caption": "妇女节，看见她",
            "visual_prompt": "未打开产品礼物静物，花束，成年孕妇温柔轮廓，9:16 收尾",
            "negative_prompt": "不要功效、医疗、通便、营养、孕期适用或安全承诺",
            "key_message": "妇女节，看见她",
            "reference_usage": "final_identity_frame",
        },
    ]
    for shot in shots:
        _set_provider_prompt_segment(shot)
    return shots

def _prompt(
    product_name: str,
    theme: str,
    platform: str,
    storyboard: List[Dict[str, Any]],
    source_assets: List[Dict[str, Any]],
    state: Dict[str, Any],
    inspiration_context: Dict[str, Any] | None = None,
) -> str:
    style = state.get("style_preferences") or {}
    learning = state.get("learning") or {}
    lines = [
        f"你是一名短视频导演，请生成一条围绕「{product_name}」的{platform}图生视频短片。",
        f"主题：{theme}。",
        "首帧/参考图：使用用户选择的参考图作为首帧或主要视觉参考，保持产品主体、包装外观和画面核心识别一致。",
        "画幅：9:16。",
        "整体要求：真实自然、信息清晰、节奏紧凑，每个镜头都服务于产品识别或卖点表达。",
        "生成重点：严格按下面分镜执行，优先保证镜头动作、机位、节奏和产品可见性。",
    ]
    visual_tone = _text(style.get("visual_tone"))
    promotion = _text(style.get("promotion_intensity"))
    if visual_tone:
        lines.append(f"视觉风格偏好：{visual_tone}。")
    if promotion:
        lines.append(f"促销强度偏好：{promotion}。")
    for item in _list(learning.get("image_generation_preferences"))[-2:]:
        if str(item).strip():
            lines.append(f"已确认视觉偏好：{item}")
    video_preferences = _list(learning.get("video_script_preferences")) or _list(learning.get("video_generation_preferences"))
    for item in video_preferences[-2:]:
        if str(item).strip():
            lines.append(f"已确认视频脚本偏好：{item}")
    for item in _list(learning.get("material_preferences"))[-2:]:
        if str(item).strip():
            lines.append(f"已确认素材偏好：{item}")
    if source_assets:
        lines.append(f"参考素材：{source_assets[0].get('remote_url') or source_assets[0].get('stored') or source_assets[0].get('source')}。")
    inspiration = inspiration_context if isinstance(inspiration_context, dict) else {}
    if inspiration.get("available"):
        lines.append("外部灵感上下文：以下内容只可作为表达角度、题材和钩子参考，不得当成产品事实。")
        for item in _list(inspiration.get("items"))[:3]:
            if not isinstance(item, dict):
                continue
            summary = _text(item.get("summary"))
            if summary:
                lines.append(f"- {summary}")
    lines.append("镜头分镜（必须按顺序执行）：")
    for shot in storyboard:
        lines.append(shot.get("provider_prompt_segment") or "")
    lines.append("字幕策略：字幕短、清晰，只使用 brief 中给出的 caption，不额外生成长段文字。")
    lines.append("音频策略：默认生成轻快背景音和真实动作声；如有口播，只复述已确认产品事实。")
    lines.append("限制：不得虚构包装、配料、认证、奖项、医学功效或未在 Product Brain 中确认的细节。")
    lines.append("限制：不要让无关人物、无关品牌、夸张促销背景抢占产品主体。")
    return "\n".join(lines)

def _brief_markdown(brief: Dict[str, Any]) -> str:
    lines = [
        f"# {brief['brief_id']}",
        "",
        f"Product: {brief['product_id']}",
        f"Source intent: {brief['source_intent_id']}",
        f"Platform: {brief['target']['platform']}",
        f"Status: {brief['status']}",
        f"Aspect ratio: {brief['target']['default_aspect_ratio']}",
        "",
        "## Prompt",
        "",
        brief["generation_contract"]["prompt"],
        "",
        "## Storyboard",
        "",
        "| Shot | Duration | Purpose | Action | Camera | Audio | Caption |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for shot in brief.get("story", {}).get("storyboard", []):
        lines.append(
            f"| {shot.get('shot')} | {shot.get('duration')} | {shot.get('purpose')} | "
            f"{shot.get('action')} | {shot.get('camera')} | {shot.get('audio')} | {shot.get('caption')} |"
        )
    lines.extend(["", "## Source Assets", ""])
    for item in brief.get("source_assets", []):
        marker = "missing" if item.get("missing") else "ready"
        lines.append(f"- {item.get('asset_id')}: {item.get('role')} ({marker}) {item.get('stored')}")
    lines.extend(["", "## Risk Notes", ""])
    lines.extend([f"- {item}" for item in brief.get("risk_notes", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def create_video_brief_from_intent(product_id: str, intent: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    intent_path = _resolve_artifact(base, intent, ["video_intents"])
    intent_payload = read_json(intent_path, {})
    if intent_payload.get("schema_version") != "product_creative.video_intent.v2.17":
        raise ValueError("video brief requires a M2.17 video intent artifact")
    if intent_payload.get("status") != "ready_for_video_brief":
        raise ValueError(f"video intent is {intent_payload.get('status')}; prepare required inputs before creating a video brief")

    state = apply_generation_safe_state(read_product_state(base))
    selected = intent_payload.get("selected_material") if isinstance(intent_payload.get("selected_material"), dict) else {}
    related = intent_payload.get("related_artifacts") if isinstance(intent_payload.get("related_artifacts"), dict) else {}
    material_id = _text(selected.get("material_id"))
    analysis_id = _text(related.get("image_analysis_id"))
    alignment_id = _text(related.get("visual_alignment_id"))
    task_material_pack_id = _text(related.get("task_material_pack_id") or selected.get("task_material_pack_id"))
    material_card_id = _text(related.get("material_card_id") or selected.get("material_card_id"))
    material = _find_artifact_by_id(base, "material_assets", "material_id", material_id)
    analysis = _find_artifact_by_id(base, "image_analysis", "analysis_id", analysis_id)
    alignment = _find_artifact_by_id(base, "visual_alignments", "alignment_id", alignment_id)
    if not material:
        raise ValueError("video brief requires the selected material artifact")
    if not analysis:
        raise ValueError("video brief requires image analysis for the selected material")
    if not alignment:
        raise ValueError("video brief requires visual alignment for the selected material")

    platform = _text((intent_payload.get("intent") or {}).get("platform")) or "douyin"
    target = _target(platform)
    product_name = _text(state.get("name")) or base.name
    theme = _theme(intent_payload)
    points = _selling_points(state)
    source_assets = _source_assets(base, intent_payload, material)
    storyboard = _storyboard(product_name, theme, points, _text(material.get("role")), platform)
    intent_message = _text(intent_payload.get("message"))
    non_use_story = any(marker in intent_message for marker in ("不展示使用", "不出现饮用", "不展示打开", "不作医疗"))
    if non_use_story:
        storyboard = _non_use_storyboard(product_name, theme)
    inspiration_context = latest_inspiration_context(base.name, platform or "video_brief")
    prompt = _prompt(product_name, theme, platform, storyboard, source_assets, state, inspiration_context)
    if non_use_story:
        prompt += (
            f"\n本次用户创意原文：{intent_message}\n"
            "硬约束：产品只作为未打开的礼物或场景元素；不得展示打开、饮用或任何使用动作；"
            "不得暗示医疗、通便、营养、孕期适用或安全；成年孕妇必须被尊重地呈现为有主体性的成年女性。"
        )
    brief_id = f"video-brief-{timestamp()}"
    brief = {
        "schema_version": VIDEO_BRIEF_SCHEMA_VERSION,
        "brief_type": "video",
        "brief_id": brief_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_review",
        "source_artifact_id": intent_payload.get("intent_id", intent_path.stem),
        "source_intent_id": intent_payload.get("intent_id", intent_path.stem),
        "source_intent_path": _rel(base, intent_path),
        "source_variant": 1,
        "target": target,
        "product": {
            "name": product_name,
            "one_liner": _text((state.get("basic") or {}).get("brief")),
            "selling_points": points,
        },
        "intent": intent_payload.get("intent", {}),
        "story": {
            "style": _text((state.get("style_preferences") or {}).get("visual_tone")) or "真实自然、产品清晰、克制表达",
            "theme": theme,
            "estimated_duration": "0-10s" if non_use_story else "0-8.5s",
            "pacing": "前1.5秒建立产品识别，3.5秒前完成核心卖点动作，6.5秒前进入真实使用场景，尾帧回到产品主体。",
            "audio_plan": [
                "默认生成轻快背景音。",
                "保留开瓶、入杯、拿起等真实动作声。",
                "如生成口播，只复述已确认产品事实和字幕短句。",
            ],
            "caption_plan": "字幕短句化，不超过 18 个中文字符，不新增未确认卖点。",
            "editing_rules": [
                "每个镜头都必须保持产品主体可识别。",
                "镜头之间用动作方向或产品位置转场，避免随机跳切。",
                "尾帧可作为封面截图。",
            ],
            "storyboard": storyboard,
        },
        "source_assets": source_assets,
        "inspiration_context": inspiration_context if inspiration_context.get("available") else {},
        "visual_grounding": {
            "material_id": material_id,
            "material_card_id": material_card_id,
            "task_material_pack_id": task_material_pack_id,
            "image_analysis_id": analysis_id,
            "visual_alignment_id": alignment_id,
            "image_analysis_confidence": analysis.get("confidence", ""),
            "alignment_status": alignment.get("status", ""),
            "requires_real_ocr_or_vlm_for_packaging_claims": bool(
                (alignment.get("checks") or {}).get("requires_real_ocr_or_vlm_for_packaging_claims")
            ),
        },
        "generation_contract": {
            "prompt": prompt,
            "provider_prompt": prompt,
            "storyboard_prompt_segments": [shot.get("provider_prompt_segment", "") for shot in storyboard],
            "script_quality_contract": {
                "shot_count": len(storyboard),
                "requires_shot_level_camera": True,
                "requires_shot_level_action": True,
                "requires_shot_level_audio": True,
                "requires_product_visibility_each_shot": True,
                "prompt_is_primary_video_quality_control": True,
            },
            "must_preserve": [item for item in [product_name, material_id] + points[:3] if item],
            "must_not_invent": [
                "unverified packaging text",
                "unverified ingredients",
                "certifications",
                "awards",
                "medical or functional claims",
                "origin details not present in Product Brain",
            ],
            "requires_human_review": True,
            "requires_video_provider_mapping": True,
        },
        "creative_brief": {
            "source": "video_intent",
            "message": intent_message,
            "not_product_fact": True,
        },
        "source_snapshot": {
            "product_state_hash": _state_hash(state),
            "product_state_status": state.get("status", ""),
            "source_intent_status": intent_payload.get("status", ""),
            "intent_readiness": intent_payload.get("readiness", {}),
        },
        "source_artifacts": [
            {"id": intent_payload.get("intent_id", intent_path.stem), "type": "video_intent", "path": _rel(base, intent_path)},
            {"id": material_id, "type": "material_asset"},
            {"id": material_card_id, "type": "material_card"},
            {"id": task_material_pack_id, "type": "task_material_pack"},
            {"id": analysis_id, "type": "image_analysis"},
            {"id": alignment_id, "type": "visual_alignment"},
        ],
        "risk_notes": [
            "This brief is ready for human review, not live video generation.",
            "Current image analysis may be mock/local metadata; do not infer packaging text or claims without real OCR/VLM.",
            "External video provider mapping remains a later step.",
        ],
        "brain_write_policy": {
            "direct_write_to_product_brain": False,
            "requires_human_confirmation_for_learning": True,
        },
    }
    out_dir = base / "artifacts" / "video_scripts"
    json_path = out_dir / f"{brief_id}.json"
    md_path = out_dir / f"{brief_id}.md"
    write_json(json_path, brief)
    if task_material_pack_id:
        record_material_usage(base.name, "video_brief", platform, task_material_pack_id, brief_id, [material_id])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_brief_markdown(brief), encoding="utf-8")
    append_jsonl(base / "structured" / "brief_index.jsonl", {
        "export_id": brief_id,
        "created_at": brief["created_at"],
        "kind": "video",
        "source": "video_intent",
        "intent_id": brief["source_intent_id"],
        "outputs": [{"brief_id": brief_id, "brief_type": "video", "source_variant": 1}],
    })
    update_index_and_log(base, "video-brief", brief_id, [f"Intent: {brief['source_intent_id']}", f"Platform: {platform}"])
    return {
        "success": True,
        "product_id": base.name,
        "brief_id": brief_id,
        "status": brief["status"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "brief": brief,
    }
