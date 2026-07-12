"""Observe/plan/policy controller for the AI-driven runtime."""

from __future__ import annotations

from ..capabilities.registry import action_descriptors
from ..contracts.durable import CommandEnvelope, GoalPlan, Observation, PolicyDecision
from ..contracts.models import IntentDecision
from .observer import RuntimeObserver
from .planner import GoalPlanner
from .policy import PolicyEngine


class AgentRuntimeController:
    def __init__(
        self,
        observer: RuntimeObserver | None = None,
        planner: GoalPlanner | None = None,
        policy: PolicyEngine | None = None,
    ):
        self._observer = observer or RuntimeObserver()
        self._planner = planner or GoalPlanner()
        self._policy = policy or PolicyEngine()

    def prepare(self, decision: IntentDecision, confirmed: bool = False) -> tuple[Observation, GoalPlan, PolicyDecision]:
        observation = self._observer.observe(decision.product_id)
        plan = self._planner.plan(decision, observation)
        first = plan.steps[0]
        descriptor = action_descriptors()[first.command]
        policy = self._policy.authorize(
            descriptor,
            CommandEnvelope(
                command=first.command,
                product_id=decision.product_id,
                confirmed=confirmed,
                payload=first.payload,
            ),
        )
        return observation, plan, policy

    def replan(self, decision: IntentDecision, previous: GoalPlan, trigger: str) -> GoalPlan:
        if trigger not in {"input_changed", "step_failed", "provider_changed", "version_conflict"}:
            raise ValueError(f"unsupported replan trigger '{trigger}'")
        if previous.replan_count >= 2:
            raise RuntimeError("replan limit reached; human review required")
        observation = self._observer.observe(decision.product_id)
        plan = self._planner.plan(decision, observation)
        plan.replan_count = previous.replan_count + 1
        return plan
