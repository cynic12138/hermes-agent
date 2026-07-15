"""Product evolution proposal and apply service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ...brain.learning import (
    apply_learning_updates,
    confirmed_learning_lines,
    proposal_from_channel_feedback,
    proposal_from_regular_feedback,
    proposal_from_result_feedback,
    proposal_from_material_feedback,
    proposal_from_video_brief_feedback,
    proposal_from_visual_alignment,
)
from ...brain.provenance import build_product_fingerprint, register_source as _register_source
from ...brain.rules import attach_rule_candidates_to_proposal
from ...brain.wiki import ensure_m1_wiki as _ensure_m1_wiki, render_product_pages
from ...common import append_text, ensure_product, json_text, now_iso, product_state_path, read_json, read_product_state, timestamp, today, update_index_and_log, wiki_path, write_json
from ...context_safety import apply_generation_safe_state
from ...ports.runtime_repositories import product_brains, proposals
from .feedback_repository import (
    _latest_result_evaluation_for_feedback,
    read_channel_feedback_entries,
    read_feedback_entries,
    read_material_feedback_entries,
    read_result_feedback_entries,
    read_video_brief_feedback_entries,
    read_visual_alignment_entries,
)


__all__ = ["apply_proposal", "evolve_product"]


def _proposal_from_feedback(base: Path, source_feedback_id: str = "") -> Dict[str, Any]:
    entries = read_feedback_entries(base)
    result_entries = [
        item for item in read_result_feedback_entries(base)
        if item.get("eligible_for_evolution_proposal")
    ]
    channel_entries = [
        item for item in read_channel_feedback_entries(base)
        if item.get("eligible_for_evolution_proposal")
    ]
    video_brief_entries = [
        item for item in read_video_brief_feedback_entries(base)
        if item.get("eligible_for_evolution_proposal")
    ]
    visual_entries = [
        item for item in read_visual_alignment_entries(base)
        if item.get("eligible_for_evolution_proposal")
    ]
    material_entries = [
        item for item in read_material_feedback_entries(base)
        if item.get("eligible_for_evolution_proposal")
    ]
    if source_feedback_id:
        selected_result = next(
            (
                item for item in result_entries
                if str(item.get("feedback_id") or "") == source_feedback_id
            ),
            {},
        )
        if not selected_result:
            raise FileNotFoundError(
                f"eligible result feedback '{source_feedback_id}' does not exist"
            )
        evaluation = _latest_result_evaluation_for_feedback(base, selected_result)
        source_ref = str(
            selected_result.get("feedback_path")
            or selected_result.get("source_result_path")
            or selected_result.get("result_path")
            or ""
        )
        source_ids = []
        if source_ref:
            source_ids.append(
                _register_source(
                    base,
                    "result_feedback",
                    source_ref,
                    "medium",
                    source_feedback_id,
                )
            )
        return proposal_from_result_feedback(
            base.name,
            selected_result,
            evaluation,
            source_ids,
            f"proposal-{timestamp()}",
            now_iso(),
        )
    latest_regular = entries[-1] if entries else {}
    latest_result = result_entries[-1] if result_entries else {}
    latest_channel = channel_entries[-1] if channel_entries else {}
    latest_video_brief = video_brief_entries[-1] if video_brief_entries else {}
    latest_visual = visual_entries[-1] if visual_entries else {}
    latest_material = material_entries[-1] if material_entries else {}
    other_latest_times = [
        str(item.get("created_at", ""))
        for item in (latest_regular, latest_result, latest_channel, latest_video_brief, latest_visual)
        if item
    ]
    if latest_material and str(latest_material.get("created_at", "")) >= max(other_latest_times or [""]):
        source_ref = str(latest_material.get("path") or "")
        source_ids = []
        if source_ref:
            source_ids.append(
                _register_source(
                    base,
                    "material_feedback",
                    source_ref,
                    "medium",
                    str(latest_material.get("feedback_id") or ""),
                )
            )
        return proposal_from_material_feedback(base.name, latest_material, source_ids, f"proposal-{timestamp()}", now_iso())
    if latest_visual and (
        str(latest_visual.get("created_at", "")) >= str(latest_regular.get("created_at", ""))
        and str(latest_visual.get("created_at", "")) >= str(latest_result.get("created_at", ""))
        and str(latest_visual.get("created_at", "")) >= str(latest_channel.get("created_at", ""))
        and str(latest_visual.get("created_at", "")) >= str(latest_video_brief.get("created_at", ""))
    ):
        source_ref = str(latest_visual.get("source_alignment_path") or "")
        source_ids = []
        if source_ref:
            source_ids.append(_register_source(base, "visual_alignment", source_ref, "medium", str(latest_visual.get("alignment_id") or "")))
        return proposal_from_visual_alignment(base.name, latest_visual, source_ids, f"proposal-{timestamp()}", now_iso())
    if video_brief_entries:
        latest_video_brief = video_brief_entries[-1]
        if (
            str(latest_video_brief.get("created_at", "")) >= str(latest_regular.get("created_at", ""))
            and str(latest_video_brief.get("created_at", "")) >= str(latest_result.get("created_at", ""))
            and str(latest_video_brief.get("created_at", "")) >= str(latest_channel.get("created_at", ""))
        ):
            source_ref = str(latest_video_brief.get("source_feedback_path") or latest_video_brief.get("source_brief_path") or "")
            source_ids = []
            if source_ref:
                source_ids.append(_register_source(base, "video_brief_feedback", source_ref, "medium", str(latest_video_brief.get("feedback_id") or "")))
            return proposal_from_video_brief_feedback(base.name, latest_video_brief, source_ids, f"proposal-{timestamp()}", now_iso())
    if channel_entries:
        latest_channel = channel_entries[-1]
        if (
            str(latest_channel.get("created_at", "")) >= str(latest_regular.get("created_at", ""))
            and str(latest_channel.get("created_at", "")) >= str(latest_result.get("created_at", ""))
            and str(latest_channel.get("created_at", "")) >= str(latest_video_brief.get("created_at", ""))
        ):
            source_ref = str(latest_channel.get("source_feedback_path") or latest_channel.get("source_artifact_path") or "")
            source_ids = []
            if source_ref:
                source_ids.append(_register_source(base, "channel_feedback", source_ref, "medium", str(latest_channel.get("feedback_id") or "")))
            return proposal_from_channel_feedback(base.name, latest_channel, source_ids, f"proposal-{timestamp()}", now_iso())
    if result_entries:
        latest_result = result_entries[-1]
        latest_regular = entries[-1] if entries else {}
        if (
            (not latest_regular or str(latest_result.get("created_at", "")) >= str(latest_regular.get("created_at", "")))
            and str(latest_result.get("created_at", "")) >= str(latest_video_brief.get("created_at", ""))
        ):
            evaluation = _latest_result_evaluation_for_feedback(base, latest_result)
            source_ref = str(latest_result.get("feedback_path") or latest_result.get("source_result_path") or latest_result.get("result_path") or "")
            source_ids = []
            if source_ref:
                source_ids.append(_register_source(base, "result_feedback", source_ref, "medium", str(latest_result.get("feedback_id") or "")))
            if evaluation.get("_path"):
                source_ids.append(
                    _register_source(
                        base,
                        "result_evaluation",
                        str(evaluation.get("_path")),
                        "medium",
                        str(evaluation.get("result_evaluation_id") or evaluation.get("evaluation_id") or ""),
                    )
                )
            return proposal_from_result_feedback(base.name, latest_result, evaluation, source_ids, f"proposal-{timestamp()}", now_iso())

    latest = entries[-1] if entries else {}
    source_ids = [str(latest.get("source_id"))] if latest.get("source_id") else []
    return proposal_from_regular_feedback(base.name, latest, source_ids, f"proposal-{timestamp()}", now_iso())


def evolve_product(
    product_id: str,
    apply_id: Optional[str] = None,
    expected_version: int | None = None,
    source_feedback_id: str = "",
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    if apply_id:
        return apply_proposal(base, apply_id, expected_version=expected_version)

    proposal = _proposal_from_feedback(base, source_feedback_id=source_feedback_id)
    proposal = attach_rule_candidates_to_proposal(base, proposal)
    proposal["storage_uri"] = proposals().save(proposal)
    proposal_path = base / "structured" / "evolution_proposals" / f"{proposal['proposal_id']}.json"
    write_json(proposal_path, proposal)
    append_text(
        wiki_path(base, "product", "product-evolution.md"),
        f"\n## {today()} | {proposal['proposal_id']}\n\n```json\n{json_text(proposal)}\n```\n",
    )
    update_index_and_log(
        base,
        "proposal",
        proposal["proposal_id"],
        [str(proposal_path.relative_to(base)), "Requires human review before apply"],
    )
    return {
        "success": True,
        "product_id": base.name,
        "proposal_id": proposal["proposal_id"],
        "proposal_path": str(proposal_path),
        "proposal": proposal,
    }


def _append_confirmed_learning(base: Path, proposal: Dict[str, Any], applied: List[Dict[str, Any]]) -> None:
    state = read_product_state(base)
    _ensure_m1_wiki(base, base.name, state.get("name") or base.name)
    grouped = confirmed_learning_lines(proposal, applied, today())

    for rel, lines in grouped.items():
        page_path = base / "wiki" / rel
        text = page_path.read_text(encoding="utf-8") if page_path.exists() else ""
        if "## Confirmed Learning" not in text:
            text = text.rstrip() + "\n\n## Confirmed Learning\n\n"
        text = text.replace("- No canonical insight yet.\n", "")
        for line in lines:
            if line not in text:
                text = text.rstrip() + "\n" + line + "\n"
        page_path.write_text(text, encoding="utf-8")


def apply_proposal(base: Path, proposal_id: str, expected_version: int | None = None) -> Dict[str, Any]:
    proposal_path = base / "structured" / "evolution_proposals" / f"{proposal_id}.json"
    proposal_records = proposals()
    proposal = proposal_records.get(proposal_id, base.name)
    if not proposal and proposal_path.exists():
        proposal = read_json(proposal_path, {})
        proposal_records.save(proposal)
    if not proposal:
        raise FileNotFoundError(f"proposal '{proposal_id}' does not exist")
    if proposal.get("status") == "applied":
        current = product_brains().current(base.name)
        return {
            "success": True,
            "product_id": base.name,
            "proposal_id": proposal_id,
            "applied_updates": proposal.get("applied_updates") or proposal.get("updates") or [],
            "preview": proposal.get("preview", []),
            "product_state": str(product_state_path(base)),
            "brain_version": current,
            "idempotent_replay": True,
        }
    brains = product_brains()
    current = brains.current(base.name)
    if not current:
        current = brains.ensure_initial(base.name, read_json(product_state_path(base), {}))
    if expected_version is not None and int(current["version"]) != int(expected_version):
        from ...contracts.errors import OptimisticVersionConflict

        raise OptimisticVersionConflict(
            f"Product Brain '{base.name}' expected version {expected_version}, actual {current['version']}"
        )
    state = dict(current["state"])
    state, applied = apply_learning_updates(state, proposal)
    state["updated_at"] = now_iso()
    state = apply_generation_safe_state(state)
    proposal["status"] = "applied"
    proposal["applied_at"] = now_iso()
    proposal["applied_updates"] = applied
    brain_version = brains.apply_proposal(
        product_id=base.name,
        proposal_id=proposal_id,
        expected_version=int(current["version"]),
        state=state,
        applied_rule_ids=proposal.get("rule_candidate_ids") or [],
        proposal_updates=proposal,
    )
    write_json(product_state_path(base), state)
    build_product_fingerprint(base.name)
    write_json(proposal_path, proposal)
    render_product_pages(base, state)
    _append_confirmed_learning(base, proposal, applied)
    update_index_and_log(base, "apply", proposal_id, [f"Applied {len(applied)} update(s)"])
    return {
        "success": True,
        "product_id": base.name,
        "proposal_id": proposal_id,
        "applied_updates": applied,
        "preview": proposal.get("preview", []),
        "product_state": str(product_state_path(base)),
        "brain_version": brain_version,
    }
