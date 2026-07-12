"""Application service for reusable rule lifecycle operations."""

from __future__ import annotations

from typing import Any, Dict, List

from ..domain.learning import LearningThresholds, rule_is_proposal_eligible
from ..ports.runtime_repositories import rules


class LearningService:
    def __init__(self, repository=None):
        self._repository = repository or rules()

    def eligible_rules(self, product_id: str, thresholds: LearningThresholds = LearningThresholds()) -> List[Dict[str, Any]]:
        rules = self._repository.eligible(
            product_id,
            thresholds.minimum_samples,
            thresholds.minimum_confidence,
        )
        return [rule for rule in rules if rule_is_proposal_eligible(rule, thresholds)]

    def decay(self, product_id: str, factor: float = 0.95) -> int:
        return self._repository.decay(product_id, factor)

    def revoke(self, product_id: str, rule_id: str, reason: str) -> bool:
        return self._repository.revoke(product_id, rule_id, reason)
