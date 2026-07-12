"""Typed contracts shared across Product Creative runtime boundaries."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Base model for strict, serializable runtime contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    WAITING_CONFIRMATION = "waiting_confirmation"
    WAITING_PROVIDER = "waiting_provider"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvidenceRef(ContractModel):
    evidence_id: str
    kind: str
    path: str = ""
    source_id: str = ""
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class IntentDecision(ContractModel):
    product_id: str = ""
    action: str
    goal: str = ""
    modality: Literal["text", "image", "video", "review", "feedback", "learning", "brain", "material", "inspiration", "unknown"] = "unknown"
    channel: str = ""
    target: str = ""
    constraints: List[str] = Field(default_factory=list)
    requested_outputs: List[str] = Field(default_factory=list)
    referenced_ids: List[str] = Field(default_factory=list)
    missing_inputs: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_confirmation: bool = False
    rationale: str = ""
    source: Literal["llm", "rule_fallback", "explicit_action"] = "rule_fallback"


class CreativeTaskBrief(ContractModel):
    """Turn-scoped creative direction; it is never a Product Brain fact."""

    goal: str
    raw_message: str
    channel: str = ""
    target: str = ""
    constraints: List[str] = Field(default_factory=list)
    requested_outputs: List[str] = Field(default_factory=list)
    source: Literal["llm", "rule_fallback", "explicit_action"] = "rule_fallback"


class ActionCommand(ContractModel):
    action: str
    product_id: str
    workflow_id: str = ""
    step_id: str = ""
    trace_id: str = ""
    idempotency_key: str = ""
    confirmed: bool = False
    args: Dict[str, Any] = Field(default_factory=dict)


class ActionResult(ContractModel):
    success: bool
    action: str
    product_id: str
    workflow_id: str = ""
    step_id: str = ""
    trace_id: str = ""
    output: Dict[str, Any] = Field(default_factory=dict)
    artifact_ids: List[str] = Field(default_factory=list)
    evidence: List[EvidenceRef] = Field(default_factory=list)
    error_code: str = ""
    error_message: str = ""
    retryable: bool = False


class WorkflowStep(ContractModel):
    step_id: str
    action: str
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    args: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    attempt: int = Field(default=0, ge=0)
    idempotency_key: str = ""
    pause_reason: str = ""
    error_code: str = ""
    error_message: str = ""
    started_at: str = ""
    completed_at: str = ""


class WorkflowInstance(ContractModel):
    workflow_id: str
    definition: str
    definition_version: str
    product_id: str
    trace_id: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    intent: IntentDecision
    steps: List[WorkflowStep] = Field(default_factory=list)
    current_step: int = Field(default=0, ge=0)
    created_at: str
    updated_at: str
    pause_reason: str = ""
    version: int = Field(default=0, ge=0)


class EvaluationReport(ContractModel):
    evaluation_id: str
    product_id: str
    subject_id: str
    subject_type: str
    score: float | None = None
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    evidence: List[EvidenceRef] = Field(default_factory=list)
    evaluator: str = ""
    created_at: str


class RuleCandidate(ContractModel):
    rule_id: str
    product_id: str
    scope: Literal["product_brain", "product_state", "channel_playbook", "material_preference", "generation_policy"]
    target_path: str
    rule_type: str
    value: Any
    conditions: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[EvidenceRef] = Field(default_factory=list)
    sample_size: int = Field(default=1, ge=1)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    direction: Literal["successful", "failed", "neutral"] = "neutral"
    risk_level: Literal["level_1", "level_2", "level_3"] = "level_2"
    conflict_key: str = ""
    status: Literal["candidate", "review_required", "approved", "rejected", "applied"] = "candidate"
    created_at: str


class WritebackProposal(ContractModel):
    proposal_id: str
    product_id: str
    rules: List[RuleCandidate]
    status: Literal["proposed", "approved", "rejected", "applied"] = "proposed"
    requires_human_review: bool = True
    created_at: str
    applied_at: str = ""
