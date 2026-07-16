"""Strict capability-constrained goal planner with deterministic fallback."""

from __future__ import annotations

from typing import Any, Callable, Dict

from ..capabilities.registry import action_descriptors, workflow_fragments
from ..contracts.durable import GoalPlan, GoalPlanStep, Observation
from ..contracts.models import CreativeTaskPlanStep, CreativeTaskRequest, IntentDecision


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

    def creative_task_actions(self, request: CreativeTaskRequest) -> list[CreativeTaskPlanStep]:
        """Build a bounded cross-domain plan from the existing capability registry."""

        candidates: list[tuple[str, str, str]] = []
        if request.requires_fresh_inspiration:
            candidates.extend(
                [
                    ("RESEARCHING", "collect_external_source_snapshot", "task_authorization"),
                    ("RESEARCHING", "create_inspiration_candidates", ""),
                    ("IDEATING", "create_inspiration_pack", ""),
                ]
            )
        if any(item in request.deliverables for item in ("image", "video")):
            candidates.append(("PREPARING_ASSETS", "prepare_task_material_pack", ""))
        if "text" in request.deliverables:
            candidates.append(("IDEATING", "run_channel_review", ""))
        if "image" in request.deliverables:
            candidates.extend(
                [
                    ("IDEATING", "resolve_image_intent", ""),
                    ("IDEATING", "create_image_brief", ""),
                    ("IDEATING", "review_image_brief", ""),
                    ("GENERATING", "create_batch_generation_policy", "human_confirmation"),
                    ("GENERATING", "build_image_provider_payload", ""),
                    ("GENERATING", "check_image_live_readiness", "provider_readiness"),
                    ("GENERATING", "submit_image_generation_job", "task_authorization"),
                ]
            )
        if "video" in request.deliverables:
            if request.preserve_exact_packaging:
                candidates.append(("GENERATING", "compose_exact_main_video", ""))
            else:
                candidates.extend(
                    [
                        ("IDEATING", "resolve_video_intent", ""),
                        ("IDEATING", "create_video_brief", ""),
                        ("IDEATING", "review_video_brief", ""),
                        ("GENERATING", "build_video_provider_payload", ""),
                        ("GENERATING", "check_video_reference_readiness", "provider_readiness"),
                        ("GENERATING", "check_video_live_readiness", "provider_readiness"),
                        ("GENERATING", "create_video_execution_policy", "human_confirmation"),
                        ("GENERATING", "submit_video_generation_task", "task_authorization"),
                        ("GENERATING", "check_video_task_status", "task_authorization"),
                    ]
                )
        if request.deliverables:
            candidates.append(("DELIVERING", "create_task_overview_package", ""))
        if any(item in request.deliverables for item in ("image", "video")):
            candidates.append(("DELIVERING", "review_generated_result", ""))

        allowed = action_descriptors()
        unknown = [action for _, action, _ in candidates if action not in allowed]
        if unknown:
            raise ValueError(f"creative task plan contains unknown capabilities: {unknown}")
        if len(candidates) > 24:
            raise ValueError("creative task plan exceeds the 24 action safety bound")
        return [
            CreativeTaskPlanStep(stage=stage, action=action, guard=guard)
            for stage, action, guard in candidates
        ]

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
