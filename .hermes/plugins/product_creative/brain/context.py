"""Product Brain context-pack assembly for generation and review workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..context_safety import apply_generation_safe_state


CONTEXT_PROFILES: Dict[str, List[str]] = {
    "product-copy-pack": [
        "SCHEMA.md",
        "index.md",
        "product/Product.md",
        "product/positioning.md",
        "product/selling-points.md",
        "product/brand-voice.md",
        "channels/ecommerce.md",
        "content-patterns/proven-patterns.md",
        "compliance/forbidden-claims.md",
    ],
    "image-brief": [
        "SCHEMA.md",
        "product/Product.md",
        "product/selling-points.md",
        "product/visual-identity.md",
        "channels/ecommerce-main-image.md",
        "content-patterns/visual-patterns.md",
        "compliance/forbidden-claims.md",
    ],
    "image-generation": [
        "product/Product.md",
        "product/selling-points.md",
        "product/visual-identity.md",
        "channels/ecommerce-main-image.md",
        "content-patterns/visual-patterns.md",
        "content-patterns/failed-patterns.md",
        "compliance/forbidden-claims.md",
    ],
    "ecommerce-main-image-copy": [
        "SCHEMA.md",
        "product/Product.md",
        "product/selling-points.md",
        "product/visual-identity.md",
        "channels/ecommerce-main-image.md",
        "content-patterns/proven-patterns.md",
        "content-patterns/failed-patterns.md",
        "compliance/forbidden-claims.md",
    ],
    "xiaohongshu-seeding-note": [
        "SCHEMA.md",
        "product/Product.md",
        "product/selling-points.md",
        "product/brand-voice.md",
        "content-patterns/proven-patterns.md",
        "content-patterns/failed-patterns.md",
        "compliance/forbidden-claims.md",
    ],
    "douyin-short-video-script": [
        "SCHEMA.md",
        "product/Product.md",
        "product/selling-points.md",
        "channels/douyin.md",
        "product/visual-identity.md",
        "content-patterns/visual-patterns.md",
        "content-patterns/video-patterns.md",
        "content-patterns/proven-patterns.md",
        "content-patterns/failed-patterns.md",
        "compliance/forbidden-claims.md",
    ],
    "feedback-evolution": [
        "product/Product.md",
        "product/selling-points.md",
        "product/visual-identity.md",
        "content-patterns/visual-patterns.md",
        "content-patterns/video-patterns.md",
        "content-patterns/proven-patterns.md",
        "content-patterns/failed-patterns.md",
        "compliance/forbidden-claims.md",
    ],
}


def build_context_pack(
    base: Path,
    product_id: str,
    target: str,
    state: Dict[str, Any],
    lint: Dict[str, Any],
) -> Dict[str, Any]:
    context_profile = target if target in CONTEXT_PROFILES else "product-copy-pack"
    pages = CONTEXT_PROFILES[context_profile]
    content: Dict[str, str] = {}
    for page in pages:
        path = base / "wiki" / page
        if path.exists():
            content[page] = path.read_text(encoding="utf-8")
    errors = lint.get("errors") if isinstance(lint.get("errors"), list) else []
    warnings = lint.get("warnings") if isinstance(lint.get("warnings"), list) else []
    return {
        "success": True,
        "product_id": product_id,
        "target": target,
        "context_profile": context_profile,
        "state": apply_generation_safe_state(state),
        "pages": content,
        "page_list": list(content.keys()),
        "lint_summary": {
            "success": bool(lint.get("success")),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }
