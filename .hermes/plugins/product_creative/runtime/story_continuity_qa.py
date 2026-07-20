"""Story structure and optional visual continuity QA for M14 media."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..common import ensure_product
from ..contracts.creative_artifacts import (
    MediaCompositeManifestArtifact,
    MediaExecutionPlanArtifact,
    MediaQualityCheck,
    MediaShotResultArtifact,
    ProductionBibleArtifact,
)
from .professional_artifacts import load_professional_artifact


VisualAdapter = Callable[..., dict[str, Any]]
_HOOK_MARKERS = ("钩子", "问题", "冲突", "hook", "stop")
_ENDING_MARKERS = ("结尾", "收束", "结束", "ending", "resolve")
_TURN_MARKERS = ("转折", "产品", "介入", "解决", "turn", "product")


def _workspace_path(product_root: Path, relative_path: str) -> Path:
    root = product_root.resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ValueError("story continuity QA path must stay inside the product workspace")
    return path


def _check(
    check_id: str,
    *,
    status: str,
    severity: str,
    expected: dict[str, Any],
    observed: dict[str, Any],
    evidence: list[str],
    shot_id: str = "",
    repairable: bool = False,
) -> MediaQualityCheck:
    return MediaQualityCheck(
        check_id=check_id,
        category="story",
        scope="shot" if shot_id else "final",
        status=status,
        severity=severity,
        shot_id=shot_id,
        expected=expected,
        observed=observed,
        evidence=evidence,
        repairable=repairable and status != "PASS",
    )


def _contains(value: str, markers: tuple[str, ...]) -> bool:
    normalized = value.casefold()
    return any(marker.casefold() in normalized for marker in markers)


def inspect_story_continuity_quality(
    product_id: str,
    *,
    plan_id: str,
    manifest_id: str,
    visual_adapter: VisualAdapter | None,
    minimum_confidence: float = 0.8,
) -> list[MediaQualityCheck]:
    """Validate story coverage and fail closed on unobserved visual continuity."""

    product_root = ensure_product(product_id)
    plan = load_professional_artifact(product_root.name, plan_id)
    manifest = load_professional_artifact(product_root.name, manifest_id)
    if not isinstance(plan, MediaExecutionPlanArtifact):
        raise ValueError("story continuity QA requires a Media Execution Plan")
    if not isinstance(manifest, MediaCompositeManifestArtifact):
        raise ValueError("story continuity QA requires a Composite Manifest")
    if manifest.plan_id != plan.artifact_id:
        raise ValueError("story continuity QA manifest does not belong to the plan")
    bible = load_professional_artifact(
        product_root.name,
        plan.production_bible_id,
    )
    if not isinstance(bible, ProductionBibleArtifact):
        raise ValueError("story continuity QA requires a Production Bible")

    checks: list[MediaQualityCheck] = []
    plan_ids = [shot.shot_id for shot in plan.shots]
    bible_ids = [shot.shot_id for shot in bible.shots]
    manifest_results: dict[str, MediaShotResultArtifact] = {}
    for artifact_id in manifest.shot_result_ids:
        artifact = load_professional_artifact(product_root.name, artifact_id)
        if isinstance(artifact, MediaShotResultArtifact):
            manifest_results[artifact.shot_id] = artifact
    rendered_ids = [
        shot.shot_id
        for shot in plan.shots
        if shot.shot_id in manifest_results
    ]
    coverage_passed = plan_ids == bible_ids == rendered_ids
    checks.append(
        _check(
            "story-shot-coverage",
            status="PASS" if coverage_passed else "FAIL",
            severity="low" if coverage_passed else "critical",
            expected={"shot_ids": bible_ids},
            observed={
                "plan_shot_ids": plan_ids,
                "rendered_shot_ids": rendered_ids,
            },
            evidence=[
                f"bible:{bible.artifact_id}",
                f"plan:{plan.artifact_id}",
                f"manifest:{manifest.artifact_id}",
            ],
            repairable=False,
        )
    )

    narrative = [shot.narrative_function for shot in bible.shots]
    has_hook = bool(narrative) and _contains(narrative[0], _HOOK_MARKERS)
    has_ending = bool(narrative) and _contains(narrative[-1], _ENDING_MARKERS)
    has_turn = any(_contains(item, _TURN_MARKERS) for item in narrative)
    structure_passed = has_hook and has_turn and has_ending
    checks.append(
        _check(
            "story-structure",
            status="PASS" if structure_passed else "FAIL",
            severity="low" if structure_passed else "high",
            expected={
                "hook": True,
                "turn_or_product_intervention": True,
                "ending": True,
            },
            observed={
                "hook": has_hook,
                "turn_or_product_intervention": has_turn,
                "ending": has_ending,
                "narrative_functions": narrative,
            },
            evidence=[f"bible:{bible.artifact_id}"],
            repairable=False,
        )
    )

    observations: dict[str, dict[str, Any]] = {}
    if visual_adapter is not None:
        for shot in bible.shots:
            result = manifest_results.get(shot.shot_id)
            if result is None:
                continue
            observations[shot.shot_id] = visual_adapter(
                product_id=product_root.name,
                shot_id=shot.shot_id,
                media_path=_workspace_path(
                    product_root,
                    result.output_relative_path,
                ),
                expected_characters=list(shot.characters),
                expected_scene=shot.scene,
                expected_product_visible=next(
                    (
                        plan_shot.product_plate_required
                        for plan_shot in plan.shots
                        if plan_shot.shot_id == shot.shot_id
                    ),
                    False,
                ),
                expected_action=shot.action,
            )

    planned_by_id = {shot.shot_id: shot for shot in plan.shots}
    for shot in bible.shots:
        planned = planned_by_id.get(shot.shot_id)
        if planned is None or not planned.motion_required:
            continue
        check_id = f"action-fulfillment:{shot.shot_id}"
        if visual_adapter is None:
            checks.append(
                _check(
                    check_id,
                    status="UNKNOWN",
                    severity="high",
                    shot_id=shot.shot_id,
                    expected={
                        "action": shot.action,
                        "action_completed": True,
                    },
                    observed={"reason": "no visual action adapter configured"},
                    evidence=[f"bible:{bible.artifact_id}"],
                    repairable=False,
                )
            )
            continue
        observation = observations.get(shot.shot_id, {})
        confidence = float(observation.get("confidence") or 0)
        evidence = [
            str(item)
            for item in observation.get("evidence_refs") or []
            if str(item).strip()
        ] or [f"visual:{shot.shot_id}"]
        if confidence < minimum_confidence:
            checks.append(
                _check(
                    check_id,
                    status="UNKNOWN",
                    severity="high",
                    shot_id=shot.shot_id,
                    expected={
                        "action": shot.action,
                        "action_completed": True,
                        "minimum_confidence": minimum_confidence,
                    },
                    observed={"confidence": confidence},
                    evidence=evidence,
                    repairable=False,
                )
            )
            continue
        observed_action = str(
            observation.get("observed_action") or ""
        ).strip()
        completed = (
            observation.get("action_completed") is True
            and bool(observed_action)
        )
        checks.append(
            _check(
                check_id,
                status="PASS" if completed else "FAIL",
                severity="low" if completed else "high",
                shot_id=shot.shot_id,
                expected={
                    "action": shot.action,
                    "action_completed": True,
                },
                observed={
                    "observed_action": observed_action,
                    "action_completed": completed,
                    "confidence": confidence,
                },
                evidence=evidence,
                repairable=not completed,
            )
        )

    for previous, current in zip(bible.shots, bible.shots[1:]):
        check_id = f"visual-continuity:{previous.shot_id}:{current.shot_id}"
        if visual_adapter is None:
            checks.append(
                _check(
                    check_id,
                    status="UNKNOWN",
                    severity="high",
                    expected={
                        "continuity_rules": list(bible.continuity_rules),
                        "previous_characters": list(previous.characters),
                        "current_characters": list(current.characters),
                    },
                    observed={"reason": "no visual continuity adapter configured"},
                    evidence=[f"bible:{bible.artifact_id}"],
                    repairable=False,
                )
            )
            continue
        previous_observation = observations.get(previous.shot_id, {})
        current_observation = observations.get(current.shot_id, {})
        confidence = min(
            float(previous_observation.get("confidence") or 0),
            float(current_observation.get("confidence") or 0),
        )
        evidence = [
            str(item)
            for observation in (previous_observation, current_observation)
            for item in observation.get("evidence_refs") or []
            if str(item).strip()
        ] or [f"visual:{previous.shot_id}:{current.shot_id}"]
        if confidence < minimum_confidence:
            checks.append(
                _check(
                    check_id,
                    status="UNKNOWN",
                    severity="high",
                    expected={
                        "minimum_confidence": minimum_confidence,
                        "continuity_rules": list(bible.continuity_rules),
                    },
                    observed={"confidence": confidence},
                    evidence=evidence,
                    repairable=False,
                )
            )
            continue
        previous_characters = set(
            str(item) for item in previous_observation.get("characters") or []
        )
        current_characters = set(
            str(item) for item in current_observation.get("characters") or []
        )
        expected_shared = set(previous.characters) & set(current.characters)
        character_continuity = expected_shared.issubset(
            previous_characters & current_characters
        )
        expected_same_scene = previous.scene == current.scene
        observed_same_scene = (
            str(previous_observation.get("scene") or "")
            == str(current_observation.get("scene") or "")
        )
        scene_continuity = not expected_same_scene or observed_same_scene
        passed = character_continuity and scene_continuity
        checks.append(
            _check(
                check_id,
                status="PASS" if passed else "FAIL",
                severity="low" if passed else "high",
                shot_id=current.shot_id,
                expected={
                    "shared_characters": sorted(expected_shared),
                    "same_scene": expected_same_scene,
                    "continuity_rules": list(bible.continuity_rules),
                },
                observed={
                    "previous_characters": sorted(previous_characters),
                    "current_characters": sorted(current_characters),
                    "same_scene": observed_same_scene,
                    "confidence": confidence,
                },
                evidence=evidence,
                repairable=not passed,
            )
        )
    return checks
