"""Feedback repository for Product Creative store compatibility."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ...brain.provenance import register_source as _register_source
from ...common import append_jsonl, ensure_product, now_iso, timestamp, update_index_and_log
from ...ports.runtime_repositories import artifacts


__all__ = [
    "record_feedback",
    "read_channel_feedback_entries",
    "read_feedback_entries",
    "read_material_feedback_entries",
    "read_result_evaluation_entries",
    "read_result_feedback_entries",
    "read_video_brief_feedback_entries",
    "read_visual_alignment_entries",
]


def record_feedback(
    product_id: str,
    artifact_id: str,
    note: str,
    selected: bool = False,
    variant: Optional[int] = None,
    rating: Optional[int] = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    feedback_id = f"feedback-{timestamp()}"
    clean_rating = None
    if rating is not None:
        clean_rating = max(1, min(int(rating), 5))
    payload = {
        "feedback_id": feedback_id,
        "artifact_id": artifact_id,
        "note": note or "",
        "selected": bool(selected),
        "variant": int(variant) if variant else None,
        "rating": clean_rating,
        "created_at": now_iso(),
    }
    raw_path = base / "raw" / "user-feedback" / f"{feedback_id}.md"
    raw_path.write_text(
        f"""# {feedback_id}

Artifact: {artifact_id}
Selected: {bool(selected)}
Variant: {payload["variant"] or ""}
Rating: {payload["rating"] or ""}

## Note

{note or ""}
""",
        encoding="utf-8",
    )
    source_id = _register_source(base, "feedback", str(raw_path.relative_to(base)), "medium", feedback_id)
    payload["source_id"] = source_id
    append_jsonl(base / "structured" / "feedback.jsonl", payload)
    artifacts().save(
        base.name,
        feedback_id,
        "feedback",
        str(raw_path.relative_to(base)),
        payload,
    )
    update_index_and_log(base, "feedback", feedback_id, [str(raw_path.relative_to(base))])
    return {"success": True, "product_id": base.name, "feedback_id": feedback_id, "feedback_path": str(raw_path)}


def read_feedback_entries(base: Path) -> List[Dict[str, Any]]:
    return artifacts().list(base.name, "feedback")


def read_result_feedback_entries(base: Path) -> List[Dict[str, Any]]:
    return artifacts().list(base.name, "result_feedback")


def read_material_feedback_entries(base: Path) -> List[Dict[str, Any]]:
    return artifacts().list(base.name, "material_feedback")


def read_result_evaluation_entries(base: Path) -> List[Dict[str, Any]]:
    entries = artifacts().list(base.name, "result_evaluations")
    entries.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("result_evaluation_id") or "")))
    return entries


def _latest_result_evaluation_for_feedback(base: Path, feedback: Dict[str, Any]) -> Dict[str, Any]:
    result_id = str(feedback.get("source_result_id") or feedback.get("result_id") or "")
    feedback_id = str(feedback.get("feedback_id") or "")
    matches = []
    for item in read_result_evaluation_entries(base):
        if feedback_id and item.get("source_feedback_id") == feedback_id:
            matches.append(item)
        elif result_id and item.get("source_result_id") == result_id:
            matches.append(item)
    return matches[-1] if matches else {}


def read_channel_feedback_entries(base: Path) -> List[Dict[str, Any]]:
    return artifacts().list(base.name, "channel_feedback")


def read_video_brief_feedback_entries(base: Path) -> List[Dict[str, Any]]:
    return artifacts().list(base.name, "video_brief_feedback")


def read_visual_alignment_entries(base: Path) -> List[Dict[str, Any]]:
    entries = artifacts().list(base.name, "visual_alignments")
    entries.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("alignment_id") or "")))
    return entries


