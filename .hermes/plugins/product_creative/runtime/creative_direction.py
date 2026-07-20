"""Professional creative direction, story expansion, production planning, and QA."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable

from ..common import ensure_product, now_iso, read_product_state
from ..context_safety import apply_generation_safe_state
from ..contracts.creative_artifacts import (
    CreativeCandidateArtifact,
    CreativeDecisionArtifact,
    ProductionBibleArtifact,
    QaReportArtifact,
    ResearchInsightPackArtifact,
    StoryPackageArtifact,
)
from ..contracts.models import CreativeTaskRecord, requires_exact_packaging
from ..ports.runtime_repositories import artifacts
from .business_skills import execute_business_skill
from .professional_artifacts import (
    ensure_product_grounding_pack,
    ensure_research_insight_pack,
    load_professional_artifact,
    persist_professional_task_checkpoint,
    professional_revision_suffix,
    record_business_skill_execution,
    record_failed_business_skill_execution,
    save_professional_artifact,
)


_SIMILARITY_MODIFIERS = (
    "快速",
    "迅速",
    "忽然",
    "突然",
    "瞬间",
    "立刻",
    "马上",
    "轻松",
    "温柔",
    "克制",
    "小小",
    "小",
)


def _structural_ngrams(value: Any) -> set[str]:
    if isinstance(value, list):
        text = "|".join(str(item) for item in value)
    else:
        text = str(value or "")
    normalized = re.sub(r"[\W_]+", "", text.lower())
    for modifier in _SIMILARITY_MODIFIERS:
        normalized = normalized.replace(modifier, "")
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def _dice_similarity(left: Any, right: Any) -> float:
    left_grams = _structural_ngrams(left)
    right_grams = _structural_ngrams(right)
    if not left_grams and not right_grams:
        return 1.0
    if not left_grams or not right_grams:
        return 0.0
    return (2.0 * len(left_grams & right_grams)) / (
        len(left_grams) + len(right_grams)
    )


def _candidate_similarity(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    weighted = (
        _dice_similarity(left.get("hook"), right.get("hook")) * 0.25
        + _dice_similarity(left.get("conflict"), right.get("conflict")) * 0.25
        + _dice_similarity(left.get("progression"), right.get("progression")) * 0.25
        + _dice_similarity(left.get("product_role"), right.get("product_role")) * 0.15
        + _dice_similarity(left.get("ending"), right.get("ending")) * 0.10
    )
    return round(min(1.0, max(0.0, weighted)), 3)


def historical_similarity_against(
    candidate: Dict[str, Any],
    historical_candidates: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    scored = []
    for historical in historical_candidates:
        artifact_id = str(historical.get("artifact_id") or "")
        if not artifact_id or artifact_id == str(candidate.get("artifact_id") or ""):
            continue
        scored.append(
            {
                "artifact_id": artifact_id,
                "score": _candidate_similarity(candidate, historical),
            }
        )
    if not scored:
        return {"score": 0.0, "similar_artifact_ids": []}
    scored.sort(key=lambda item: (item["score"], item["artifact_id"]), reverse=True)
    maximum = scored[0]["score"]
    return {
        "score": maximum,
        "similar_artifact_ids": [
            item["artifact_id"]
            for item in scored
            if maximum - item["score"] <= 0.01
        ],
    }


def _execute_recorded_skill(
    task: CreativeTaskRecord,
    *,
    skill_name: str,
    input_payload: Dict[str, Any],
    expected_output_schema: Dict[str, Any],
    input_artifacts: list[Any],
    actual_actions: list[str],
):
    try:
        return execute_business_skill(
            skill_name,
            input_payload=input_payload,
            expected_output_schema=expected_output_schema,
        )
    except Exception as exc:
        record_failed_business_skill_execution(
            task,
            skill_name=skill_name,
            input_artifacts=input_artifacts,
            actual_actions=actual_actions,
            error=exc,
        )
        raise


def _product_name(task: CreativeTaskRecord) -> str:
    state = apply_generation_safe_state(
        read_product_state(ensure_product(task.product_id))
    )
    safe = state.get("generation_safe") if isinstance(state.get("generation_safe"), dict) else {}
    return str(safe.get("product_name") or state.get("name") or task.product_id)


def _creative_candidate_output_schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    text_list = {"type": "array", "items": text}
    required = [
        "direction",
        "one_liner",
        "stop_reason",
        "product_role",
        "target_emotion",
        "channel_fit",
        "hook",
        "conflict",
        "progression",
        "ending",
        "required_materials",
        "production_route",
        "risks",
        "estimated_cost",
        "feasibility",
        "historical_difference",
        "novelty_strategy",
    ]
    return {
        "type": "object",
        "required": ["candidates"],
        "additionalProperties": False,
        "properties": {
            "candidates": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": required,
                    "additionalProperties": False,
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["stable", "variation", "exploration"],
                        },
                        "one_liner": text,
                        "stop_reason": text,
                        "product_role": text,
                        "target_emotion": text,
                        "channel_fit": text,
                        "hook": text,
                        "conflict": text,
                        "progression": {
                            "type": "array",
                            "minItems": 2,
                            "items": text,
                        },
                        "ending": text,
                        "required_materials": text_list,
                        "production_route": text,
                        "risks": text_list,
                        "estimated_cost": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "feasibility": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "historical_difference": text,
                        "novelty_strategy": {"type": "string"},
                    },
                },
            }
        },
    }


def ensure_creative_candidates(
    task: CreativeTaskRecord,
    research: ResearchInsightPackArtifact,
) -> list[CreativeCandidateArtifact]:
    brief = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["creative_task_brief"],
    )
    grounding = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["product_grounding_pack"],
    )
    suffix = professional_revision_suffix(task)
    expected_ids = [
        f"candidate-{task.task_id}{suffix}-{direction}"
        for direction in ("stable", "variation", "exploration")
    ]
    existing_candidates: list[CreativeCandidateArtifact] = []
    for artifact_id in expected_ids:
        try:
            artifact = load_professional_artifact(task.product_id, artifact_id)
        except FileNotFoundError:
            existing_candidates = []
            break
        if not isinstance(artifact, CreativeCandidateArtifact):
            existing_candidates = []
            break
        existing_candidates.append(artifact)
    if len(existing_candidates) == 3:
        task.professional_artifacts["creative_candidates"] = expected_ids
        return existing_candidates
    product_name = _product_name(task)
    packaging_route = (
        "exact-main-composite"
        if task.request.preserve_exact_packaging
        else "generated-scene-with-product-reference"
    )
    required_materials = [
        str(item.get("material_id"))
        for item in task.selected_materials
        if item.get("material_id")
    ]
    historical = [
        item
        for item in artifacts().list(task.product_id, "creative_candidates")
        if str(item.get("artifact_id") or "")
        not in set(task.professional_artifacts.get("creative_candidates") or [])
    ]
    strategy_actions = ["artifact_read", "history_search", "material_read"]
    run_result = _execute_recorded_skill(
        task,
        skill_name="creative-strategy",
        input_payload={
            "task": brief.model_dump(mode="json"),
            "grounding": grounding.model_dump(mode="json"),
            "research": research.model_dump(mode="json"),
            "historical_candidates": historical[-30:],
            "product_name": product_name,
            "production_route": packaging_route,
            "required_materials": required_materials,
            "required_directions": ["stable", "variation", "exploration"],
        },
        expected_output_schema=_creative_candidate_output_schema(),
        input_artifacts=[brief, grounding, research],
        actual_actions=strategy_actions,
    )
    raw_candidates = run_result.payload.get("candidates")
    if not isinstance(raw_candidates, list) or len(raw_candidates) != 3:
        raise ValueError("creative-strategy must return exactly three candidates")
    base_refs = list(
        dict.fromkeys(
            [
                grounding.artifact_id,
                research.artifact_id,
                *research.source_refs,
            ]
        )
    )
    candidates = []
    for payload in raw_candidates:
        if not isinstance(payload, dict):
            raise ValueError("creative-strategy candidate must be an object")
        direction = str(payload.get("direction") or "")
        similarity = historical_similarity_against(payload, historical)
        candidate = CreativeCandidateArtifact.model_validate(
            {
                "artifact_id": f"candidate-{task.task_id}{suffix}-{direction}",
                "task_id": task.task_id,
                "product_id": task.product_id,
                "created_at": now_iso(),
                "source_refs": base_refs,
                "status": "READY",
                **{
                    key: payload.get(key)
                    for key in (
                        "direction",
                        "one_liner",
                        "stop_reason",
                        "product_role",
                        "target_emotion",
                        "channel_fit",
                        "hook",
                        "conflict",
                        "progression",
                        "ending",
                        "required_materials",
                        "production_route",
                        "risks",
                        "estimated_cost",
                        "feasibility",
                        "historical_difference",
                        "novelty_strategy",
                    )
                },
                "historical_similarity": similarity["score"],
                "similar_artifact_ids": similarity["similar_artifact_ids"],
            }
        )
        candidates.append(candidate)
    if {item.direction for item in candidates} != {
        "stable",
        "variation",
        "exploration",
    }:
        raise ValueError(
            "creative-strategy must return stable, variation, and exploration"
        )
    for candidate in candidates:
        save_professional_artifact(candidate)
    record_business_skill_execution(
        task,
        skill_name="creative-strategy",
        run_result=run_result,
        input_artifacts=[brief, grounding, research],
        output_artifacts=candidates,
        actual_actions=strategy_actions,
    )
    task.professional_artifacts["creative_candidates"] = [
        item.artifact_id for item in candidates
    ]
    return candidates


def _requested_candidate_direction(revision: str) -> str:
    normalized = revision.strip()
    upper = normalized.upper()
    markers = {
        "stable": ("选择A", "选A", "A方向", "A方案", "第一个方向", "第一套方案", "稳定方向"),
        "variation": ("选择B", "选B", "B方向", "B方案", "第二个方向", "第二套方案", "变化方向"),
        "exploration": ("选择C", "选C", "C方向", "C方案", "第三个方向", "第三套方案", "探索方向"),
    }
    for direction, values in markers.items():
        if any(marker in upper for marker in values):
            return direction
    return ""


def _creative_decision_output_schema(candidate_ids: list[str]) -> dict[str, Any]:
    bounded_score = {"type": "number", "minimum": 0, "maximum": 1}
    score_fields = [
        "candidate_id",
        "product_fit",
        "channel_fit",
        "freshness",
        "feasibility",
        "packaging_safety",
        "compliance_safety",
        "total",
    ]
    return {
        "type": "object",
        "required": [
            "scores",
            "selected_candidate_id",
            "selection_reason",
            "rejected_candidates",
        ],
        "additionalProperties": False,
        "properties": {
            "scores": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": score_fields,
                    "additionalProperties": False,
                    "properties": {
                        "candidate_id": {
                            "type": "string",
                            "enum": candidate_ids,
                        },
                        "product_fit": bounded_score,
                        "channel_fit": bounded_score,
                        "freshness": bounded_score,
                        "feasibility": bounded_score,
                        "packaging_safety": bounded_score,
                        "compliance_safety": bounded_score,
                        "total": bounded_score,
                    },
                },
            },
            "selected_candidate_id": {
                "type": "string",
                "enum": candidate_ids,
            },
            "selection_reason": {"type": "string", "minLength": 1},
            "rejected_candidates": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "required": ["candidate_id", "reason"],
                    "additionalProperties": False,
                    "properties": {
                        "candidate_id": {
                            "type": "string",
                            "enum": candidate_ids,
                        },
                        "reason": {"type": "string", "minLength": 1},
                    },
                },
            },
            "allowed_deviation": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
        },
    }


def _story_package_output_schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    text_list = {"type": "array", "items": text}
    return {
        "type": "object",
        "required": [
            "premise",
            "characters",
            "setting",
            "world_rules",
            "hook_visual",
            "hook_audio",
            "inciting_incident",
            "conflict",
            "escalation",
            "turn",
            "product_intervention",
            "ending",
            "dialogue",
            "narrative_functions",
            "prohibited_content",
        ],
        "additionalProperties": False,
        "properties": {
            "premise": text,
            "characters": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "motivation"],
                    "additionalProperties": False,
                    "properties": {
                        "name": text,
                        "motivation": text,
                    },
                },
            },
            "setting": text,
            "world_rules": {
                "type": "array",
                "minItems": 1,
                "items": text,
            },
            "hook_visual": text,
            "hook_audio": text,
            "inciting_incident": text,
            "conflict": text,
            "escalation": {
                "type": "array",
                "minItems": 1,
                "items": text,
            },
            "turn": text,
            "product_intervention": text,
            "ending": text,
            "dialogue": {"type": "array", "items": {"type": "string"}},
            "narrative_functions": {
                "type": "array",
                "minItems": 4,
                "items": text,
            },
            "prohibited_content": text_list,
        },
    }


def _storyboard_output_schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    text_list = {"type": "array", "items": text}
    shot_required = [
        "composition",
        "action",
        "characters",
        "scene",
        "caption",
        "narrative_function",
    ]
    return {
        "type": "object",
        "required": [
            "specification",
            "shots",
            "asset_roles",
            "packaging_strategy",
            "continuity_rules",
            "provider_mapping",
            "retry_policy",
            "delivery_requirements",
        ],
        "additionalProperties": False,
        "properties": {
            "specification": {"type": "object"},
            "shots": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": shot_required,
                    "additionalProperties": False,
                    "properties": {
                        "composition": text,
                        "action": text,
                        "characters": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "scene": text,
                        "caption": {"type": "string"},
                        "narrative_function": text,
                    },
                },
            },
            "asset_roles": {
                "type": "object",
                "additionalProperties": text,
            },
            "packaging_strategy": text,
            "continuity_rules": {
                "type": "array",
                "minItems": 1,
                "items": text,
            },
            "provider_mapping": {
                "type": "object",
                "additionalProperties": text,
            },
            "retry_policy": {"type": "object"},
            "delivery_requirements": {
                "type": "array",
                "minItems": 1,
                "items": text,
            },
        },
    }


def _compliance_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["checks", "warnings", "blockers"],
        "additionalProperties": False,
        "properties": {
            "checks": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "status", "detail"],
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "status": {
                            "type": "string",
                            "enum": ["PASS", "WARN", "FAIL"],
                        },
                        "detail": {"type": "string", "minLength": 1},
                    },
                },
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
            "blockers": {"type": "array", "items": {"type": "string"}},
        },
    }


def ensure_creative_decision(
    task: CreativeTaskRecord,
    candidates: list[CreativeCandidateArtifact],
) -> CreativeDecisionArtifact:
    grounding = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["product_grounding_pack"],
    )
    research = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["research_insight_pack"],
    )
    revision = task.revision_messages[-1] if task.revision_messages else ""
    requested_direction = _requested_candidate_direction(revision)
    if not requested_direction and any(
        marker in revision for marker in ("包内", "物件", "最后一个位置", "轻喜剧")
    ):
        requested_direction = "variation"
    review_actions = [
        "artifact_read",
        "history_search",
        "material_read",
        "provider_capability_read",
        "policy_read",
    ]
    candidate_ids = [item.artifact_id for item in candidates]
    run_result = _execute_recorded_skill(
        task,
        skill_name="creative-review",
        input_payload={
            "grounding": grounding.model_dump(mode="json"),
            "research": research.model_dump(mode="json"),
            "candidates": [item.model_dump(mode="json") for item in candidates],
            "requested_direction": requested_direction,
            "user_revision": revision,
            "preserve_exact_packaging": task.request.preserve_exact_packaging,
        },
        expected_output_schema=_creative_decision_output_schema(candidate_ids),
        input_artifacts=[grounding, research, *candidates],
        actual_actions=review_actions,
    )
    payload = dict(run_result.payload)
    if requested_direction:
        requested_id = next(
            item.artifact_id
            for item in candidates
            if item.direction == requested_direction
        )
        payload["selected_candidate_id"] = requested_id
        payload["selection_reason"] = (
            f"用户本次修订明确选择“{revision}”；独立评审保留风险评分，"
            "最终方向遵循用户选择。"
        )
        payload["rejected_candidates"] = [
            {
                "candidate_id": item.artifact_id,
                "reason": "用户明确选择了另一方向；保留本方向及评分供后续修订参考。",
            }
            for item in candidates
            if item.artifact_id != requested_id
        ]
    decision = CreativeDecisionArtifact.model_validate(
        {
            "artifact_id": (
                f"decision-{task.task_id}{professional_revision_suffix(task)}"
            ),
            "task_id": task.task_id,
            "product_id": task.product_id,
            "created_at": now_iso(),
            "source_refs": [
                grounding.artifact_id,
                research.artifact_id,
                *candidate_ids,
            ],
            "status": "READY",
            "candidate_ids": candidate_ids,
            "scores": payload.get("scores"),
            "selected_candidate_id": payload.get("selected_candidate_id"),
            "selection_reason": payload.get("selection_reason"),
            "rejected_candidates": payload.get("rejected_candidates"),
            "preview_required": task.request.autonomy_mode == "preview_first",
            "allowed_deviation": payload.get("allowed_deviation") or [],
        }
    )
    save_professional_artifact(decision)
    record_business_skill_execution(
        task,
        skill_name="creative-review",
        run_result=run_result,
        input_artifacts=[grounding, research, *candidates],
        output_artifacts=[decision],
        actual_actions=review_actions,
    )
    task.professional_artifacts["creative_decision"] = decision.artifact_id
    selected = next(
        item
        for item in candidates
        if item.artifact_id == decision.selected_candidate_id
    )
    task.selected_idea = {
        "candidate_id": selected.artifact_id,
        "direction": selected.direction,
        "one_liner": selected.one_liner,
        "hook": selected.hook,
        "production_route": selected.production_route,
        "decision_id": decision.artifact_id,
    }
    return decision


def ensure_story_package(
    task: CreativeTaskRecord,
    candidate: CreativeCandidateArtifact,
    decision: CreativeDecisionArtifact,
) -> StoryPackageArtifact:
    grounding = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["product_grounding_pack"],
    )
    script_actions = ["artifact_read", "material_read", "policy_read"]
    run_result = _execute_recorded_skill(
        task,
        skill_name="script-writer",
        input_payload={
            "grounding": grounding.model_dump(mode="json"),
            "candidate": candidate.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json"),
            "user_revision": (
                task.revision_messages[-1] if task.revision_messages else ""
            ),
        },
        expected_output_schema=_story_package_output_schema(),
        input_artifacts=[grounding, candidate, decision],
        actual_actions=script_actions,
    )
    payload = run_result.payload
    story = StoryPackageArtifact.model_validate(
        {
            "artifact_id": (
                f"story-{task.task_id}{professional_revision_suffix(task)}"
            ),
            "task_id": task.task_id,
            "product_id": task.product_id,
            "created_at": now_iso(),
            "source_refs": [
                grounding.artifact_id,
                candidate.artifact_id,
                decision.artifact_id,
                *candidate.source_refs,
            ],
            "status": "READY",
            **{
                key: payload.get(key)
                for key in (
                    "premise",
                    "characters",
                    "setting",
                    "world_rules",
                    "hook_visual",
                    "hook_audio",
                    "inciting_incident",
                    "conflict",
                    "escalation",
                    "turn",
                    "product_intervention",
                    "ending",
                    "dialogue",
                    "narrative_functions",
                    "prohibited_content",
                )
            },
        }
    )
    save_professional_artifact(story)
    record_business_skill_execution(
        task,
        skill_name="script-writer",
        run_result=run_result,
        input_artifacts=[grounding, candidate, decision],
        output_artifacts=[story],
        actual_actions=script_actions,
    )
    task.professional_artifacts["story_package"] = story.artifact_id
    return story


def _shot_durations(total_seconds: int, count: int) -> list[float]:
    unit = round(total_seconds / count, 2)
    values = [unit] * count
    values[-1] = round(total_seconds - sum(values[:-1]), 2)
    return values


def _shot_durations_for_product_reveal(
    total_seconds: int,
    requested_reveal_seconds: float | None,
) -> tuple[list[float], bool]:
    if (
        requested_reveal_seconds is None
        or requested_reveal_seconds <= 0
        or requested_reveal_seconds >= total_seconds
    ):
        durations = _shot_durations(total_seconds, 5)
        return durations, False
    product_shot_index = 2 if requested_reveal_seconds <= total_seconds / 2 else 3
    before = _shot_durations(requested_reveal_seconds, product_shot_index)
    after = _shot_durations(
        total_seconds - requested_reveal_seconds,
        5 - product_shot_index,
    )
    return before + after, product_shot_index == 2


def _requested_product_reveal_seconds(task: CreativeTaskRecord) -> float | None:
    messages = [task.request.raw_message, *task.revision_messages]
    pattern = re.compile(
        r"(?:产品|主图|包装)?[^，。；\n]{0,12}?"
        r"(?:第\s*)?(\d+(?:\.\d+)?)\s*秒"
        r"(?:左右|前后|附近)?(?:出现|露出|展示|入镜|亮相)"
    )
    for message in reversed(messages):
        match = pattern.search(message)
        if match:
            return float(match.group(1))
    return None


def ensure_production_bible(
    task: CreativeTaskRecord,
    story: StoryPackageArtifact,
    candidate: CreativeCandidateArtifact,
) -> ProductionBibleArtifact:
    grounding = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["product_grounding_pack"],
    )
    selected_materials = list(getattr(grounding, "selected_materials"))
    material_id = str((selected_materials or [{}])[0].get("material_id") or "")
    total_seconds = 10
    brief = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["creative_task_brief"],
    )
    if getattr(brief, "duration_seconds"):
        total_seconds = int(brief.duration_seconds)
    requested_reveal_seconds = _requested_product_reveal_seconds(task)
    durations, early_product_reveal = _shot_durations_for_product_reveal(
        total_seconds,
        requested_reveal_seconds,
    )
    storyboard_actions = [
        "artifact_read",
        "material_read",
        "provider_capability_read",
        "policy_read",
    ]
    run_result = _execute_recorded_skill(
        task,
        skill_name="storyboard-director",
        input_payload={
            "task": brief.model_dump(mode="json"),
            "grounding": grounding.model_dump(mode="json"),
            "story": story.model_dump(mode="json"),
            "required_shot_count": 5,
            "requested_product_reveal_seconds": requested_reveal_seconds,
            "deterministic_constraints": {
                "duration_seconds": total_seconds,
                "aspect_ratio": getattr(brief, "aspect_ratio") or "9:16",
                "product_material_id": material_id,
                "preserve_exact_packaging": task.request.preserve_exact_packaging,
                "subtitles": "post_composite_only",
            },
        },
        expected_output_schema=_storyboard_output_schema(),
        input_artifacts=[brief, grounding, story],
        actual_actions=storyboard_actions,
    )
    payload = run_result.payload
    raw_shots = payload.get("shots")
    if not isinstance(raw_shots, list) or len(raw_shots) != 5:
        raise ValueError(
            "storyboard-director must return exactly five shots for the M12 short-video route"
        )
    product_shot_index = (
        2
        if early_product_reveal
        else 3
    )
    shots = []
    for index, raw_shot in enumerate(raw_shots):
        if not isinstance(raw_shot, dict):
            raise ValueError("storyboard-director shot must be an object")
        input_materials = []
        if material_id and index in {product_shot_index, len(raw_shots) - 1}:
            input_materials.append(material_id)
        shots.append(
            {
                "shot_id": f"shot-{index + 1:02d}",
                "duration_seconds": durations[index],
                "composition": raw_shot.get("composition"),
                "action": raw_shot.get("action"),
                "characters": raw_shot.get("characters") or [],
                "scene": raw_shot.get("scene"),
                "input_materials": input_materials,
                "caption": raw_shot.get("caption") or "",
                "narrative_function": raw_shot.get("narrative_function"),
            }
        )
    packaging_strategy = (
        "exact-main-composite"
        if task.request.preserve_exact_packaging
        else "reference-guided-generation"
    )
    specification = dict(payload.get("specification") or {})
    specification.update(
        {
            "aspect_ratio": getattr(brief, "aspect_ratio") or "9:16",
            "duration_seconds": total_seconds,
            "language": "zh-CN",
            "requested_product_reveal_seconds": requested_reveal_seconds,
            "product_reveal_seconds": sum(
                shot["duration_seconds"]
                for shot in shots[:product_shot_index]
            ),
            "subtitle_rendering": "deterministic_post_composite",
        }
    )
    asset_roles = dict(payload.get("asset_roles") or {})
    if material_id:
        asset_roles[material_id] = (
            "immutable_product_plate"
            if task.request.preserve_exact_packaging
            else "product_reference"
        )
    asset_roles.update(
        {
            "generated-background": "background_only",
            "generated-character": "character_only",
            "deterministic-subtitles": "post_composite_text",
        }
    )
    provider_mapping = dict(payload.get("provider_mapping") or {})
    provider_mapping.update(
        {
            "product_plate": "local_material",
            "subtitles": "deterministic_compositor",
            "final": "compositor",
        }
    )
    continuity_rules = list(payload.get("continuity_rules") or [])
    continuity_rules.extend(
        rule
        for rule in (
            "产品 plate 的包装、文字、比例和颜色不得改变",
            "字幕不由图片或视频生成模型直接绘制",
        )
        if rule not in continuity_rules
    )
    bible = ProductionBibleArtifact.model_validate(
        {
            "artifact_id": (
                f"bible-{task.task_id}{professional_revision_suffix(task)}"
            ),
            "task_id": task.task_id,
            "product_id": task.product_id,
            "created_at": now_iso(),
            "source_refs": [
                brief.artifact_id,
                grounding.artifact_id,
                story.artifact_id,
                candidate.artifact_id,
                f"material:{material_id}",
            ],
            "status": "READY",
            "specification": specification,
            "shots": shots,
            "asset_roles": asset_roles,
            "packaging_strategy": packaging_strategy,
            "continuity_rules": continuity_rules,
            "provider_mapping": provider_mapping,
            "retry_policy": payload.get("retry_policy"),
            "delivery_requirements": payload.get("delivery_requirements"),
        }
    )
    save_professional_artifact(bible)
    record_business_skill_execution(
        task,
        skill_name="storyboard-director",
        run_result=run_result,
        input_artifacts=[brief, grounding, story],
        output_artifacts=[bible],
        actual_actions=storyboard_actions,
    )
    task.professional_artifacts["production_bible"] = bible.artifact_id
    return bible


def ensure_preflight_qa(
    task: CreativeTaskRecord,
    candidates: list[CreativeCandidateArtifact],
    decision: CreativeDecisionArtifact,
    story: StoryPackageArtifact,
    bible: ProductionBibleArtifact,
) -> QaReportArtifact:
    grounding = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["product_grounding_pack"],
    )
    research = load_professional_artifact(
        task.product_id,
        task.professional_artifacts["research_insight_pack"],
    )
    checks = []

    def add(name: str, passed: bool, success: str, failure: str) -> None:
        checks.append(
            {
                "name": name,
                "status": "PASS" if passed else "FAIL",
                "detail": success if passed else failure,
            }
        )

    add(
        "grounding_complete",
        getattr(grounding, "readiness_status") == "READY",
        "产品、SKU、包装与表述边界满足当前任务。",
        "Product Grounding 尚未满足当前任务。",
    )
    add(
        "three_distinct_candidates",
        len(candidates) == 3
        and len({item.direction for item in candidates}) == 3
        and len({item.one_liner for item in candidates}) == 3,
        "稳定、变化、探索三个方向实质不同。",
        "创意候选数量或差异不足。",
    )
    add(
        "decision_explained",
        bool(decision.selected_candidate_id and decision.selection_reason),
        "选中方向和淘汰理由完整。",
        "缺少可解释 Creative Decision。",
    )
    story_text = story.model_dump_json()
    add(
        "story_specific",
        all(
            str(value).strip()
            for value in (
                story.hook_visual,
                story.conflict,
                story.turn,
                story.ending,
            )
        )
        and "从一个细节开始" not in story_text
        and "产品细节" not in story_text,
        "剧情包含具体钩子、冲突、转折和结尾。",
        "剧情仍是通用模板或缺少关键叙事功能。",
    )
    research_refs = set(research.source_refs)
    candidate_refs = set(
        ref for candidate in candidates for ref in candidate.source_refs
    )
    add(
        "research_traceability",
        bool(research.insights or research.degradation_notes)
        and research_refs.issubset(candidate_refs),
        "研究来源已进入候选，或已明确记录离线降级。",
        "研究来源没有进入创意候选。",
    )
    material_ids = {
        str(item.get("material_id") or "")
        for item in getattr(grounding, "selected_materials")
        if item.get("material_id")
    }
    packaging_preservation_required = (
        task.request.preserve_exact_packaging
        or requires_exact_packaging(task.request.raw_message)
    )
    packaging_safe = (
        not packaging_preservation_required
        or (
            bible.packaging_strategy == "exact-main-composite"
            and all(
                bible.asset_roles.get(material_id) == "immutable_product_plate"
                for material_id in material_ids
            )
        )
    )
    add(
        "packaging_route_safe",
        packaging_safe,
        "包装保真要求与 Production Bible 路线一致。",
        "包装保真要求与生产路线冲突。",
    )
    forbidden_claims = list(getattr(grounding, "forbidden_claims"))
    candidate_copy = " ".join(
        " ".join(
            [
                candidate.one_liner,
                candidate.stop_reason,
                candidate.product_role,
                candidate.hook,
                candidate.conflict,
                *candidate.progression,
                candidate.ending,
            ]
        )
        for candidate in candidates
    )
    story_copy = " ".join(
        [
            story.premise,
            story.hook_visual,
            story.hook_audio,
            story.inciting_incident,
            story.conflict,
            *story.escalation,
            story.turn,
            story.product_intervention,
            story.ending,
            *story.dialogue,
        ]
    )
    production_copy = " ".join(
        " ".join([shot.action, shot.caption])
        for shot in bible.shots
    )
    combined = " ".join([candidate_copy, story_copy, production_copy])
    found_forbidden = [claim for claim in forbidden_claims if claim and claim in combined]
    add(
        "claim_boundary_safe",
        not found_forbidden,
        "创意与生产文案未命中禁用表述。",
        f"命中禁用表述：{', '.join(found_forbidden)}",
    )
    add(
        "production_executable",
        len(bible.shots) >= 4
        and all(shot.narrative_function for shot in bible.shots)
        and bool(bible.provider_mapping),
        "逐镜头规格、素材角色和 Provider 映射完整。",
        "Production Bible 缺少可执行字段。",
    )
    repetitive = [
        candidate.artifact_id
        for candidate in candidates
        if candidate.historical_similarity >= 0.75
        and not candidate.novelty_strategy.strip()
    ]
    add(
        "historical_novelty",
        not repetitive,
        "高相似候选已说明结构性差异策略，或没有命中高相似历史方向。",
        "高相似候选缺少结构性差异策略：" + ", ".join(repetitive),
    )
    compliance_actions = ["artifact_read", "policy_read", "material_read"]
    compliance_run = _execute_recorded_skill(
        task,
        skill_name="compliance-guard",
        input_payload={
            "grounding": grounding.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json"),
            "story": story.model_dump(mode="json"),
            "production_bible": bible.model_dump(mode="json"),
            "deterministic_checks": checks,
            "hard_rule_note": (
                "Any deterministic FAIL remains a FAIL even if semantic review passes."
            ),
        },
        expected_output_schema=_compliance_output_schema(),
        input_artifacts=[grounding, decision, story, bible],
        actual_actions=compliance_actions,
    )
    semantic_checks = compliance_run.payload.get("checks")
    if not isinstance(semantic_checks, list):
        raise ValueError("compliance-guard checks must be an array")
    for item in semantic_checks:
        if not isinstance(item, dict):
            raise ValueError("compliance-guard check must be an object")
        status = str(item.get("status") or "")
        if status not in {"PASS", "WARN", "FAIL"}:
            raise ValueError("compliance-guard returned an invalid check status")
        checks.append(
            {
                "name": str(item.get("name") or "semantic_compliance_review"),
                "status": status,
                "detail": str(item.get("detail") or "").strip(),
            }
        )
    blockers = [
        item["detail"]
        for item in checks
        if item["status"] == "FAIL"
    ]
    blockers.extend(
        str(item)
        for item in compliance_run.payload.get("blockers") or []
        if str(item).strip() and str(item) not in blockers
    )
    failed_names = {
        item["name"]
        for item in checks
        if item["status"] == "FAIL"
    }
    revisable_checks = {
        "three_distinct_candidates",
        "decision_explained",
        "story_specific",
        "research_traceability",
        "claim_boundary_safe",
        "historical_novelty",
        "semantic_compliance_review",
    }
    gate_result = (
        "PASS"
        if not failed_names
        else "NEEDS_REVISION"
        if failed_names.issubset(revisable_checks)
        else "BLOCKED"
    )
    qa = QaReportArtifact(
        artifact_id=f"qa-{task.task_id}{professional_revision_suffix(task)}",
        task_id=task.task_id,
        product_id=task.product_id,
        created_at=now_iso(),
        source_refs=[
            grounding.artifact_id,
            research.artifact_id,
            decision.artifact_id,
            story.artifact_id,
            bible.artifact_id,
        ],
        status=gate_result,
        checks=checks,
        gate_result=gate_result,
        blockers=blockers,
        warnings=[
            *list(research.degradation_notes),
            *[
                str(item)
                for item in compliance_run.payload.get("warnings") or []
                if str(item).strip()
            ],
        ],
        evaluated_artifact_ids=[
            grounding.artifact_id,
            research.artifact_id,
            *[item.artifact_id for item in candidates],
            decision.artifact_id,
            story.artifact_id,
            bible.artifact_id,
        ],
    )
    save_professional_artifact(qa)
    record_business_skill_execution(
        task,
        skill_name="compliance-guard",
        run_result=compliance_run,
        input_artifacts=[grounding, decision, story, bible],
        output_artifacts=[qa],
        actual_actions=compliance_actions,
    )
    task.professional_artifacts["qa_report"] = qa.artifact_id
    task.professional_artifact_status = "complete" if qa.gate_result == "PASS" else "in_progress"
    return qa


def build_professional_creative_pack(task: CreativeTaskRecord) -> Dict[str, Any]:
    existing_qa_id = str(task.professional_artifacts.get("qa_report") or "")
    if existing_qa_id:
        qa = load_professional_artifact(task.product_id, existing_qa_id)
        return {
            "provider_ready": qa.gate_result == "PASS",
            "blocked_at": "" if qa.gate_result == "PASS" else "preflight_qa",
            "candidate_ids": list(
                task.professional_artifacts.get("creative_candidates") or []
            ),
            "decision_id": str(
                task.professional_artifacts.get("creative_decision") or ""
            ),
            "story_id": str(
                task.professional_artifacts.get("story_package") or ""
            ),
            "production_bible_id": str(
                task.professional_artifacts.get("production_bible") or ""
            ),
            "qa_report_id": qa.artifact_id,
            "gate_result": qa.gate_result,
            "blockers": list(qa.blockers),
        }
    existing_decision_id = str(
        task.professional_artifacts.get("creative_decision") or ""
    )
    if (
        existing_decision_id
        and task.request.autonomy_mode == "preview_first"
        and not task.professional_artifacts.get("story_package")
    ):
        return {
            "provider_ready": False,
            "blocked_at": "creative_preview",
            "candidate_ids": list(
                task.professional_artifacts.get("creative_candidates") or []
            ),
            "decision_id": existing_decision_id,
        }
    grounding = ensure_product_grounding_pack(task)
    persist_professional_task_checkpoint(task)
    if grounding.readiness_status != "READY":
        return {
            "provider_ready": False,
            "blocked_at": "product_grounding_pack",
            "blockers": list(grounding.blockers),
        }
    research = ensure_research_insight_pack(task)
    persist_professional_task_checkpoint(task)
    candidates = ensure_creative_candidates(task, research)
    persist_professional_task_checkpoint(task)
    decision = ensure_creative_decision(task, candidates)
    persist_professional_task_checkpoint(task)
    if decision.preview_required:
        task.status = "NEEDS_INPUT"
        task.blocked_reason = "Three professional creative candidates are ready for user review."
        return {
            "provider_ready": False,
            "blocked_at": "creative_preview",
            "candidate_ids": [item.artifact_id for item in candidates],
            "decision_id": decision.artifact_id,
        }
    selected = next(
        item for item in candidates if item.artifact_id == decision.selected_candidate_id
    )
    story = ensure_story_package(task, selected, decision)
    persist_professional_task_checkpoint(task)
    bible = ensure_production_bible(task, story, selected)
    persist_professional_task_checkpoint(task)
    qa = ensure_preflight_qa(task, candidates, decision, story, bible)
    persist_professional_task_checkpoint(task)
    return {
        "provider_ready": qa.gate_result == "PASS",
        "blocked_at": "" if qa.gate_result == "PASS" else "preflight_qa",
        "candidate_ids": [item.artifact_id for item in candidates],
        "decision_id": decision.artifact_id,
        "story_id": story.artifact_id,
        "production_bible_id": bible.artifact_id,
        "qa_report_id": qa.artifact_id,
        "gate_result": qa.gate_result,
        "blockers": list(qa.blockers),
    }
