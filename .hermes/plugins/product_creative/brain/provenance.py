"""Product Brain source provenance and fingerprint helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from ..common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, write_json
from ..ports.runtime_repositories import artifacts


SOURCE_REGISTRY_SCHEMA_VERSION = "product_creative.source_registry.v1"
PRODUCT_FINGERPRINT_SCHEMA_VERSION = "product_creative.product_fingerprint.v1"

__all__ = [
    "PRODUCT_FINGERPRINT_SCHEMA_VERSION",
    "SOURCE_REGISTRY_SCHEMA_VERSION",
    "build_product_fingerprint",
    "fingerprint_guard_keywords",
    "known_source_ids",
    "read_product_fingerprint",
    "read_source_entries",
    "register_source",
    "source_ids_for_page",
    "source_ids_in_text",
    "source_index_path",
]


def source_index_path(base: Path) -> Path:
    return base / "structured" / "source_index.jsonl"


def read_source_entries(base: Path) -> List[Dict[str, Any]]:
    return artifacts().list(base.name, "source_registry")


def register_source(
    base: Path,
    source_type: str,
    path: str,
    confidence: str = "medium",
    note: str = "",
) -> str:
    entries = read_source_entries(base)
    for entry in entries:
        if entry.get("source_type") == source_type and entry.get("path") == path:
            return str(entry.get("source_id"))
    source_id = f"source-{timestamp()}-{len(entries) + 1}"
    payload = {
        "schema_version": SOURCE_REGISTRY_SCHEMA_VERSION,
        "source_id": source_id,
        "source_type": source_type,
        "product_id": base.name,
        "path": path,
        "created_at": now_iso(),
        "confidence": confidence,
        "note": note,
    }
    append_jsonl(source_index_path(base), payload)
    artifacts().save(base.name, source_id, "source_registry", "structured/source_index.jsonl", payload)
    return source_id


def known_source_ids(base: Path) -> Dict[str, Dict[str, Any]]:
    return {str(item.get("source_id")): item for item in read_source_entries(base) if item.get("source_id")}


def source_ids_in_text(text: str) -> List[str]:
    ids = []
    for item in re.findall(r"source-[0-9]{8}-[0-9]{6}-[0-9]+", text):
        if item not in ids:
            ids.append(item)
    return ids


def source_ids_for_page(base: Path, text: str) -> List[str]:
    ids = source_ids_in_text(text)
    known = known_source_ids(base)
    return [item for item in ids if item in known]


def keywords_from_text(text: str, limit: int = 8) -> List[str]:
    pieces = re.split(r"[，,、；;。！？!?\s\n]+", text)
    blocked = {
        "待补充",
        "No",
        "canonical",
        "insight",
        "yet",
        "source",
        "Product",
        "Wiki",
        "title",
        "type",
        "product_id",
        "status",
        "draft",
        "confidence",
        "sources",
        "created_at",
        "updated_at",
        "product_profile",
        "channel_playbook",
        "content_pattern",
    }
    items = []
    for piece in pieces:
        item = piece.strip(" -:：[]()（）|")
        if len(item) < 2 or item in blocked:
            continue
        if re.fullmatch(r"\d+", item):
            continue
        if item not in items:
            items.append(item)
        if len(items) >= limit:
            break
    return items


def build_product_fingerprint(product_id: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    state = read_product_state(base)
    texts = [
        str(state.get("name") or base.name),
        str(state.get("basic", {}).get("brief") or ""),
        " ".join(str(item) for item in state.get("selling_points", [])),
    ]
    for rel in ["product/Product.md", "product/selling-points.md", "product/positioning.md"]:
        path = base / "wiki" / rel
        if path.exists():
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
    keywords = []
    for text in texts:
        for item in keywords_from_text(text):
            if item not in keywords:
                keywords.append(item)
        if len(keywords) >= 12:
            break
    fingerprint = {
        "schema_version": PRODUCT_FINGERPRINT_SCHEMA_VERSION,
        "product_id": base.name,
        "created_at": now_iso(),
        "name": state.get("name") or base.name,
        "keywords": keywords[:12],
        "source": "product_state_and_wiki",
    }
    path = base / "structured" / "product_fingerprint.json"
    write_json(path, fingerprint)
    return {"success": True, "product_id": base.name, "files": {"json": str(path)}, "fingerprint": fingerprint}


def read_product_fingerprint(base: Path) -> Dict[str, Any]:
    path = base / "structured" / "product_fingerprint.json"
    if not path.exists():
        return build_product_fingerprint(base.name)["fingerprint"]
    return read_json(path, {})


def fingerprint_guard_keywords(fingerprint: Dict[str, Any]) -> List[str]:
    blocked = {
        "高级感",
        "低促销感",
        "可信",
        "克制",
        "产品",
        "卖点",
        "主图",
        "文案",
        "用户",
        "视觉",
        "title",
        "type",
        "product_id",
        "status",
        "draft",
        "confidence",
        "sources",
        "created_at",
        "updated_at",
        "product_profile",
        "channel_playbook",
        "content_pattern",
        "Product",
        "Core",
        "State",
        "Wiki",
        "created",
        "updated",
        "product",
        "Selling",
        "Points",
        "One-Liner",
    }
    values = []
    product_id = str(fingerprint.get("product_id") or "").strip()
    if product_id:
        values.append(product_id)
    raw_values = [str(fingerprint.get("name") or "")] + [str(item) for item in fingerprint.get("keywords", [])]
    for value in raw_values:
        item = value.strip()
        if not item or item in blocked:
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", item):
            continue
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", item):
            continue
        if len(item) < 4:
            continue
        if item not in values:
            values.append(item)
    return values


