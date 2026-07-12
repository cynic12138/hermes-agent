from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import read_json

def _resolve_artifact_path(base: Path, artifact: str) -> Path:
    if not artifact:
        raise ValueError("artifact id or path is required")

    candidate = Path(artifact)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("artifact path must stay inside the product workspace")
        return resolved

    name = artifact if artifact.endswith(".json") else f"{artifact}.json"
    path = base / "artifacts" / "copy" / name
    if path.exists():
        return path.resolve()

    raise FileNotFoundError(f"artifact '{artifact}' does not exist")

def _resolve_channel_artifact_path(base: Path, artifact: str) -> Path:
    if not artifact:
        raise ValueError("artifact id or path is required")

    candidate = Path(artifact)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("artifact path must stay inside the product workspace")
        return resolved

    name = artifact if artifact.endswith(".json") else f"{artifact}.json"
    path = base / "artifacts" / "channel_content" / name
    if path.exists():
        return path.resolve()

    raise FileNotFoundError(f"channel artifact '{artifact}' does not exist")

def _clip_score(value: int) -> int:
    return max(0, min(100, value))

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _score_text_length(text: str, low: int, high: int, points: int) -> Tuple[int, str]:
    length = len(text)
    if low <= length <= high:
        return points, ""
    if length == 0:
        return 0, "missing"
    return max(1, points // 2), f"length {length} outside {low}-{high}"

def _variant_grounding_issues(artifact: Dict[str, Any], variant: int) -> List[Dict[str, Any]]:
    warnings = artifact.get("grounding_audit", {}).get("warnings") or []
    return [item for item in warnings if item.get("variant") in {variant, str(variant), None}]
