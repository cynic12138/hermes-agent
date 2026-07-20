"""Versioned professional creative artifacts used by the M11 workflow."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Dict, List, Literal, Type

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ArtifactStatus = Literal[
    "DRAFT",
    "READY",
    "PASS",
    "NEEDS_REVISION",
    "BLOCKED",
    "LEGACY_INCOMPLETE",
]


def professional_artifact_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ProfessionalArtifact(BaseModel):
    """Tamper-evident base contract for one task-scoped creative artifact."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=True)

    schema_name: str
    schema_version: Literal["1.0"] = "1.0"
    artifact_id: NonEmptyStr
    task_id: NonEmptyStr
    product_id: NonEmptyStr
    created_at: NonEmptyStr
    source_refs: List[NonEmptyStr] = Field(default_factory=list)
    status: ArtifactStatus
    content_hash: str = ""

    @model_validator(mode="after")
    def seal_or_verify_content_hash(self) -> "ProfessionalArtifact":
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        expected = professional_artifact_hash(payload)
        if self.content_hash and self.content_hash != expected:
            raise ValueError("content_hash does not match the professional artifact payload")
        if not self.content_hash:
            object.__setattr__(self, "content_hash", expected)
        return self


class CreativeTaskBriefArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.creative_task_brief.v1"] = (
        "product_creative.creative_task_brief.v1"
    )
    original_message: NonEmptyStr
    interpreted_goal: NonEmptyStr
    deliverables: List[Literal["text", "image", "video"]] = Field(min_length=1)
    channel: str = ""
    duration_seconds: int | None = Field(default=None, ge=1, le=600)
    aspect_ratio: str = ""
    constraints: List[NonEmptyStr] = Field(default_factory=list)
    prohibited_requirements: List[NonEmptyStr] = Field(default_factory=list)
    unknown_fields: List[NonEmptyStr] = Field(default_factory=list)
    assumptions: List[NonEmptyStr] = Field(default_factory=list)
    autonomy_mode: Literal["adaptive", "preview_first", "direct"] = "adaptive"
    authorization_scope: Dict[str, Any] = Field(default_factory=dict)


class ProductGroundingPackArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.product_grounding_pack.v1"] = (
        "product_creative.product_grounding_pack.v1"
    )
    brain_version_id: NonEmptyStr
    brain_fingerprint: Annotated[
        str,
        StringConstraints(pattern=r"^[0-9a-f]{64}$"),
    ]
    sku: Dict[str, Any]
    packaging: Dict[str, Any]
    confirmed_claims: List[NonEmptyStr] = Field(default_factory=list)
    forbidden_claims: List[NonEmptyStr] = Field(default_factory=list)
    selected_materials: List[Dict[str, Any]] = Field(default_factory=list)
    field_evidence_refs: Dict[str, List[str]] = Field(default_factory=dict)
    blockers: List[NonEmptyStr] = Field(default_factory=list)
    readiness_status: Literal["READY", "NEEDS_INPUT", "BLOCKED_PRODUCT"]


class ResearchInsightItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    insight_id: NonEmptyStr
    source_type: Literal["web", "xiaohongshu", "douyin", "historical", "workspace"]
    source_ref: NonEmptyStr
    summary: NonEmptyStr
    insight_kind: str = ""
    observation: str = ""
    why_it_matters: str = ""
    adaptation_rule: str = ""
    creative_use: str = ""
    avoid_copying: str = ""
    source_features: Dict[str, Any] = Field(default_factory=dict)
    published_at: str = ""
    confidence: float = Field(ge=0.0, le=1.0)


class ResearchInsightPackArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.research_insight_pack.v1"] = (
        "product_creative.research_insight_pack.v1"
    )
    research_goal: NonEmptyStr
    data_sources: List[
        Literal["web", "xiaohongshu", "douyin", "historical", "workspace"]
    ] = Field(default_factory=list)
    insights: List[ResearchInsightItem] = Field(default_factory=list)
    degradation_notes: List[NonEmptyStr] = Field(default_factory=list)
    not_product_fact: Literal[True] = True

    @model_validator(mode="after")
    def require_insight_or_explicit_degradation(self) -> "ResearchInsightPackArtifact":
        if not self.insights and not self.degradation_notes:
            raise ValueError("research insight pack needs insights or an explicit degradation note")
        return self


class CreativeCandidateArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.creative_candidate.v1"] = (
        "product_creative.creative_candidate.v1"
    )
    direction: Literal["stable", "variation", "exploration"]
    one_liner: NonEmptyStr
    stop_reason: NonEmptyStr
    product_role: NonEmptyStr
    target_emotion: NonEmptyStr
    channel_fit: NonEmptyStr
    hook: NonEmptyStr
    conflict: NonEmptyStr
    progression: List[NonEmptyStr] = Field(min_length=2)
    ending: NonEmptyStr
    required_materials: List[NonEmptyStr] = Field(default_factory=list)
    production_route: NonEmptyStr
    risks: List[NonEmptyStr] = Field(default_factory=list)
    estimated_cost: Literal["low", "medium", "high"]
    feasibility: float = Field(ge=0.0, le=1.0)
    historical_difference: NonEmptyStr
    historical_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    similar_artifact_ids: List[NonEmptyStr] = Field(default_factory=list)
    novelty_strategy: str = ""


class CreativeCandidateScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: NonEmptyStr
    product_fit: float = Field(ge=0.0, le=1.0)
    channel_fit: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    feasibility: float = Field(ge=0.0, le=1.0)
    packaging_safety: float = Field(ge=0.0, le=1.0)
    compliance_safety: float = Field(ge=0.0, le=1.0)
    total: float = Field(ge=0.0, le=1.0)


class RejectedCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: NonEmptyStr
    reason: NonEmptyStr


class CreativeDecisionArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.creative_decision.v1"] = (
        "product_creative.creative_decision.v1"
    )
    candidate_ids: List[NonEmptyStr] = Field(min_length=3, max_length=3)
    scores: List[CreativeCandidateScore] = Field(min_length=3, max_length=3)
    selected_candidate_id: NonEmptyStr
    selection_reason: NonEmptyStr
    rejected_candidates: List[RejectedCandidate] = Field(min_length=2)
    preview_required: bool = False
    allowed_deviation: List[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_candidate_coverage(self) -> "CreativeDecisionArtifact":
        candidate_ids = set(self.candidate_ids)
        if len(candidate_ids) != 3:
            raise ValueError("creative decision requires three distinct candidates")
        if {item.candidate_id for item in self.scores} != candidate_ids:
            raise ValueError("creative decision scores must cover all candidates")
        if self.selected_candidate_id not in candidate_ids:
            raise ValueError("selected candidate is not part of this decision")
        rejected = {item.candidate_id for item in self.rejected_candidates}
        if rejected != candidate_ids - {self.selected_candidate_id}:
            raise ValueError("rejected candidates must cover the two unselected candidates")
        return self


class StoryCharacter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: NonEmptyStr
    motivation: NonEmptyStr


class StoryPackageArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.story_package.v1"] = (
        "product_creative.story_package.v1"
    )
    premise: NonEmptyStr
    characters: List[StoryCharacter] = Field(min_length=1)
    setting: NonEmptyStr
    world_rules: List[NonEmptyStr] = Field(min_length=1)
    hook_visual: NonEmptyStr
    hook_audio: NonEmptyStr
    inciting_incident: NonEmptyStr
    conflict: NonEmptyStr
    escalation: List[NonEmptyStr] = Field(min_length=1)
    turn: NonEmptyStr
    product_intervention: NonEmptyStr
    ending: NonEmptyStr
    dialogue: List[str] = Field(default_factory=list)
    narrative_functions: List[NonEmptyStr] = Field(min_length=4)
    prohibited_content: List[NonEmptyStr] = Field(default_factory=list)


class ProductionShot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    shot_id: NonEmptyStr
    duration_seconds: float = Field(gt=0, le=60)
    composition: NonEmptyStr
    action: NonEmptyStr
    characters: List[str] = Field(default_factory=list)
    scene: NonEmptyStr
    input_materials: List[str] = Field(default_factory=list)
    caption: str = ""
    narrative_function: NonEmptyStr


class ProductionBibleArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.production_bible.v1"] = (
        "product_creative.production_bible.v1"
    )
    specification: Dict[str, Any]
    shots: List[ProductionShot] = Field(min_length=2)
    asset_roles: Dict[str, NonEmptyStr]
    packaging_strategy: NonEmptyStr
    continuity_rules: List[NonEmptyStr] = Field(min_length=1)
    provider_mapping: Dict[str, NonEmptyStr]
    retry_policy: Dict[str, Any]
    delivery_requirements: List[NonEmptyStr] = Field(min_length=1)


class MediaDependencyCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: NonEmptyStr
    status: Literal["READY", "DEGRADED", "BLOCKED"]
    detail: NonEmptyStr
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MediaDependencyReportArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_dependency_report.v1"] = (
        "product_creative.media_dependency_report.v1"
    )
    overall_status: Literal["READY", "DEGRADED", "BLOCKED"]
    checks: List[MediaDependencyCheck] = Field(min_length=1)
    blockers: List[NonEmptyStr] = Field(default_factory=list)
    warnings: List[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def align_dependency_status(self) -> "MediaDependencyReportArtifact":
        blocked_check = any(item.status == "BLOCKED" for item in self.checks)
        if self.overall_status == "READY" and (blocked_check or self.blockers):
            raise ValueError("READY dependency report cannot contain blockers")
        if self.overall_status == "BLOCKED" and not (blocked_check or self.blockers):
            raise ValueError("BLOCKED dependency report must explain at least one blocker")
        if self.overall_status == "DEGRADED":
            if blocked_check or self.blockers:
                raise ValueError("DEGRADED dependency report cannot contain blockers")
            if not (
                self.warnings
                or any(item.status == "DEGRADED" for item in self.checks)
            ):
                raise ValueError("DEGRADED dependency report must explain a warning")
        return self


class ProductPlateArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.product_plate.v1"] = (
        "product_creative.product_plate.v1"
    )
    source_material_id: NonEmptyStr
    source_content_hash: Annotated[
        str,
        StringConstraints(pattern=r"^[0-9a-f]{64}$"),
    ]
    plate_relative_path: NonEmptyStr
    plate_content_hash: Annotated[
        str,
        StringConstraints(pattern=r"^[0-9a-f]{64}$"),
    ]
    mask_mode: Literal[
        "source_alpha",
        "edge_connected_background",
        "full_rect",
    ]
    source_size: tuple[int, int]
    plate_size: tuple[int, int]
    allowed_transforms: List[NonEmptyStr] = Field(min_length=1)
    forbidden_transforms: List[NonEmptyStr] = Field(min_length=1)
    warnings: List[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plate_dimensions(self) -> "ProductPlateArtifact":
        if any(value <= 0 for value in (*self.source_size, *self.plate_size)):
            raise ValueError("product plate dimensions must be positive")
        return self


class MediaShotPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    shot_id: NonEmptyStr
    ordinal: int = Field(ge=1)
    duration_seconds: float = Field(gt=0, le=60)
    execution_mode: Literal[
        "video_background",
        "image_background",
        "local_motion",
    ]
    product_plate_required: bool
    prompt: NonEmptyStr
    motion_required: bool = False
    motion_description: str = ""
    maximum_freeze_ratio: float = Field(default=0.65, ge=0, le=1)
    product_plate_motion: Literal[
        "none",
        "static",
        "subtle_entrance",
    ] = "none"
    caption: str = ""
    input_materials: List[str] = Field(default_factory=list)
    max_attempts: int = Field(default=2, ge=1, le=5)
    idempotency_key: NonEmptyStr


class MediaExecutionPlanArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_execution_plan.v1"] = (
        "product_creative.media_execution_plan.v1"
    )
    production_bible_id: NonEmptyStr
    production_bible_hash: Annotated[
        str,
        StringConstraints(pattern=r"^[0-9a-f]{64}$"),
    ]
    dependency_report_id: NonEmptyStr
    product_plate_id: str = ""
    aspect_ratio: NonEmptyStr
    canvas: tuple[int, int]
    fps: int = Field(ge=1, le=120)
    shots: List[MediaShotPlan] = Field(min_length=2)
    output_requirements: Dict[str, Any] = Field(default_factory=dict)
    call_budget: Dict[Literal["image", "video"], int]

    @model_validator(mode="after")
    def validate_media_plan(self) -> "MediaExecutionPlanArtifact":
        if any(value <= 0 for value in self.canvas):
            raise ValueError("media execution canvas dimensions must be positive")
        shot_ids = [shot.shot_id for shot in self.shots]
        ordinals = [shot.ordinal for shot in self.shots]
        if (
            len(set(shot_ids)) != len(shot_ids)
            or ordinals != list(range(1, len(self.shots) + 1))
        ):
            raise ValueError("media execution shots must be unique and ordered")
        if any(value < 0 or value > 5 for value in self.call_budget.values()):
            raise ValueError("media execution call budget must be between 0 and 5")
        if any(shot.product_plate_required for shot in self.shots) and not self.product_plate_id:
            raise ValueError("product plate is required by at least one media shot")
        return self


class MediaShotResultArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_shot_result.v1"] = (
        "product_creative.media_shot_result.v1"
    )
    plan_id: NonEmptyStr
    shot_id: NonEmptyStr
    attempt: int = Field(ge=1, le=5)
    execution_status: Literal[
        "COMPLETED",
        "FAILED_RETRYABLE",
        "FAILED_FINAL",
    ]
    provider: NonEmptyStr
    external_call_performed: bool
    provider_task_id: str = ""
    input_hashes: Dict[str, Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]]
    source_relative_path: str = ""
    output_relative_path: str = ""
    output_content_hash: str = ""
    duration_seconds: float = Field(default=0, ge=0, le=60)
    error_code: str = ""
    error_detail: str = ""
    command_summary: List[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def align_media_shot_result(self) -> "MediaShotResultArtifact":
        if self.execution_status == "COMPLETED":
            if (
                not self.output_relative_path
                or not self.output_content_hash
                or self.duration_seconds <= 0
            ):
                raise ValueError("completed media shot requires output path, hash, and duration")
            if not re_full_sha256(self.output_content_hash):
                raise ValueError("completed media shot requires a valid output hash")
            if self.error_code or self.error_detail:
                raise ValueError("completed media shot cannot contain failure details")
        else:
            if self.output_relative_path or self.output_content_hash:
                raise ValueError("failed media shot cannot claim output")
            if not self.error_code or not self.error_detail:
                raise ValueError("failed media shot requires error code and detail")
        return self


class MediaCompositeManifestArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_composite_manifest.v1"] = (
        "product_creative.media_composite_manifest.v1"
    )
    plan_id: NonEmptyStr
    shot_result_ids: List[NonEmptyStr] = Field(min_length=2)
    output_relative_path: NonEmptyStr
    output_content_hash: Annotated[
        str,
        StringConstraints(pattern=r"^[0-9a-f]{64}$"),
    ]
    duration_seconds: float = Field(gt=0, le=3600)
    codec: NonEmptyStr
    audio_codec: NonEmptyStr
    subtitle_mode: Literal["deterministic_ass", "none"]
    command_summary: List[NonEmptyStr] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_shot_result_ids(self) -> "MediaCompositeManifestArtifact":
        if len(set(self.shot_result_ids)) != len(self.shot_result_ids):
            raise ValueError("media composite manifest requires unique shot results")
        return self


def re_full_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


class QaCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: NonEmptyStr
    status: Literal["PASS", "WARN", "FAIL"]
    detail: NonEmptyStr


class QaReportArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.qa_report.v1"] = (
        "product_creative.qa_report.v1"
    )
    checks: List[QaCheck] = Field(min_length=1)
    gate_result: Literal["PASS", "NEEDS_REVISION", "BLOCKED"]
    blockers: List[NonEmptyStr] = Field(default_factory=list)
    warnings: List[NonEmptyStr] = Field(default_factory=list)
    evaluated_artifact_ids: List[NonEmptyStr] = Field(min_length=1)

    @model_validator(mode="after")
    def align_gate_and_checks(self) -> "QaReportArtifact":
        failed = any(item.status == "FAIL" for item in self.checks)
        if self.gate_result == "PASS" and (failed or self.blockers):
            raise ValueError("PASS qa report cannot contain failed checks or blockers")
        if self.gate_result != "PASS" and not (failed or self.blockers):
            raise ValueError("non-PASS qa report must explain at least one failure")
        return self


class SkillArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: NonEmptyStr
    content_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def _contains_sensitive_metadata(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            sensitive_key = (
                normalized
                in {
                    "api_key",
                    "apikey",
                    "token",
                    "access_token",
                    "refresh_token",
                    "cookie",
                    "authorization",
                    "secret",
                }
                or normalized.endswith(("_api_key", "_cookie", "_secret"))
                or (
                    normalized.endswith("_token")
                    and not normalized.endswith("_tokens")
                )
            )
            if sensitive_key:
                return True
            if _contains_sensitive_metadata(item):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_metadata(item) for item in value)
    return False


class BusinessSkillExecutionArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.skill_execution.v1"] = (
        "product_creative.skill_execution.v1"
    )
    skill_name: NonEmptyStr
    skill_version: Annotated[
        str,
        StringConstraints(pattern=r"^\d+\.\d+\.\d+$"),
    ]
    stage: NonEmptyStr
    execution_mode: Literal["deterministic", "llm_structured", "fixture", "degraded"]
    input_artifacts: List[SkillArtifactRef] = Field(default_factory=list)
    output_artifacts: List[SkillArtifactRef] = Field(default_factory=list)
    allowed_tools: List[NonEmptyStr] = Field(default_factory=list)
    actual_actions: List[NonEmptyStr] = Field(default_factory=list)
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: NonEmptyStr
    finished_at: str = ""
    execution_status: Literal["COMPLETED", "FAILED", "DEGRADED"]
    failure_code: str = ""
    failure_detail: str = ""

    @model_validator(mode="after")
    def validate_execution_boundary(self) -> "BusinessSkillExecutionArtifact":
        outside = set(self.actual_actions) - set(self.allowed_tools)
        if outside:
            raise ValueError(
                "actual action is outside the Skill allowlist: "
                + ", ".join(sorted(outside))
            )
        if _contains_sensitive_metadata(self.model_metadata):
            raise ValueError("model metadata contains sensitive credential fields")
        if self.execution_status == "FAILED":
            if self.output_artifacts:
                raise ValueError("failed execution cannot claim outputs")
            if not self.failure_code or not self.failure_detail:
                raise ValueError("failed execution requires failure code and detail")
        elif self.failure_code or self.failure_detail:
            raise ValueError("successful execution cannot contain failure details")
        return self


class MediaQualityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    check_id: NonEmptyStr
    category: NonEmptyStr
    scope: Literal[
        "final",
        "shot",
        "frame",
        "audio",
        "subtitle",
        "packaging",
    ]
    status: Literal["PASS", "WARN", "FAIL", "UNKNOWN"]
    severity: Literal["low", "medium", "high", "critical"]
    shot_id: str = ""
    time_range: tuple[float, float] | None = None
    expected: Dict[str, Any] = Field(default_factory=dict)
    observed: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[NonEmptyStr] = Field(default_factory=list)
    repairable: bool = False

    @model_validator(mode="after")
    def validate_media_quality_check(self) -> "MediaQualityCheck":
        if self.time_range is not None:
            start, end = self.time_range
            if start < 0 or end < start:
                raise ValueError("media quality check time_range must be ordered and non-negative")
        if self.status == "PASS" and self.repairable:
            raise ValueError("PASS media quality check cannot be repairable")
        return self


class MediaQaReportArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_qa_report.v1"] = (
        "product_creative.media_qa_report.v1"
    )
    plan_id: NonEmptyStr
    manifest_id: NonEmptyStr
    qa_run: int = Field(ge=1)
    overall_result: Literal["PASS", "REPAIR", "HUMAN_REVIEW", "REJECT"]
    checks: List[MediaQualityCheck] = Field(min_length=1)
    failed_shot_ids: List[NonEmptyStr] = Field(default_factory=list)
    hard_blockers: List[NonEmptyStr] = Field(default_factory=list)
    warnings: List[NonEmptyStr] = Field(default_factory=list)
    evidence_refs: List[NonEmptyStr] = Field(default_factory=list)
    model_provenance: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def align_media_qa_result(self) -> "MediaQaReportArtifact":
        check_ids = [item.check_id for item in self.checks]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("media QA report requires unique check IDs")
        failed = [item for item in self.checks if item.status == "FAIL"]
        unknown = [item for item in self.checks if item.status == "UNKNOWN"]
        failed_shots = {item.shot_id for item in failed if item.shot_id}
        declared_failed_shots = set(self.failed_shot_ids)
        if len(declared_failed_shots) != len(self.failed_shot_ids):
            raise ValueError("media QA report failed_shot_ids must be unique")
        if declared_failed_shots != failed_shots:
            raise ValueError(
                "media QA report failed_shot_ids must match failed checks"
            )
        if _contains_sensitive_metadata(self.model_provenance):
            raise ValueError("media QA model provenance contains sensitive fields")
        if self.overall_result == "PASS":
            if (
                failed
                or unknown
                or self.failed_shot_ids
                or self.hard_blockers
                or self.status != "PASS"
            ):
                raise ValueError(
                    "PASS media QA report cannot contain failed, unknown, or blocked checks"
                )
        elif self.overall_result == "REPAIR":
            repairable_failures = [
                item
                for item in failed
                if item.repairable and item.shot_id
            ]
            if (
                not failed
                or len(repairable_failures) != len(failed)
                or self.status != "NEEDS_REVISION"
            ):
                raise ValueError(
                    "REPAIR media QA report requires only repairable failed shots"
                )
        elif self.overall_result == "HUMAN_REVIEW":
            if not (unknown or failed or self.hard_blockers):
                raise ValueError(
                    "HUMAN_REVIEW media QA report must explain uncertainty or failure"
                )
            if self.status != "BLOCKED":
                raise ValueError(
                    "HUMAN_REVIEW media QA report must use BLOCKED artifact status"
                )
        else:
            critical_failure = any(
                item.status == "FAIL" and item.severity == "critical"
                for item in self.checks
            )
            if not (critical_failure or self.hard_blockers):
                raise ValueError(
                    "REJECT media QA report requires a critical failure or blocker"
                )
            if self.status != "BLOCKED":
                raise ValueError(
                    "REJECT media QA report must use BLOCKED artifact status"
                )
        return self


class MediaShotRepair(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    shot_id: NonEmptyStr
    check_ids: List[NonEmptyStr] = Field(min_length=1)
    action: Literal[
        "rerender_subtitle",
        "recomposite_plate",
        "regenerate_background",
        "recompose_final",
    ]
    reason: NonEmptyStr
    provider_call_required: bool = False


class MediaRepairDecisionArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_repair_decision.v1"] = (
        "product_creative.media_repair_decision.v1"
    )
    qa_report_id: NonEmptyStr
    decision: Literal[
        "LOCAL_REPAIR",
        "PROVIDER_REPAIR",
        "HUMAN_REVIEW",
        "REJECT",
    ]
    repair_round: int = Field(ge=1, le=2)
    shot_repairs: List[MediaShotRepair] = Field(default_factory=list)
    preserved_shot_ids: List[NonEmptyStr] = Field(default_factory=list)
    estimated_provider_calls: int = Field(default=0, ge=0, le=5)
    authorization_required: bool = False
    reason: NonEmptyStr

    @model_validator(mode="after")
    def validate_media_repair_decision(self) -> "MediaRepairDecisionArtifact":
        repair_shots = [item.shot_id for item in self.shot_repairs]
        if len(repair_shots) != len(set(repair_shots)):
            raise ValueError("media repair decision requires unique repaired shots")
        if len(self.preserved_shot_ids) != len(set(self.preserved_shot_ids)):
            raise ValueError("media repair decision requires unique preserved shots")
        if set(repair_shots) & set(self.preserved_shot_ids):
            raise ValueError("preserved shots cannot also be repaired")
        provider_required = (
            self.estimated_provider_calls > 0
            or any(item.provider_call_required for item in self.shot_repairs)
        )
        if self.authorization_required != provider_required:
            raise ValueError(
                "authorization_required must match Provider repair calls"
            )
        if self.decision == "LOCAL_REPAIR":
            if not self.shot_repairs or provider_required:
                raise ValueError(
                    "LOCAL_REPAIR requires local-only shot repairs"
                )
            if self.status != "NEEDS_REVISION":
                raise ValueError(
                    "LOCAL_REPAIR must use NEEDS_REVISION artifact status"
                )
        elif self.decision == "PROVIDER_REPAIR":
            if not self.shot_repairs or not provider_required:
                raise ValueError(
                    "PROVIDER_REPAIR requires an authorized Provider repair"
                )
            if self.status != "NEEDS_REVISION":
                raise ValueError(
                    "PROVIDER_REPAIR must use NEEDS_REVISION artifact status"
                )
        else:
            if self.shot_repairs or provider_required:
                raise ValueError(
                    "terminal media repair decisions cannot claim repairs"
                )
            if self.status != "BLOCKED":
                raise ValueError(
                    "terminal media repair decisions must use BLOCKED status"
                )
        return self


class MediaHumanOverrideArtifact(ProfessionalArtifact):
    schema_name: Literal["product_creative.media_human_override.v1"] = (
        "product_creative.media_human_override.v1"
    )
    qa_report_id: NonEmptyStr
    decision: Literal["approve", "reject", "accept_with_warning"]
    reason: NonEmptyStr
    actor: NonEmptyStr
    confirmation_id: NonEmptyStr
    receipt_id: NonEmptyStr

    @model_validator(mode="after")
    def align_media_human_override(self) -> "MediaHumanOverrideArtifact":
        expected_status = "BLOCKED" if self.decision == "reject" else "PASS"
        if self.status != expected_status:
            raise ValueError(
                f"{self.decision} media override must use {expected_status} status"
            )
        return self


ProfessionalArtifactType = (
    CreativeTaskBriefArtifact
    | ProductGroundingPackArtifact
    | ResearchInsightPackArtifact
    | CreativeCandidateArtifact
    | CreativeDecisionArtifact
    | StoryPackageArtifact
    | ProductionBibleArtifact
    | MediaDependencyReportArtifact
    | ProductPlateArtifact
    | MediaExecutionPlanArtifact
    | MediaShotResultArtifact
    | MediaCompositeManifestArtifact
    | QaReportArtifact
    | BusinessSkillExecutionArtifact
    | MediaQaReportArtifact
    | MediaRepairDecisionArtifact
    | MediaHumanOverrideArtifact
)


_MODELS: Dict[str, Type[ProfessionalArtifact]] = {
    model.model_fields["schema_name"].default: model
    for model in (
        CreativeTaskBriefArtifact,
        ProductGroundingPackArtifact,
        ResearchInsightPackArtifact,
        CreativeCandidateArtifact,
        CreativeDecisionArtifact,
        StoryPackageArtifact,
        ProductionBibleArtifact,
        MediaDependencyReportArtifact,
        ProductPlateArtifact,
        MediaExecutionPlanArtifact,
        MediaShotResultArtifact,
        MediaCompositeManifestArtifact,
        QaReportArtifact,
        BusinessSkillExecutionArtifact,
        MediaQaReportArtifact,
        MediaRepairDecisionArtifact,
        MediaHumanOverrideArtifact,
    )
}


def professional_artifact_model(schema_name: str) -> Type[ProfessionalArtifact]:
    try:
        return _MODELS[schema_name]
    except KeyError as exc:
        raise ValueError(f"unsupported professional artifact schema '{schema_name}'") from exc
