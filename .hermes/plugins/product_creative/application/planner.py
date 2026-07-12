"""Strict capability-constrained goal planner with deterministic fallback."""

from __future__ import annotations

from typing import Any, Callable, Dict

from ..capabilities.registry import action_descriptors, workflow_fragments
from ..contracts.durable import GoalPlan, GoalPlanStep, Observation
from ..contracts.models import IntentDecision


StructuredPlanner = Callable[[Dict[str, Any]], Dict[str, Any]]


class GoalPlanner:
    def __init__(self, llm: StructuredPlanner | None = None):
        self._llm = llm

    def plan(self, decision: IntentDecision, observation: Observation) -> GoalPlan:
        if self._llm is not None:
            try:
                candidate = GoalPlan.model_validate(
                    self._llm(
                        {
                            "decision": decision.model_dump(mode="json"),
                            "observation": observation.model_dump(mode="json"),
                            "allowed_commands": sorted(action_descriptors()),
                        }
                    )
                )
                self.validate(candidate, observation)
                candidate.planner = "llm"
                return candidate
            except Exception:
                pass
        return self.deterministic(decision, observation)

    def deterministic(self, decision: IntentDecision, observation: Observation) -> GoalPlan:
        descriptors = action_descriptors()
        if decision.action not in descriptors:
            raise ValueError(f"planner cannot select unknown action '{decision.action}'")
        actions = (decision.action,)
        for workflow in workflow_fragments():
            if decision.action in workflow.actions:
                actions = workflow.actions[workflow.actions.index(decision.action) :]
                break
        steps = [
            GoalPlanStep(
                command=action,
                goal=decision.goal,
                payload={"product_id": decision.product_id},
                success_criteria=[f"{action} completes with a durable receipt"],
                requires_confirmation=descriptors[action].requires_explicit_confirmation
                or descriptors[action].mutates_confirmed_product_brain,
            )
            for action in actions[:10]
        ]
        plan = GoalPlan(
            product_id=decision.product_id,
            goal=decision.goal or decision.action,
            modality=decision.modality,
            target=decision.target,
            constraints=decision.constraints,
            evidence_ids=observation.evidence_ids,
            steps=steps,
            missing_inputs=decision.missing_inputs,
            confidence=decision.confidence,
            planner="deterministic",
        )
        self.validate(plan, observation)
        return plan

    @staticmethod
    def validate(plan: GoalPlan, observation: Observation) -> None:
        allowed = action_descriptors()
        if plan.product_id != observation.product_id:
            raise ValueError("plan product does not match observation")
        if not plan.steps or len(plan.steps) > 10:
            raise ValueError("plan must contain 1..10 steps")
        unknown = [step.command for step in plan.steps if step.command not in allowed]
        if unknown:
            raise ValueError(f"plan contains unknown capabilities: {unknown}")
        if plan.replan_count > 2:
            raise ValueError("replan limit exceeded")
