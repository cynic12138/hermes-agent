"""Evidence-backed rule candidates and writeback lifecycle."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ..contracts.models import EvidenceRef, RuleCandidate
from ..ports.runtime_repositories import rules


RULE_CANDIDATE_SCHEMA_VERSION = "product_creative.rule_candidate.v1"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _scope(path: str) -> str:
    if path == "learning.channel_preferences":
        return "channel_playbook"
    if path == "learning.material_preferences":
        return "material_preference"
    if path in {"learning.image_generation_preferences", "learning.video_script_preferences"}:
        return "generation_policy"
    return "product_state"


def _risk(value: str) -> str:
    return {"low": "level_1", "medium": "level_2", "high": "level_3"}.get(value, "level_2")


def _direction(path: str) -> str:
    if path == "learning.successful_patterns":
        return "successful"
    if path == "learning.failed_patterns":
        return "failed"
    return "neutral"


def _evidence_refs(payload: Dict[str, Any], subject_id: str) -> List[EvidenceRef]:
    call_mode = _text((payload.get("llm") or {}).get("call_mode"))
    refs = [
        EvidenceRef(
            evidence_id=_text(payload.get("result_evaluation_id") or payload.get("evaluation_id") or subject_id),
            kind="result_evaluation" if payload.get("result_evaluation_id") or payload.get("evaluation_id") else "learning_proposal",
            path=_text(payload.get("evaluation_path") or payload.get("proposal_path")),
            confidence=0.75 if call_mode and call_mode != "rule_fallback" else 0.6,
        )
    ]
    if payload.get("source_result_id"):
        refs.append(
            EvidenceRef(
                evidence_id=_text(payload.get("source_result_id")),
                kind="generation_result",
                path=_text(payload.get("source_result_path")),
            )
        )
    if payload.get("source_feedback_id"):
        refs.append(
            EvidenceRef(
                evidence_id=_text(payload.get("source_feedback_id")),
                kind="user_feedback",
                path=_text(payload.get("source_feedback_path")),
            )
        )
    return refs


def rule_candidates_from_updates(
    product_id: str,
    subject_id: str,
    updates: Iterable[Dict[str, Any]],
    payload: Dict[str, Any],
    created_at: str,
) -> List[RuleCandidate]:
    candidates: List[RuleCandidate] = []
    evidence = _evidence_refs(payload, subject_id)
    for update in updates:
        path = _text(update.get("path"))
        value = update.get("value")
        if not path or value is None or value == "":
            continue
        risk_level = _risk(_text(update.get("risk_level")) or "medium")
        confidence = 0.75 if any(ref.confidence and ref.confidence >= 0.7 for ref in evidence) else 0.6
        candidate = RuleCandidate(
            rule_id=f"rule-{uuid.uuid4().hex}",
            product_id=product_id,
            scope=_scope(path),
            target_path=path,
            rule_type=_text(update.get("update_type")) or "learning_preference",
            value=value,
            conditions={
                "target_page": _text(update.get("target_page")),
                "target_section": _text(update.get("target_section")),
                "source_subject_id": subject_id,
            },
            evidence=evidence,
            confidence=confidence,
            direction=_direction(path),
            risk_level=risk_level,
            conflict_key=f"{_scope(path)}:{path}",
            status="candidate" if risk_level == "level_1" else "review_required",
            created_at=created_at,
        )
        candidates.append(candidate)
    return candidates


def persist_rule_candidates(base: Path, candidates: Iterable[RuleCandidate], subject_id: str) -> List[str]:
    return rules().persist(candidates, subject_id)


def create_rule_candidates_for_evaluation(base: Path, evaluation: Dict[str, Any]) -> List[RuleCandidate]:
    evaluation_id = _text(evaluation.get("result_evaluation_id") or evaluation.get("evaluation_id"))
    evaluation_payload = dict(evaluation)
    evaluation_payload["evaluation_path"] = str(
        Path("artifacts") / "result_evaluations" / f"{evaluation_id}.json"
    )
    candidates = rule_candidates_from_updates(
        base.name,
        evaluation_id,
        evaluation.get("proposed_updates") or [],
        evaluation_payload,
        _text(evaluation.get("created_at")),
    )
    persist_rule_candidates(base, candidates, evaluation_id)
    return candidates


def _candidate(rule_id: str, base: Path) -> Dict[str, Any]:
    return rules().get(rule_id)


def _rules_for_subject(base: Path, subject_id: str) -> List[Dict[str, Any]]:
    return rules().list(base.name, subject_id)


def attach_rule_candidates_to_proposal(base: Path, proposal: Dict[str, Any]) -> Dict[str, Any]:
    subject_ids = {
        _text(update.get("source_evaluation_id"))
        for update in proposal.get("updates") or []
        if isinstance(update, dict) and update.get("source_evaluation_id")
    }
    rules: List[Dict[str, Any]] = []
    for subject_id in sorted(subject_ids):
        rules.extend(_rules_for_subject(base, subject_id))
    if not rules:
        candidates = rule_candidates_from_updates(
            base.name,
            _text(proposal.get("proposal_id")),
            proposal.get("updates") or [],
            {
                **proposal,
                "proposal_path": str(Path("structured") / "evolution_proposals" / f"{proposal.get('proposal_id')}.json"),
            },
            _text(proposal.get("created_at")),
        )
        persist_rule_candidates(base, candidates, _text(proposal.get("proposal_id")))
        rules = [{"schema_version": RULE_CANDIDATE_SCHEMA_VERSION, **item.model_dump(mode="json")} for item in candidates]
    proposal["rule_candidate_ids"] = [rule.get("rule_id") for rule in rules if rule.get("rule_id")]
    proposal["rules"] = rules
    proposal["writeback_contract"] = {
        "level_1": "recorded_automatically_but_not_applied_to_canonical_brain",
        "level_2": "requires_human_review",
        "level_3": "requires_explicit_human_confirmation",
        "projection_refresh_after_apply": True,
    }
    return proposal


def mark_rule_candidates_applied(base: Path, rule_ids: Iterable[str], applied_at: str, proposal_id: str) -> None:
    rules().mark_applied(base.name, rule_ids, applied_at, proposal_id)
