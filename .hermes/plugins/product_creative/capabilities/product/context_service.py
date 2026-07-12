"""Product Brain context projection service."""

from typing import Any, Dict

from ...common import ensure_product, read_product_state
from ...brain.context import build_context_pack
from ...brain.wiki import wiki_lint_product


def context_pack(product_id: str, target: str = "product-copy-pack") -> Dict[str, Any]:
    base = ensure_product(product_id)
    state = read_product_state(base)
    lint = wiki_lint_product(base.name, write_report=False)
    return build_context_pack(base, base.name, target, state, lint)
