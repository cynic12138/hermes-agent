"""Product source ingestion services."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...common import ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...brain.provenance import build_product_fingerprint, register_source as _register_source
from ...brain.wiki import render_product_pages
from ...context_safety import apply_generation_safe_state, generation_safe_list
from ...ports.runtime_repositories import brain_documents


__all__ = ["ingest_product"]


def _first_nonempty_lines(text: str, limit: int = 8) -> List[str]:
    lines = []
    for raw in text.splitlines():
        item = raw.strip(" \t-•*0123456789.、")
        if item:
            lines.append(item)
        if len(lines) >= limit:
            break
    return lines


def _sentences(text: str, limit: int = 5) -> List[str]:
    parts = re.split(r"[。！？!?；;\n]+", text)
    items = [p.strip(" \t-•*0123456789.、") for p in parts if p.strip()]
    return items[:limit]


def _compact_phrase(value: str) -> str:
    value = value.strip(" \t-•*0123456789.、，。；;:：")
    value = re.sub(r"^(主打|突出|强调|卖点是|核心是)", "", value).strip()
    return value


def _extract_selling_points(text: str) -> List[str]:
    pieces = re.split(r"[，,、；;。！？!?\n]+", text)
    blocked = ("希望", "不要", "避免", "整体表达", "风格", "促销")
    points: List[str] = []
    for piece in pieces:
        item = _compact_phrase(piece)
        if len(item) < 2:
            continue
        if any(word in item for word in blocked):
            continue
        if item not in points:
            points.append(item)
        if len(points) >= 5:
            break
    return points


def _summarize_source(text: str) -> Dict[str, Any]:
    compact = re.sub(r"\s+", " ", text).strip()
    candidates = _extract_selling_points(text) or _first_nonempty_lines(text, 8) or _sentences(text, 8)
    selling_points = []
    for item in candidates:
        if len(item) > 80:
            item = item[:77] + "..."
        if item not in selling_points:
            selling_points.append(item)
        if len(selling_points) >= 5:
            break
    if not selling_points and compact:
        selling_points = [compact[:80]]
    return {"brief": compact[:500], "selling_points": selling_points}


def _load_text_input(value: Optional[str]) -> Dict[str, str]:
    if not value:
        return {"content": "", "source": ""}
    candidate = Path(value)
    if candidate.exists() and candidate.is_file():
        return {
            "content": candidate.read_text(encoding="utf-8", errors="replace"),
            "source": str(candidate.resolve()),
        }
    return {"content": value, "source": "inline"}


def ingest_product(product_id: str, text: Optional[str], images: Optional[List[str]] = None) -> Dict[str, Any]:
    base = ensure_product(product_id)
    loaded = _load_text_input(text)
    stamp = timestamp()
    sources = []

    if loaded["content"]:
        raw_path = base / "raw" / "product-inputs" / f"{stamp}-input.md"
        raw_path.write_text(loaded["content"], encoding="utf-8")
        sources.append(str(raw_path.relative_to(base)))
        _register_source(base, "raw_input", str(raw_path.relative_to(base)), "medium", loaded["source"])

    image_entries = []
    for item in images or []:
        if not item:
            continue
        src = Path(item)
        if src.exists() and src.is_file():
            dest = base / "raw" / "product-images" / f"{stamp}-{src.name}"
            shutil.copy2(src, dest)
            image_entries.append({"source": str(src.resolve()), "stored": str(dest.relative_to(base))})
            sources.append(str(dest.relative_to(base)))
            _register_source(base, "product_image", str(dest.relative_to(base)), "medium", str(src.resolve()))
        else:
            image_entries.append({"source": item, "stored": "", "missing": True})

    state = read_product_state(base)
    summary = _summarize_source(loaded["content"])
    if summary["brief"]:
        state.setdefault("basic", {})["brief"] = summary["brief"]
    if summary["selling_points"]:
        product_name = str(state.get("name") or "").strip()
        clean_points = generation_safe_list([
            point for point in summary["selling_points"]
            if point not in {product_name, base.name}
        ] or summary["selling_points"], limit=6, max_chars=80)
        state["selling_points"] = [
            point for point in clean_points
            if point not in {product_name, base.name}
        ] or clean_points
    if loaded["content"]:
        style = state.setdefault("style_preferences", {})
        if "高级" in loaded["content"] or "质感" in loaded["content"]:
            style.setdefault("visual_tone", "高级感、可信、克制")
        if "不要过度促销" in loaded["content"] or "不要太促销" in loaded["content"]:
            style.setdefault("promotion_intensity", "低促销感")
    state.setdefault("sources", [])
    state["sources"].extend(s for s in sources if s not in state["sources"])
    state["updated_at"] = now_iso()
    state["status"] = "draft"
    state.setdefault("assets", {})["images"] = image_entries
    state = apply_generation_safe_state(state)
    brain_documents(base).save_state(state)
    build_product_fingerprint(base.name)

    render_product_pages(base, state)
    update_index_and_log(base, "ingest", "Product source material", sources or ["No source content saved"])
    return {
        "success": True,
        "product_id": base.name,
        "sources": sources,
        "image_count": len(image_entries),
        "product_state": str(product_state_path(base)),
    }


