"""Pure learning eligibility and risk policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class LearningThresholds:
    minimum_samples: int = 2
    minimum_confidence: float = 0.68


def rule_is_proposal_eligible(rule: Dict[str, Any], thresholds: LearningThresholds = LearningThresholds()) -> bool:
    return (
        str(rule.get("status") or "") in {"candidate", "approved"}
        and int(rule.get("sample_size") or 0) >= thresholds.minimum_samples
        and float(rule.get("confidence") or 0) >= thresholds.minimum_confidence
        and not bool((rule.get("conditions") or {}).get("conflicts_with"))
    )
