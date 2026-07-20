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


def requires_exact_packaging(message: str) -> bool:
    """Return whether natural language requires immutable packaging/main-image pixels."""

    text = message.strip()
    direct_markers = (
        "包装不能变",
        "包装不变",
        "不能改变包装",
        "主图不能变",
        "不重绘",
        "不得重绘",
        "禁止重绘",
        "原始像素",
        "逐帧保持",
        "像素级保持",
        "保持包装与品牌文字原样",
        "包装与品牌文字原样",
        "包装保持原样",
        "保持包装原样",
        "包装必须保持原样",
    )
    if any(marker in text for marker in direct_markers):
        return True
    packaging_subjects = (
        "包装",
        "包装外观",
        "包装文字",
        "产品外观",
        "产品文字",
        "主图",
    )
    preservation_constraints = (
        "不得变化",
        "不能变化",
        "不允许变化",
        "不得改变",
        "不能改变",
        "不允许改变",
        "不要改变",
        "保持不变",
        "原样保留",
        "不得改动",
        "不能改动",
        "不允许改动",
        "不要改动",
        "不得修改",
        "不能修改",
        "不允许修改",
    )
    return any(subject in text for subject in packaging_subjects) and any(
        constraint in text for constraint in preservation_constraints
    )


def requests_text_deliverable(message: str) -> bool:
    """Distinguish requested copy output from constraints about packaging text."""

    text = message.strip()
    if any(marker in text for marker in ("文案", "口播", "脚本")):
        return True
    if "文字" not in text:
        return False
    if any(
        marker in text
        for marker in (
            "不要生成文字",
            "不生成文字",
            "禁止生成文字",
            "无需文字",
            "不需要文字",
            "不要文字",
        )
    ):
        return False
    if any(
        marker in text
        for marker in (
            "生成文字",
            "写文字",
            "输出文字",
            "文字内容",
            "文字稿",
            "一段文字",
            "几段文字",
            "一些文字",
        )
    ):
        return True
    if requires_exact_packaging(text) and any(
        marker in text
        for marker in ("包装文字", "包装外观和文字", "产品文字", "主图文字")
    ):
        return False
    return True


class CreativeTaskRequest(ContractModel):
    """Normalized user goal for a recoverable cross-capability creative task."""

    raw_message: str
    deliverables: List[Literal["text", "image", "video"]] = Field(default_factory=list)
    goal_kind: Literal["creative", "understanding"] = "creative"
    autonomy_mode: Literal["adaptive", "preview_first", "direct"] = "adaptive"
    requires_fresh_inspiration: bool = False
    preserve_exact_packaging: bool = False

    @classmethod
    def from_message(cls, message: str) -> "CreativeTaskRequest":
        text = message.strip()
        deliverables: List[Literal["text", "image", "video"]] = []
        if requests_text_deliverable(text):
            deliverables.append("text")
        image_output_requested = any(marker in text for marker in ("图片", "产品图", "生图")) or any(
            marker in text
            for marker in (
                "做主图",
                "生成主图",
                "设计主图",
                "做首帧",
                "生成首帧",
                "做封面",
                "生成封面",
            )
        )
        if image_output_requested:
            deliverables.append("image")
        if any(marker in text for marker in ("视频", "短片", "成片")):
            deliverables.append("video")
        if (
            not deliverables
            and any(marker in text for marker in ("抖音", "短视频"))
            and any(marker in text for marker in ("剧情", "分镜", "创意方案", "方案"))
        ):
            deliverables.append("video")
        understanding_only = not deliverables and any(
            marker in text
            for marker in ("了解产品", "了解这个产品", "认识产品", "产品大脑", "建脑", "补充产品资料")
        )
        autonomy_mode = "preview_first" if any(
            marker in text for marker in ("先给我看", "先看方案", "先看创意", "先确认方案")
        ) else "adaptive"
        return cls(
            raw_message=text,
            deliverables=deliverables,
            goal_kind="understanding" if understanding_only else "creative",
            autonomy_mode=autonomy_mode,
            requires_fresh_inspiration=any(
                marker in text for marker in ("今天", "今日", "最近", "最新", "热点", "节日")
            ),
            preserve_exact_packaging=requires_exact_packaging(text),
        )


class ProductKnowledgeField(ContractModel):
    key: str
    label: str
    status: Literal["CONFIRMED", "INFERRED", "UNKNOWN", "CONFLICTED"]
    value: Any = None
    source_ids: List[str] = Field(default_factory=list)
    blocking: bool = False
    impact: str = ""


class DiscoveryQuestion(ContractModel):
    question_id: str
    field_key: str
    prompt: str
    priority: int = Field(ge=0)
    blocking: bool = False


class ProductReadinessReport(ContractModel):
    schema_version: Literal["product_creative.product_readiness.v1"] = (
        "product_creative.product_readiness.v1"
    )
    readiness_id: str
    task_id: str
    product_id: str
    created_at: str
    deliverables: List[Literal["text", "image", "video"]] = Field(default_factory=list)
    ready: bool = False
    fields: List[ProductKnowledgeField] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    questions: List[DiscoveryQuestion] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    artifact_path: str = ""


class CreativeTaskPlanStep(ContractModel):
    stage: Literal[
        "RESEARCHING",
        "IDEATING",
        "PREPARING_ASSETS",
        "GENERATING",
        "DELIVERING",
    ]
    action: str
    status: Literal["PENDING", "READY", "BLOCKED", "RUNNING", "COMPLETED", "FAILED"] = "PENDING"
    guard: Literal["", "task_authorization", "provider_readiness", "human_confirmation"] = ""


class CreativeTaskPlan(ContractModel):
    schema_version: Literal["product_creative.creative_task_plan.v1"] = (
        "product_creative.creative_task_plan.v1"
    )
    task_id: str
    stages: List[
        Literal[
            "UNDERSTANDING",
            "RESEARCHING",
            "IDEATING",
            "PREPARING_ASSETS",
            "GENERATING",
            "DELIVERING",
            "AWAITING_FEEDBACK",
        ]
    ] = Field(default_factory=list)
    artifact_gates: List[
        Literal[
            "creative_task_brief",
            "product_grounding_pack",
            "research_insight_pack",
            "creative_candidates",
            "creative_decision",
            "story_package",
            "production_bible",
            "preflight_qa",
        ]
    ] = Field(default_factory=list, max_length=8)
    actions: List[CreativeTaskPlanStep] = Field(default_factory=list, max_length=24)


class CreativeTaskRecord(ContractModel):
    schema_version: Literal["product_creative.creative_task.v1"] = (
        "product_creative.creative_task.v1"
    )
    task_id: str
    product_id: str
    created_at: str
    updated_at: str
    status: Literal[
        "UNDERSTANDING",
        "NEEDS_INPUT",
        "READY",
        "RESEARCHING",
        "IDEATING",
        "PREPARING_ASSETS",
        "GENERATING",
        "DELIVERING",
        "AWAITING_FEEDBACK",
        "COMPLETED",
        "BLOCKED_PRODUCT",
        "BLOCKED_AUTHORIZATION",
        "BLOCKED_PROVIDER",
        "FAILED_RETRYABLE",
        "FAILED_FINAL",
        "CANCELLED",
    ]
    current_stage: str
    request: CreativeTaskRequest
    readiness: ProductReadinessReport
    plan: CreativeTaskPlan
    completed_stages: List[str] = Field(default_factory=list)
    questions: List[DiscoveryQuestion] = Field(default_factory=list)
    blocked_reason: str = ""
    pending_proposal_id: str = ""
    pending_proposal_kind: Literal["", "discovery", "learning"] = ""
    authorization_request_id: str = ""
    authorization_id: str = ""
    provider: str = ""
    task_context: Dict[str, Any] = Field(default_factory=dict)
    selected_materials: List[Dict[str, Any]] = Field(default_factory=list)
    selected_idea: Dict[str, Any] = Field(default_factory=dict)
    professional_artifact_status: Literal[
        "legacy_incomplete",
        "not_started",
        "in_progress",
        "complete",
    ] = "legacy_incomplete"
    professional_artifacts: Dict[str, Any] = Field(default_factory=dict)
    result_descriptors: List[Dict[str, Any]] = Field(default_factory=list)
    revision_messages: List[str] = Field(default_factory=list)
    artifact_path: str = ""


class DiscoverySessionRecord(ContractModel):
    schema_version: Literal["product_creative.discovery_session.v1"] = (
        "product_creative.discovery_session.v1"
    )
    task_id: str
    product_id: str
    created_at: str
    updated_at: str
    turns: List[Dict[str, Any]] = Field(default_factory=list)
    acknowledged_unknown_fields: List[str] = Field(default_factory=list)
    artifact_path: str = ""


class TaskAuthorizationRequest(ContractModel):
    schema_version: Literal["product_creative.task_authorization_request.v1"] = (
        "product_creative.task_authorization_request.v1"
    )
    request_id: str
    task_id: str
    product_id: str
    data_sources: List[Literal["web", "xiaohongshu", "douyin"]] = Field(default_factory=list)
    allow_browser_cookies: bool = False
    allow_paid_image: bool = False
    allow_paid_video: bool = False
    max_image_calls: int = Field(default=0, ge=0, le=20)
    max_video_calls: int = Field(default=0, ge=0, le=20)
    created_at: str
    status: Literal["PENDING", "APPROVED", "REJECTED", "EXPIRED"] = "PENDING"
    artifact_path: str = ""


class TaskAuthorizationRecord(ContractModel):
    schema_version: Literal["product_creative.task_authorization.v1"] = (
        "product_creative.task_authorization.v1"
    )
    authorization_id: str
    request_id: str
    task_id: str
    product_id: str
    data_sources: List[Literal["web", "xiaohongshu", "douyin"]] = Field(default_factory=list)
    allow_browser_cookies: bool = False
    allow_paid_image: bool = False
    allow_paid_video: bool = False
    max_image_calls: int = Field(default=0, ge=0, le=20)
    max_video_calls: int = Field(default=0, ge=0, le=20)
    used_image_calls: int = Field(default=0, ge=0)
    used_video_calls: int = Field(default=0, ge=0)
    product_brain_writeback: Literal[False] = False
    created_at: str
    expires_at: str
    status: Literal["ACTIVE", "EXPIRED", "REVOKED", "CONSUMED"] = "ACTIVE"
    artifact_path: str = ""


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
