"""Typed contracts for the durable Product Creative application boundary."""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import Field

from .models import ContractModel, EvidenceRef


class CommandEnvelope(ContractModel):
    command: str
    product_id: str = ""
    workflow_id: str = ""
    step_id: str = ""
    trace_id: str = ""
    idempotency_key: str = ""
    confirmed: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)


class CommandResult(ContractModel):
    command: str
    product_id: str = ""
    status: Literal["succeeded", "paused", "failed", "pending"]
    success: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    artifact_ids: List[str] = Field(default_factory=list)
    evidence: List[EvidenceRef] = Field(default_factory=list)
    retryable: bool = False
    error_code: str = ""
    error_message: str = ""


class GoalPlanStep(ContractModel):
    command: str
    goal: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    success_criteria: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False


class GoalPlan(ContractModel):
    product_id: str
    goal: str
    modality: Literal["text", "image", "video", "review", "feedback", "learning", "brain", "material", "inspiration", "unknown"] = "unknown"
    target: str = ""
    constraints: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    steps: List[GoalPlanStep]
    missing_inputs: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    planner: Literal["llm", "deterministic"] = "deterministic"
    replan_count: int = Field(default=0, ge=0, le=2)


class Observation(ContractModel):
    product_id: str
    brain_version_id: str = ""
    brain_version: int = 0
    workflow_status: str = ""
    current_action: str = ""
    artifact_ids: List[str] = Field(default_factory=list)
    material_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    provider_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    compact_context: Dict[str, Any] = Field(default_factory=dict)


class DomainEvent(ContractModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    product_id: str
    trace_id: str
    sequence: int = Field(ge=1)
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class WritebackDecision(ContractModel):
    proposal_id: str
    product_id: str
    decision: Literal["confirm", "reject", "rollback"]
    target_brain_version: int | None = None
    confirmed: bool = False
    reason: str = ""


class PolicyDecision(ContractModel):
    allowed: bool
    status: Literal["allowed", "confirmation_required", "blocked", "human_review"]
    reason: str = ""
    risk_level: Literal["low", "medium", "high"] = "low"
    confirmation_subject: str = ""
