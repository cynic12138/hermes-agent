"""Product workspace creation and resolution services."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import now_iso, product_dir, product_state_path, products_root, read_json, slug, timestamp, today, wiki_path, write_if_missing, write_json
from ...brain.wiki import ensure_m1_wiki as _ensure_m1_wiki
from ...context_safety import apply_generation_safe_state
from ...ports.runtime_repositories import product_brains


__all__ = ["create_product", "resolve_product_workspace"]


def _init_workspace(base: Path, product_id: str, name: str) -> None:
    for rel in [
        "wiki/product",
        "wiki/audience",
        "wiki/channels",
        "wiki/content-patterns",
        "wiki/experiments",
        "wiki/skills",
        "wiki/compliance",
        "wiki/eval",
        "raw/product-inputs",
        "raw/product-images",
        "raw/user-feedback",
        "raw/generated-content",
        "structured/evolution_proposals",
        "assets/images",
        "assets/videos",
        "assets/generated",
        "artifacts/copy",
        "artifacts/evaluations",
        "artifacts/image_briefs",
        "artifacts/video_scripts",
        "artifacts/provider_payloads",
        "artifacts/provider_validations",
        "artifacts/generation_jobs",
        "artifacts/generated_images",
        "artifacts/generated_videos",
        "artifacts/video_tasks",
        "artifacts/channel_content",
        "artifacts/review_packages",
        "artifacts/result_review_packages",
        "artifacts/result_evaluations",
        "artifacts/result_feedback",
        "artifacts/live_readiness",
        "artifacts/creative_runs",
        "artifacts/image_qa",
        "artifacts/comparison_packages",
        "artifacts/wiki_lint",
        "artifacts/state_exports",
        "artifacts/channel_evaluations",
        "artifacts/channel_feedback",
        "artifacts/channel_review_packages",
        "artifacts/channel_review_runs",
        "artifacts/material_assets",
        "artifacts/image_analysis",
        "artifacts/visual_alignments",
        "artifacts/material_cards",
        "artifacts/material_library",
        "artifacts/task_material_packs",
        "artifacts/material_usage",
        "artifacts/material_feedback",
        "artifacts/video_intents",
        "artifacts/workflow_runs",
    ]:
        (base / rel).mkdir(parents=True, exist_ok=True)

    date = today()
    write_if_missing(
        base / "wiki" / "SCHEMA.md",
        f"""# Product Wiki Schema

## Domain

Product Brain for product `{product_id}`.

## Conventions

- Raw files under `raw/` are source evidence and should not be edited in place.
- Wiki pages store conclusions, playbooks, experiments, and reviewable learning.
- Every important claim should keep a source reference and confidence.
- High-impact updates to product positioning, selling points, brand voice, compliance, and Product State require human confirmation.

## Page Types

- product_profile
- channel_playbook
- content_pattern
- experiment
- skill_playbook
- compliance_rule
- eval_rubric
""",
    )
    write_if_missing(
        base / "wiki" / "index.md",
        f"""# Product Wiki Index

Last updated: {date}

## Product

- [[product/Product]] - Product Brain home page.
- [[product/selling-points]] - Core selling points and proof points.

## Channels

- [[channels/ecommerce]] - Ecommerce copy and main-image description playbook.
- [[channels/douyin]] - Short-video script and storyboard playbook.

## Experiments

- No experiments yet.
""",
    )
    write_if_missing(
        base / "wiki" / "log.md",
        f"""# Product Wiki Log

## [{date}] create | Product workspace initialized
- Product id: {product_id}
- Product name: {name}
""",
    )
    write_if_missing(
        wiki_path(base, "product", "Product.md"),
        f"""---
title: Product Core State
type: product_profile
product_id: {product_id}
created: {date}
updated: {date}
confidence: low
status: draft
sources: []
---

# {name}

## Product One-Liner

待补充。

## Current Positioning

待补充。

## Core Selling Points

- 待补充。

## Channel Strategy Entrypoints

- Ecommerce: [[channels/ecommerce]]
- Douyin: [[channels/douyin]]

## Current Learning

- 尚无反馈学习。
""",
    )
    write_if_missing(
        wiki_path(base, "product", "selling-points.md"),
        f"""---
title: Selling Points
type: product_profile
product_id: {product_id}
created: {date}
updated: {date}
confidence: low
status: draft
sources: []
---

# Selling Points

- 待补充。
""",
    )
    write_if_missing(
        wiki_path(base, "channels", "ecommerce.md"),
        f"""---
title: Ecommerce Copy Playbook
type: channel_playbook
product_id: {product_id}
created: {date}
updated: {date}
confidence: low
status: draft
sources: []
---

# Ecommerce Copy Playbook

## Main Image Description Principles

- 先突出用户可感知利益，再补充产品事实。
- 文案应短、清晰、可放进主图。
- 图片生成 prompt 应说明主体、背景、构图、光线、风格和禁止项。
""",
    )
    write_if_missing(
        wiki_path(base, "channels", "douyin.md"),
        f"""---
title: Douyin Storyboard Playbook
type: channel_playbook
product_id: {product_id}
created: {date}
updated: {date}
confidence: low
status: draft
sources: []
---

# Douyin Storyboard Playbook

## Short Video Principles

- 前 3 秒给出场景、痛点或反差。
- 每个镜头只表达一个信息。
- 分镜描述应可直接转成视频 prompt。
""",
    )
    _ensure_m1_wiki(base, product_id, name)


def create_product(product_id: str, name: str) -> Dict[str, Any]:
    pid = slug(product_id)
    base = product_dir(pid)
    base.mkdir(parents=True, exist_ok=True)
    _init_workspace(base, pid, name or pid)
    state_path = product_state_path(base)
    if not state_path.exists():
        initial_state = {
            "product_id": pid,
            "name": name or pid,
            "status": "draft",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "sources": [],
            "basic": {"brief": ""},
            "selling_points": [],
            "style_preferences": {},
            "learning": {
                "successful_patterns": [],
                "failed_patterns": [],
                "feedback_preferences": [],
                "image_generation_preferences": [],
                "video_script_preferences": [],
                "channel_preferences": [],
            },
        }
        write_json(state_path, apply_generation_safe_state(initial_state))
    brain_version = product_brains().ensure_initial(pid, read_json(state_path, {}))
    return {
        "success": True,
        "product_id": pid,
        "product_dir": str(base),
        "product_state": str(state_path),
        "brain_version": brain_version,
    }


def _workspace_summary(base: Path) -> Dict[str, Any]:
    current = product_brains().current(base.name)
    state = current.get("state") if current else read_json(product_state_path(base), {})
    fingerprint = read_json(base / "structured" / "product_fingerprint.json", {})
    keywords = fingerprint.get("keywords") if isinstance(fingerprint.get("keywords"), list) else []
    return {
        "product_id": base.name,
        "name": str(state.get("name") or fingerprint.get("name") or base.name),
        "status": str(state.get("status") or ""),
        "updated_at": str(state.get("updated_at") or ""),
        "selling_points": state.get("selling_points") if isinstance(state.get("selling_points"), list) else [],
        "keywords": [str(item) for item in keywords],
        "product_dir": str(base),
    }


def _workspace_score(summary: Dict[str, Any], query: str) -> int:
    text = query.strip().lower()
    if not text:
        return 0
    product_id = str(summary.get("product_id") or "").lower()
    name = str(summary.get("name") or "").lower()
    keywords = [str(item).lower() for item in summary.get("keywords") or []]
    selling_points = [str(item).lower() for item in summary.get("selling_points") or []]
    score = 0
    if text == product_id:
        score += 100
    if text == name:
        score += 90
    if text in product_id:
        score += 50
    if text in name:
        score += 60
    for item in keywords + selling_points:
        if text and text in item:
            score += 10
    query_parts = [part for part in re.split(r"[\s,，、]+", text) if len(part) >= 2]
    for part in query_parts:
        if part in product_id or part in name:
            score += 8
        for item in keywords + selling_points:
            if part in item:
                score += 2
    return score


def _safe_suggested_product_id(value: str) -> str:
    raw = value.strip()
    if raw:
        try:
            return slug(raw)
        except ValueError:
            pass
    return f"product-{timestamp()}"


def _unique_product_id(candidate: str) -> str:
    root = products_root()
    product_id = _safe_suggested_product_id(candidate)
    if not (root / product_id).exists():
        return product_id
    for index in range(2, 100):
        next_id = f"{product_id}-{index}"
        if not (root / next_id).exists():
            return next_id
    return f"{product_id}-{timestamp()}"


def resolve_product_workspace(
    query: str = "",
    create_if_missing: bool = False,
    suggested_id: str = "",
    name: str = "",
    limit: int = 10,
) -> Dict[str, Any]:
    root = products_root()
    summaries: List[Dict[str, Any]] = []
    for base in sorted([item for item in root.iterdir() if item.is_dir()]):
        if not (base / "structured").exists():
            continue
        summary = _workspace_summary(base)
        summary["match_score"] = _workspace_score(summary, query)
        summaries.append(summary)

    matches = [item for item in summaries if not query.strip() or int(item.get("match_score") or 0) > 0]
    matches.sort(key=lambda item: (int(item.get("match_score") or 0), str(item.get("updated_at") or ""), str(item.get("product_id") or "")), reverse=True)
    minimum_unique_score = 40
    selected = matches[0] if matches and int(matches[0].get("match_score") or 0) >= minimum_unique_score else {}
    ambiguous = bool(len(matches) > 1 and selected and int(matches[1].get("match_score") or 0) == int(selected.get("match_score") or 0))

    if selected and not ambiguous:
        return {
            "success": True,
            "schema_version": "product_creative.workspace_resolve.v4.9",
            "query": query,
            "selected_product_id": selected.get("product_id", ""),
            "selected": selected,
            "matches": matches[: max(1, min(int(limit or 10), 20))],
            "created": False,
            "user_next_message": f"继续围绕 {selected.get('name') or selected.get('product_id')} 工作。",
        }

    if create_if_missing:
        product_name = name.strip() or query.strip()
        product_id = _unique_product_id(suggested_id or product_name or "product")
        created = create_product(product_id, product_name or product_id)
        selected_summary = _workspace_summary(product_dir(created["product_id"]))
        return {
            "success": True,
            "schema_version": "product_creative.workspace_resolve.v4.9",
            "query": query,
            "selected_product_id": created["product_id"],
            "selected": selected_summary,
            "matches": matches[: max(1, min(int(limit or 10), 20))],
            "created": True,
            "user_next_message": f"已创建产品工作区 {created['product_id']}，下一步可以补充产品资料或上传主图。",
        }

    return {
        "success": True,
        "schema_version": "product_creative.workspace_resolve.v4.9",
        "query": query,
        "selected_product_id": "",
        "selected": {},
        "matches": matches[: max(1, min(int(limit or 10), 20))],
        "created": False,
        "ambiguous": ambiguous,
        "user_next_message": "没有唯一匹配的产品工作区。请让用户确认产品，或在用户明确要开始新产品时设置 create_if_missing。",
    }


