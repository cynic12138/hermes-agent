"""Conversation intent parsing for Product Creative runtime.

This module owns lightweight message-to-intent heuristics. Workflow planning
consumes these signals but should not grow its own parsing rules.
"""

from __future__ import annotations

import re

from ..capabilities.registry import action_descriptors, intent_rules


def message_indicates_confirmation(message: str) -> bool:
    text = message.lower()
    markers = ["确认", "同意", "应用", "apply", "confirm", "yes"]
    return any(marker in text for marker in markers)


def target_from_message(message: str) -> str:
    text = message.lower()
    if "小红书" in message or "xiaohongshu" in text or "种草" in message:
        return "xiaohongshu-seeding-note"
    if "抖音" in message or "douyin" in text or "短视频" in message:
        return "douyin-short-video-script"
    if "主图" in message or "电商" in message or "ecommerce" in text:
        return "ecommerce-main-image-copy"
    return ""


def external_provider_from_message(message: str) -> str:
    text = message.lower()
    if "小红书" in message or "xiaohongshu" in text or "xhs" in text:
        return "xiaohongshu-sidecar"
    if "抖音" in message or "douyin" in text:
        return "douyin-sidecar"
    if "http://" in text or "https://" in text or "网页" in message or "网络" in message:
        return "generic-web"
    return "manual"


def external_mode_from_message(message: str) -> str:
    if any(item in message for item in ["真实", "抓取", "搜索", "爬取", "平台", "小红书", "抖音", "联网"]):
        return "live"
    if any(item in message for item in ["导入", "本地文件", "文件"]):
        return "import"
    return "dry_run"


def exact_video_template_from_message(message: str) -> str:
    text = message.lower()
    if any(item in message for item in ["节日", "春节", "中秋", "七夕", "端午", "聚会", "送礼"]):
        return "festival_topic"
    if any(item in message for item in ["三个卖点", "三卖点", "三不", "三个不", "三点", "不加色素", "不加香精", "不加防腐剂"]):
        return "three_claims"
    if any(item in message for item in ["痛点", "解决", "怕添加", "顾虑", "担心", "安心"]):
        return "problem_solution"
    if any(item in message for item in ["夏日", "清爽", "冰爽", "解暑", "降温", "炎热"]):
        return "summer_refresh"
    if "anime" in text or any(item in message for item in ["动漫", "卡通", "故事", "剧情"]):
        return "anime_story"
    return "anime_story"


def variant_from_message(message: str) -> int | None:
    patterns = [
        r"第\s*([1-5])\s*(?:版|个|张|条)",
        r"variant\s*([1-5])",
        r"版本\s*([1-5])",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.I)
        if match:
            return int(match.group(1))
    return None


def rating_from_message(message: str) -> int | None:
    patterns = [
        r"评分\s*([1-5])",
        r"打\s*([1-5])\s*分",
        r"([1-5])\s*分",
        r"rating\s*([1-5])",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.I)
        if match:
            return int(match.group(1))
    return None


def duration_from_message(message: str) -> int | None:
    patterns = [
        r"([2-9]|1[0-5])\s*秒",
        r"duration\s*[:=]?\s*([2-9]|1[0-5])",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.I)
        if match:
            return int(match.group(1))
    return None


def fps_from_message(message: str) -> int | None:
    patterns = [
        r"([6-9]|[12]\d|30)\s*fps",
        r"fps\s*[:=]?\s*([6-9]|[12]\d|30)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.I)
        if match:
            return int(match.group(1))
    return None


def message_indicates_selected(message: str) -> bool:
    return any(item in message for item in ["选择", "选中", "选第", "采用", "保留", "喜欢", "不错", "满意"])


def message_indicates_rejected(message: str) -> bool:
    return any(item in message for item in ["不喜欢", "不要", "不采用", "不满意", "偏离", "不适合"])


def message_allows_evolution(message: str) -> bool:
    return any(item in message for item in ["记住", "学习", "以后", "后续", "下次", "沉淀", "偏好", "保持", "持续"])


def url_from_message(message: str) -> str:
    match = re.search(r"https?://[^\s\"'<>]+", message)
    return match.group(0) if match else ""


def action_from_message(message: str, fallback: str) -> str:
    for rule in intent_rules():
        if rule.matcher(message):
            return rule.action
    descriptor = action_descriptors().get(fallback)
    if descriptor and descriptor.requires_user_input and message.strip():
        return fallback
    return fallback
