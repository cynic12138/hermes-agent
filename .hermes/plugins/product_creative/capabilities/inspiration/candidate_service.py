"""Inspiration candidate mining service."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json

from .shared import _list, _rel, _safe_limit, _sanitize_string, _text
from .collection_service import _resolve_snapshot

INSPIRATION_SIGNAL_SCHEMA_VERSION = "product_creative.inspiration_signal.v6.6"

INSPIRATION_CANDIDATE_SCHEMA_VERSION = "product_creative.inspiration_candidate.v6.6"

def _tokens(text: str) -> List[str]:
    return [item for item in re.split(r"[\s,，。！？!?.;；:：、｜|/\\()（）【】\[\]\"']+", text.lower()) if len(item) >= 2]

def _product_terms(state: Dict[str, Any]) -> List[str]:
    terms = _tokens(_text(state.get("name")))
    for item in _list(state.get("selling_points")):
        terms.extend(_tokens(str(item)))
    return list(dict.fromkeys(terms))

def _extract_signals(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    title = _text(item.get("title"))
    text = _text(item.get("text"))
    analysis = item.get("copy_analysis") if isinstance(item.get("copy_analysis"), dict) else {}
    signals: List[Dict[str, Any]] = []
    for key, signal_type in [
        ("opening_hook", "hook"),
        ("pain_points", "pain_point"),
        ("selling_points", "selling_point"),
        ("calls_to_action", "cta"),
        ("replicable_formula", "script_structure"),
    ]:
        value = analysis.get(key)
        if isinstance(value, list):
            for entry in value[:3]:
                if str(entry).strip():
                    signals.append({"signal_type": signal_type, "text": _sanitize_string(entry, 240)})
        elif isinstance(value, str) and value.strip():
            signals.append({"signal_type": signal_type, "text": _sanitize_string(value, 240)})
    if title:
        signals.append({"signal_type": "hook", "text": title})
    if text:
        first = re.split(r"[。！？!?\n]", text)[0]
        if first.strip():
            signals.append({"signal_type": "scene", "text": _sanitize_string(first, 240)})
    return signals[:8]

def _fit_score(product_terms: List[str], item: Dict[str, Any]) -> Dict[str, Any]:
    blob = f"{item.get('title', '')} {item.get('text', '')}".lower()
    hits = [term for term in product_terms if term and term.lower() in blob]
    score = min(1.0, 0.35 + len(hits) * 0.15) if blob else 0.2
    if not hits and product_terms:
        return {"score": 0.45, "hits": [], "reason": "No direct term hit; usable only as channel expression or creative format inspiration."}
    return {"score": score, "hits": hits[:8], "reason": "Matches product terms or selling-point vocabulary."}

def _candidate_markdown(candidate: Dict[str, Any]) -> str:
    lines = [
        f"# {candidate['candidate_id']}",
        "",
        f"Channel: {candidate['channel']}",
        f"Usable for: {', '.join(candidate.get('usable_for') or [])}",
        f"Confidence: {candidate['confidence']}",
        "",
        "## Angle",
        "",
        candidate.get("angle", ""),
        "",
        "## Hook",
        "",
        candidate.get("hook", ""),
        "",
        "## Product Fit",
        "",
        candidate.get("product_fit_reason", ""),
        "",
        "## Risks",
        "",
    ]
    lines.extend([f"- {item}" for item in candidate.get("risks", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def create_inspiration_candidates(
    product_id: str,
    snapshot: str,
    goal: str = "",
    max_candidates: int = 5,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    source = _resolve_snapshot(base, snapshot)
    state = read_product_state(base)
    product_name = _text(state.get("name")) or base.name
    product_terms = _product_terms(state)
    channel = _text(source.get("channel")) or "web"
    clean_goal = _text(goal) or f"{channel} creative inspiration"
    candidates: List[Dict[str, Any]] = []
    signal_paths: List[str] = []
    max_count = _safe_limit(max_candidates, 5, 10)
    signal_dir = base / "artifacts" / "inspiration_signals"
    candidate_dir = base / "artifacts" / "inspiration_candidates"

    for item in _list(source.get("items")):
        if len(candidates) >= max_count:
            break
        if not isinstance(item, dict):
            continue
        fit = _fit_score(product_terms, item)
        signals = _extract_signals(item)
        signal_ids = []
        for signal in signals[:3]:
            signal_id = f"inspiration-signal-{timestamp()}-{len(signal_ids) + len(candidates) + 1}"
            signal_doc = {
                "schema_version": INSPIRATION_SIGNAL_SCHEMA_VERSION,
                "signal_id": signal_id,
                "product_id": base.name,
                "snapshot_id": source.get("snapshot_id"),
                "created_at": now_iso(),
                "channel": channel,
                "signal_type": signal["signal_type"],
                "text": signal["text"],
                "evidence": item.get("title") or item.get("url") or "",
                "confidence": fit["score"],
                "not_product_fact": True,
            }
            signal_json = signal_dir / f"{signal_id}.json"
            write_json(signal_json, signal_doc)
            append_jsonl(
                base / "structured" / "inspiration_signal_index.jsonl",
                {
                    "signal_id": signal_id,
                    "created_at": signal_doc["created_at"],
                    "snapshot_id": source.get("snapshot_id"),
                    "channel": channel,
                    "signal_type": signal["signal_type"],
                    "path": _rel(base, signal_json),
                },
            )
            signal_ids.append(signal_id)
            signal_paths.append(str(signal_json))
        primary_signal = signals[0]["text"] if signals else _text(item.get("title")) or "外部内容结构"
        candidate_id = f"inspiration-candidate-{timestamp()}-{len(candidates) + 1}"
        hook = primary_signal
        title = _text(item.get("title"))
        text = _text(item.get("text"))
        candidate = {
            "schema_version": INSPIRATION_CANDIDATE_SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "product_id": base.name,
            "created_at": now_iso(),
            "source_snapshot_ids": [source.get("snapshot_id")],
            "signal_ids": signal_ids,
            "channel": channel,
            "goal": clean_goal,
            "usable_for": ["copy", "image_brief", "video_brief"],
            "angle": f"把外部灵感“{hook}”转成 {product_name} 的渠道表达。",
            "hook": hook,
            "scene": _sanitize_string(text or title, 220),
            "visual_direction": f"围绕 {product_name} 保持产品主体真实，以外部素材的场景/节奏作为参考，不复制外部产品事实。",
            "script_structure": "开场钩子 -> 产品事实锚定 -> 场景/情绪表达 -> 轻 CTA",
            "product_relevance_score": fit["score"],
            "product_fit_reason": fit["reason"],
            "matched_terms": fit["hits"],
            "risks": [
                "not_product_fact",
                "Do not copy competitor claims or unverified platform facts.",
                "Use as creative format only until human feedback confirms effectiveness.",
            ],
            "confidence": round(float(fit["score"]), 2),
            "not_product_fact": True,
            "requires_confirmation_for_playbook": True,
            "mutates_product_brain": False,
        }
        candidate_json = candidate_dir / f"{candidate_id}.json"
        candidate_md = candidate_dir / f"{candidate_id}.md"
        write_json(candidate_json, candidate)
        candidate_md.parent.mkdir(parents=True, exist_ok=True)
        candidate_md.write_text(_candidate_markdown(candidate), encoding="utf-8")
        append_jsonl(
            base / "structured" / "inspiration_candidate_index.jsonl",
            {
                "candidate_id": candidate_id,
                "created_at": candidate["created_at"],
                "snapshot_id": source.get("snapshot_id"),
                "channel": channel,
                "confidence": candidate["confidence"],
                "path": _rel(base, candidate_json),
            },
        )
        candidates.append(candidate)

    update_index_and_log(
        base,
        "inspiration-candidates",
        source.get("snapshot_id", "snapshot"),
        [f"Created candidates: {len(candidates)}", f"Channel: {channel}"],
    )
    return {
        "success": True,
        "schema_version": INSPIRATION_CANDIDATE_SCHEMA_VERSION,
        "product_id": base.name,
        "snapshot_id": source.get("snapshot_id"),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "signal_files": signal_paths,
        "mutates_product_brain": False,
    }

def _resolve_candidate(base: Path, value: str) -> Dict[str, Any]:
    path = base / "artifacts" / "inspiration_candidates" / f"{value}.json"
    if path.exists():
        return read_json(path, {})
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("candidate path must stay inside the product workspace")
        return read_json(resolved, {})
    raise FileNotFoundError(f"inspiration candidate '{value}' does not exist")
