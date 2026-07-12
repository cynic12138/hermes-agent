"""Product Brain wiki templates, linting, rendering, and state export."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..common import ensure_product, now_iso, product_dir, product_state_path, read_json, read_product_state, timestamp, today, update_index_and_log, wiki_path, write_json
from ..context_safety import apply_generation_safe_state
from ..ports.runtime_repositories import brain_documents
from .context import CONTEXT_PROFILES
from .provenance import (
    fingerprint_guard_keywords as _fingerprint_guard_keywords,
    known_source_ids as _known_source_ids,
    read_product_fingerprint as _read_product_fingerprint,
    source_ids_for_page as _source_ids_for_page,
    source_ids_in_text as _source_ids_in_text,
)


__all__ = [
    "M1_REQUIRED_FRONTMATTER",
    "M1_WIKI_TEMPLATES",
    "PRODUCT_STATE_EXPORT_SCHEMA_VERSION",
    "ensure_m1_wiki",
    "export_product_state_from_wiki",
    "render_product_pages",
    "wiki_lint_product",
    "wiki_upgrade_product",
]


M1_REQUIRED_FRONTMATTER = [
    "title",
    "type",
    "product_id",
    "status",
    "confidence",
    "sources",
    "created_at",
    "updated_at",
]

M1_WIKI_TEMPLATES: List[Tuple[str, str, str, str]] = [
    ("product/Product.md", "Product Core State", "product_profile", "product"),
    ("product/positioning.md", "Positioning", "product_profile", "product"),
    ("product/selling-points.md", "Selling Points", "product_profile", "product"),
    ("product/brand-voice.md", "Brand Voice", "product_profile", "product"),
    ("product/visual-identity.md", "Visual Identity", "product_profile", "product"),
    ("channels/ecommerce.md", "Ecommerce Copy Playbook", "channel_playbook", "channels"),
    ("channels/ecommerce-main-image.md", "Ecommerce Main Image Playbook", "channel_playbook", "channels"),
    ("content-patterns/visual-patterns.md", "Visual Patterns", "content_pattern", "content-patterns"),
    ("content-patterns/video-patterns.md", "Video Patterns", "content_pattern", "content-patterns"),
    ("content-patterns/proven-patterns.md", "Proven Patterns", "content_pattern", "content-patterns"),
    ("content-patterns/failed-patterns.md", "Failed Patterns", "content_pattern", "content-patterns"),
    ("compliance/forbidden-claims.md", "Forbidden Claims", "compliance_rule", "compliance"),
    ("eval/content-quality-rubric.md", "Content Quality Rubric", "eval_rubric", "eval"),
]

PRODUCT_STATE_EXPORT_SCHEMA_VERSION = "product_creative.product_state_export.v2"

def _template_body(title: str, group: str, name: str = "") -> str:
    if group == "product" and title == "Product Core State":
        return f"""# {name or "Product"}

## Product One-Liner

待补充。

## Current Positioning

待补充。

## Core Selling Points

- 待补充。

## Channel Strategy Entrypoints

- Ecommerce: [[channels/ecommerce]]

## Current Learning

- 尚无反馈学习。

## Confirmed Learning

- No canonical insight yet.
"""
    if group == "product" and title == "Selling Points":
        return """# Selling Points

## Core Selling Points

- 待补充。

## Evidence

- No evidence yet.

## Confirmed Learning

- No canonical insight yet.
"""
    if group == "product":
        return f"""# {title}

## Current Draft

待补充。

## Evidence

- No evidence yet.

## Open Questions

- 待补充。

## Confirmed Learning

- No canonical insight yet.
"""
    if group == "channels":
        return f"""# {title}

## Channel Principles

- 待补充。

## Constraints

- 待补充。

## Confirmed Learning

- No canonical insight yet.
"""
    if group == "content-patterns":
        return f"""# {title}

## Patterns

- No canonical insight yet.

## Evidence

- No evidence yet.

## Confirmed Learning

- No canonical insight yet.
"""
    if group == "compliance":
        return f"""# {title}

## Rules

- No canonical rule yet.

## Evidence

- No evidence yet.

## Confirmed Learning

- No canonical insight yet.
"""
    return f"""# {title}

## Rubric

- 待补充。

## Confirmed Learning

- No canonical insight yet.
"""


def _frontmatter(title: str, page_type: str, product_id: str, date: str) -> str:
    return f"""---
title: {title}
type: {page_type}
product_id: {product_id}
status: draft
confidence: low
sources: []
created_at: {date}
updated_at: {date}
---
"""


def _split_frontmatter(text: str) -> Tuple[Dict[str, str], str, bool]:
    if not text.startswith("---"):
        return {}, text, False
    match = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)", text, flags=re.S)
    if not match:
        return {}, text, False
    raw_meta, body = match.group(1), match.group(2)
    meta: Dict[str, str] = {}
    for line in raw_meta.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body, True


def _render_frontmatter(meta: Dict[str, str]) -> str:
    order = M1_REQUIRED_FRONTMATTER
    lines = ["---"]
    for key in order:
        if key not in meta:
            continue
        lines.append(f"{key}: {meta[key]}")
    for key, value in meta.items():
        if key not in order:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _normalize_wiki_page(path: Path, product_id: str, title: str, page_type: str, date: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    meta, body, has_frontmatter = _split_frontmatter(text)
    changed = not has_frontmatter
    defaults = {
        "title": title,
        "type": page_type,
        "product_id": product_id,
        "status": "draft",
        "confidence": "low",
        "sources": "[]",
        "created_at": meta.get("created") or date,
        "updated_at": meta.get("updated") or date,
    }
    for key, value in defaults.items():
        if not meta.get(key):
            meta[key] = value
            changed = True
    if changed:
        path.write_text(_render_frontmatter(meta) + body.lstrip(), encoding="utf-8")
    return changed


def ensure_m1_wiki(base: Path, product_id: str, name: str = "") -> Dict[str, Any]:
    created = []
    normalized = []
    date = today()
    for rel, title, page_type, group in M1_WIKI_TEMPLATES:
        path = base / "wiki" / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                _frontmatter(title, page_type, product_id, date) + "\n" + _template_body(title, group, name),
                encoding="utf-8",
            )
            created.append(rel)
        elif _normalize_wiki_page(path, product_id, title, page_type, date):
            normalized.append(rel)
    return {"created": created, "normalized": normalized}


def _section(text: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text, flags=re.M)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+", text[start:], flags=re.M)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def _bullet_items(text: str) -> List[str]:
    items = []
    for line in text.splitlines():
        item = line.strip()
        if not item.startswith("- "):
            continue
        value = item[2:].strip()
        if not value or value in {"待补充。", "No canonical insight yet.", "No evidence yet."}:
            continue
        if value not in items:
            items.append(value)
    return items


def _safe_rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))




def render_product_pages(base: Path, state: Dict[str, Any]) -> None:
    date = today()
    name = state.get("name") or base.name
    brief = state.get("basic", {}).get("brief") or "待补充。"
    points = state.get("selling_points") or ["待补充。"]
    point_lines = "\n".join(f"- {item}" for item in points)
    learning = state.get("learning", {})
    preferences = list(learning.get("feedback_preferences", []) or [])
    preferences.extend(learning.get("channel_preferences", []) or [])
    preference_lines = "\n".join(f"- {item}" for item in preferences) or "- 尚无反馈学习。"
    sources = state.get("sources") or []
    source_lines = "\n".join(f"  - {s}" for s in sources)
    product_page = wiki_path(base, "product", "Product.md")
    selling_page = wiki_path(base, "product", "selling-points.md")
    previous_product = product_page.read_text(encoding="utf-8") if product_page.exists() else ""
    previous_selling = selling_page.read_text(encoding="utf-8") if selling_page.exists() else ""
    confirmed_product = _section(previous_product, "Confirmed Learning") or "- No canonical insight yet."
    confirmed_selling = _section(previous_selling, "Confirmed Learning") or "- No canonical insight yet."
    wiki_path(base, "product", "Product.md").write_text(
        f"""---
title: Product Core State
type: product_profile
product_id: {base.name}
confidence: low
status: draft
sources:
{source_lines if source_lines else "  []"}
created_at: {date}
updated_at: {date}
---

# {name}

## Product One-Liner

{brief[:120]}

## Current Positioning

{brief}

## Core Selling Points

{point_lines}

## Channel Strategy Entrypoints

- Ecommerce: [[channels/ecommerce]]
- Douyin: [[channels/douyin]]

## Current Learning

{preference_lines}

## Confirmed Learning

{confirmed_product}
""",
        encoding="utf-8",
    )
    wiki_path(base, "product", "selling-points.md").write_text(
        f"""---
title: Selling Points
type: product_profile
product_id: {base.name}
confidence: low
status: draft
sources:
{source_lines if source_lines else "  []"}
created_at: {date}
updated_at: {date}
---

# Selling Points

## Core Selling Points

{point_lines}

## Confirmed Learning

{confirmed_selling}
""",
        encoding="utf-8",
    )




def wiki_upgrade_product(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    state = read_product_state(base)
    result = ensure_m1_wiki(base, base.name, state.get("name") or base.name)
    update_index_and_log(
        base,
        "wiki-upgrade",
        "M1 canonical Product Brain schema",
        [
            f"Created {len(result['created'])} page(s)",
            f"Normalized {len(result['normalized'])} page(s)",
        ],
    )
    return {
        "success": True,
        "product_id": base.name,
        "created": result["created"],
        "normalized": result["normalized"],
        "required_pages": [item[0] for item in M1_WIKI_TEMPLATES],
    }


def _wiki_markdown_files(base: Path) -> List[Path]:
    return sorted((base / "wiki").glob("**/*.md"))


def _frontmatter_source_values(text: str) -> List[str]:
    match = re.match(r"---\s*\n(.*?)\n---", text, flags=re.S)
    if not match:
        return []
    lines = match.group(1).splitlines()
    values = []
    in_sources = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("sources:"):
            in_sources = True
            value = stripped.split(":", 1)[1].strip()
            if value and value != "[]":
                values.append(value.strip("'\""))
            continue
        if in_sources:
            if stripped.startswith("- "):
                values.append(stripped[2:].strip().strip("'\""))
                continue
            if line and not line.startswith(" "):
                in_sources = False
    return [item for item in values if item and item != "[]"]


def wiki_lint_product(product_id: str, write_report: bool = True) -> Dict[str, Any]:
    base = ensure_product(product_id)
    root = base.resolve()
    errors: List[str] = []
    warnings: List[str] = []
    checked_pages = []
    required_pages = [item[0] for item in M1_WIKI_TEMPLATES]
    known_products = [
        item.name for item in product_dir(base.name).parent.iterdir()
        if item.is_dir() and item.name != base.name
    ]
    known_sources = _known_source_ids(base)
    other_fingerprints = []
    for other_id in known_products:
        other_base = product_dir(other_id)
        fingerprint = _read_product_fingerprint(other_base)
        keywords = _fingerprint_guard_keywords(fingerprint)
        if keywords:
            other_fingerprints.append({"product_id": other_id, "keywords": keywords})

    for rel, _title, _page_type, _group in M1_WIKI_TEMPLATES:
        path = base / "wiki" / rel
        if not path.exists():
            errors.append(f"missing required wiki page: {rel}")

    for path in _wiki_markdown_files(base):
        rel = _safe_rel(base / "wiki", path)
        checked_pages.append(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, _body, has_frontmatter = _split_frontmatter(text)
        if rel in required_pages:
            if not has_frontmatter:
                errors.append(f"{rel}: missing frontmatter")
                continue
            for key in M1_REQUIRED_FRONTMATTER:
                if key not in meta:
                    errors.append(f"{rel}: missing frontmatter field '{key}'")
            if meta.get("product_id") and meta.get("product_id") != base.name:
                errors.append(f"{rel}: product_id is {meta.get('product_id')}, expected {base.name}")
            if meta.get("status") == "canonical" and meta.get("sources", "[]") == "[]":
                errors.append(f"{rel}: canonical page requires sources")

        for other_id in known_products:
            if other_id and other_id in text:
                errors.append(f"{rel}: references another product id '{other_id}'")
            if f"products/{other_id}" in text.replace("\\", "/"):
                errors.append(f"{rel}: references another product workspace '{other_id}'")
        for fingerprint in other_fingerprints:
            for keyword in fingerprint["keywords"]:
                if keyword in text:
                    warnings.append(
                        f"{rel}: contains fingerprint keyword '{keyword}' from product '{fingerprint['product_id']}'"
                    )
        for source_id in _source_ids_in_text(text):
            source = known_sources.get(source_id)
            if not source:
                errors.append(f"{rel}: references unknown source id '{source_id}'")
            elif source.get("product_id") != base.name:
                errors.append(f"{rel}: source id '{source_id}' belongs to another product")

        for source in _frontmatter_source_values(text):
            normalized = source.replace("\\", "/")
            if normalized.startswith(("raw/", "wiki/", "structured/", "assets/", "artifacts/")):
                continue
            candidate = Path(source)
            if candidate.is_absolute():
                resolved = candidate.resolve()
                if resolved != root and root not in resolved.parents:
                    errors.append(f"{rel}: source points outside product workspace: {source}")
            else:
                warnings.append(f"{rel}: source is not a known product-relative path: {source}")

    report = {
        "success": not errors,
        "schema_version": "product_creative.wiki_lint.v1",
        "product_id": base.name,
        "created_at": now_iso(),
        "checked_page_count": len(checked_pages),
        "checked_pages": checked_pages,
        "errors": errors,
        "warnings": warnings,
    }
    files = {}
    if write_report:
        out_dir = base / "artifacts" / "wiki_lint"
        report_path = out_dir / f"wiki-lint-{timestamp()}.json"
        write_json(report_path, report)
        files["json"] = str(report_path)
        update_index_and_log(
            base,
            "wiki-lint",
            "M1 Product Brain lint",
            [f"Errors: {len(errors)}", f"Warnings: {len(warnings)}"],
        )
    return {**report, "files": files}


def export_product_state_from_wiki(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    wiki_upgrade_product(base.name)
    product_text = wiki_path(base, "product", "Product.md").read_text(encoding="utf-8")
    selling_text = wiki_path(base, "product", "selling-points.md").read_text(encoding="utf-8")
    old_state = read_product_state(base)
    product_meta, product_body, _ = _split_frontmatter(product_text)
    name_match = re.search(r"^#\s+(.+)$", product_body, flags=re.M)
    name = name_match.group(1).strip() if name_match else old_state.get("name") or base.name
    one_liner = _section(product_body, "Product One-Liner")
    positioning = _section(product_body, "Current Positioning") or one_liner
    points = _bullet_items(_section(product_body, "Core Selling Points"))
    if not points:
        points = _bullet_items(_section(selling_text, "Core Selling Points")) or _bullet_items(selling_text)
    confirmed = []
    confirmed_source_pages = []
    confirmed_source_ids = []
    for path in _wiki_markdown_files(base):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = _safe_rel(base / "wiki", path)
        items = _bullet_items(_section(text, "Confirmed Learning"))
        if items:
            confirmed_source_pages.append(rel)
            for source_id in _source_ids_for_page(base, text):
                if source_id not in confirmed_source_ids:
                    confirmed_source_ids.append(source_id)
        confirmed.extend(items)
    status = "canonical" if product_meta.get("status") == "canonical" and points else "draft_incomplete"
    warnings = []
    if not confirmed_source_ids and confirmed:
        warnings.append("confirmed_wiki_learning has no registered source ids")
    brief_source_ids = _source_ids_for_page(base, product_text)
    selling_source_ids = _source_ids_for_page(base, selling_text)
    state = {
        "product_id": base.name,
        "name": name,
        "status": status,
        "created_at": old_state.get("created_at") or now_iso(),
        "updated_at": now_iso(),
        "sources": old_state.get("sources", []),
        "basic": {
            "brief": positioning if positioning and positioning != "待补充。" else old_state.get("basic", {}).get("brief", ""),
            "_source": "wiki/product/Product.md",
        },
        "selling_points": points,
        "style_preferences": old_state.get("style_preferences", {}),
        "learning": {
            "successful_patterns": old_state.get("learning", {}).get("successful_patterns", []),
            "failed_patterns": old_state.get("learning", {}).get("failed_patterns", []),
            "feedback_preferences": old_state.get("learning", {}).get("feedback_preferences", []),
            "image_generation_preferences": old_state.get("learning", {}).get("image_generation_preferences", []),
            "video_script_preferences": old_state.get("learning", {}).get(
                "video_script_preferences",
                old_state.get("learning", {}).get("video_generation_preferences", []),
            ),
            "channel_preferences": old_state.get("learning", {}).get("channel_preferences", []),
            "confirmed_wiki_learning": confirmed,
        },
        "assets": old_state.get("assets", {}),
        "_provenance": {
            "basic.brief": {
                "source_page": "wiki/product/Product.md",
                "status": product_meta.get("status") or "draft",
                "confidence": product_meta.get("confidence") or "low",
                "source_ids": brief_source_ids,
            },
            "selling_points": {
                "source_page": "wiki/product/selling-points.md",
                "status": "draft",
                "confidence": "low",
                "source_ids": selling_source_ids,
            },
            "learning.confirmed_wiki_learning": {
                "source_pages": confirmed_source_pages,
                "source_ids": confirmed_source_ids,
            },
        },
        "_warnings": warnings,
        "_export": {
            "schema_version": PRODUCT_STATE_EXPORT_SCHEMA_VERSION,
            "source": "product_wiki",
            "exported_at": now_iso(),
            "page_count": len(_wiki_markdown_files(base)),
            "pages": [item[0] for item in M1_WIKI_TEMPLATES],
            "context_profiles": sorted(CONTEXT_PROFILES.keys()),
        },
    }
    state = apply_generation_safe_state(state)
    brain_documents(base).save_state(state)
    out_dir = base / "artifacts" / "state_exports"
    export_path = out_dir / f"state-export-{timestamp()}.json"
    write_json(export_path, state)
    update_index_and_log(base, "state-export", "Product State from Product Wiki", [str(export_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "status": state["status"],
        "product_state": str(product_state_path(base)),
        "files": {"json": str(export_path)},
        "state": state,
    }


