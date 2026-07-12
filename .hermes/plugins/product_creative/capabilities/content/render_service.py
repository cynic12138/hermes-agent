"""Content artifact rendering and material context service."""

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
from .fallback_service import TARGET_REGISTRY


CHANNEL_CONTENT_SCHEMA_VERSION = "product_creative.channel_content.v2.2"

def _copy_pack_markdown(product_id: str, artifact_id: str, packs: List[Dict[str, Any]]) -> str:
    sections = [f"# Product Copy Pack {artifact_id}", "", f"Product: {product_id}", ""]
    for pack in packs:
        sections.extend(
            [
                f"## Variant {pack['variant']} - {pack['style']}",
                "",
                "### Product One-Liner",
                "",
                pack["product_one_liner"],
                "",
                "### Core Selling Points",
                "",
            ]
        )
        sections.extend(f"- {item}" for item in pack["core_selling_points"])
        sections.extend(
            [
                "",
                "### Ecommerce Main Image Copy",
                "",
                f"- Headline: {pack['ecommerce_main_image_copy']['headline']}",
                f"- Subheadline: {pack['ecommerce_main_image_copy']['subheadline']}",
                f"- Visual direction: {pack['ecommerce_main_image_copy']['visual_direction']}",
                "",
                "### Image Generation Prompt",
                "",
                pack["image_generation_prompt"],
                "",
                "### Short Video Storyboard",
                "",
            ]
        )
        for shot in pack["short_video_storyboard"]:
            sections.append(
                f"- Shot {shot['shot']} ({shot['duration']}): "
                f"{shot['description']} Caption: {shot['caption']}"
            )
        sections.append("")
    return "\n".join(sections)

def _channel_content_markdown(product_id: str, artifact_id: str, target: str, packs: List[Dict[str, Any]]) -> str:
    target_name = TARGET_REGISTRY[target]["name"]
    sections = [f"# {target_name} {artifact_id}", "", f"Product: {product_id}", f"Target: {target}", ""]
    for pack in packs:
        sections.extend([f"## Variant {pack['variant']} - {pack['style']}", ""])
        if target == "ecommerce-main-image-copy":
            sections.extend(
                [
                    "### Main Image Copy",
                    "",
                    f"- Main title: {pack['main_title']}",
                    f"- Subtitle: {pack['subtitle']}",
                    "",
                    "### Selling Point Lines",
                    "",
                ]
            )
            sections.extend(f"- {item}" for item in pack["selling_point_lines"])
            sections.extend(["", "### Image Text Suggestions", ""])
            sections.extend(f"- {item}" for item in pack["image_text_suggestions"])
            sections.extend(["", "### Visual Prompt Seed", "", pack["visual_prompt_seed"], ""])
        elif target == "xiaohongshu-seeding-note":
            sections.extend(["### Title Options", ""])
            sections.extend(f"- {item}" for item in pack["title_options"])
            sections.extend(
                [
                    "",
                    "### Opening Hook",
                    "",
                    pack["opening_hook"],
                    "",
                    "### Body",
                    "",
                    pack["body"],
                    "",
                    "### Selling Point Mapping",
                    "",
                ]
            )
            sections.extend(f"- {item}" for item in pack["selling_point_mapping"])
            sections.extend(["", "### Tone", "", pack["tone"], "", "### Hashtags", ""])
            sections.extend(f"- {item}" for item in pack["hashtags"])
        elif target == "douyin-short-video-script":
            sections.extend(["### Hook 0-3s", "", pack["hook_0_3s"], "", "### Shots", ""])
            for shot in pack["shots"]:
                sections.append(
                    f"- Shot {shot['shot']} ({shot['duration']}): "
                    f"Visual: {shot['visual']} Voiceover: {shot['voiceover']} Caption: {shot['caption']}"
                )
            sections.extend(["", "### Product Exposure Points", ""])
            sections.extend(f"- {item}" for item in pack["product_exposure_points"])
            sections.extend(["", "### CTA", "", pack["cta"], "", "### Video Brief Seed", "", pack["video_brief_seed"], ""])
        sections.extend(["### Avoid Claims", ""])
        sections.extend(f"- {item}" for item in pack["avoid_claims"])
        sections.append("")
    return "\n".join(sections)

def _artifact_markdown(product_id: str, artifact_id: str, target: str, packs: List[Dict[str, Any]]) -> str:
    if target == "product-copy-pack":
        return _copy_pack_markdown(product_id, artifact_id, packs)
    return _channel_content_markdown(product_id, artifact_id, target, packs)

def _material_context_for_target(product_id: str, target: str) -> Dict[str, Any]:
    inspiration_context = latest_inspiration_context(product_id, target)
    if target == "product-copy-pack":
        return {"inspiration_context": inspiration_context} if inspiration_context.get("available") else {}
    pack_result = prepare_task_material_pack(product_id, "channel_content", target, 3)
    pack = pack_result.get("task_material_pack") if isinstance(pack_result.get("task_material_pack"), dict) else {}
    if not pack:
        return {"inspiration_context": inspiration_context} if inspiration_context.get("available") else {}
    context = {
        "task_material_pack_id": pack.get("task_material_pack_id", ""),
        "task": pack.get("task", ""),
        "channel": pack.get("channel", ""),
        "selected_materials": [
            {
                "material_id": item.get("material_id", ""),
                "role": item.get("role", ""),
                "score": item.get("score", 0),
                "summary": item.get("summary", ""),
                "markdown_path": item.get("markdown_path", ""),
                "warnings": item.get("warnings", []),
            }
            for item in pack.get("selected_materials", [])
            if isinstance(item, dict)
        ],
        "missing_requirements": pack.get("missing_requirements", []),
    }
    if inspiration_context.get("available"):
        context["inspiration_context"] = inspiration_context
    return context

def _create_experiment_page(base: Path, artifact_id: str, target: str, packs: List[Dict[str, Any]]) -> None:
    date = today()
    page = base / "wiki" / "experiments" / f"{date}-{artifact_id}.md"
    variant_lines = "\n".join(f"- Variant {p['variant']}: {p['style']}" for p in packs)
    page.write_text(
        f"""---
title: {artifact_id}
type: experiment
product_id: {base.name}
created: {date}
updated: {date}
confidence: low
status: generated
sources:
  - raw/generated-content/{artifact_id}.md
---

# {artifact_id}

## Goal

Generate product creative content for `{target}`.

## Variants

{variant_lines}

## Feedback

待用户反馈。
""",
        encoding="utf-8",
    )
