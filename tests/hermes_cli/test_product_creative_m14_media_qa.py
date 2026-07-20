from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import sys

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENT = ROOT / ".hermes" / "plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))


NOW = "2026-07-17T00:00:00+00:00"


@pytest.fixture(autouse=True)
def _isolated_product_creative_workspace(tmp_path):
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        yield


def _base(artifact_id: str, schema_name: str) -> dict:
    return {
        "schema_name": schema_name,
        "artifact_id": artifact_id,
        "task_id": "task-m14",
        "product_id": "honeydew",
        "created_at": NOW,
        "source_refs": ["media-composite-task-m14"],
        "status": "READY",
    }


def _check(
    *,
    check_id: str = "technical-codec",
    status: str = "PASS",
    severity: str = "low",
    shot_id: str = "",
    repairable: bool = False,
) -> dict:
    return {
        "check_id": check_id,
        "category": "technical",
        "scope": "final",
        "status": status,
        "severity": severity,
        "shot_id": shot_id,
        "time_range": [0.0, 10.0],
        "expected": {"codec": "h264"},
        "observed": {"codec": "h264" if status == "PASS" else "unknown"},
        "evidence": ["ffprobe:final"],
        "repairable": repairable,
    }


def _configure_local_media_tools(monkeypatch):
    known_root = Path(
        r"C:\Program Files\AIMIXMaster\resources\app.asar.unpacked"
        r"\node_modules\ffmpeg-static-all\win\bin"
    )
    packaged_ffmpeg = known_root / "ffmpeg.exe"
    packaged_ffprobe = known_root / "ffprobe.exe"
    ffmpeg = (
        packaged_ffmpeg
        if packaged_ffmpeg.is_file()
        else Path(shutil.which("ffmpeg") or "")
    )
    ffprobe = (
        packaged_ffprobe
        if packaged_ffprobe.is_file()
        else Path(shutil.which("ffprobe") or "")
    )
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("local ffmpeg/ffprobe are required for M14 media QA")
    monkeypatch.setenv("PRODUCT_CREATIVE_FFMPEG_PATH", str(ffmpeg))
    monkeypatch.setenv("PRODUCT_CREATIVE_FFPROBE_PATH", str(ffprobe))


def _technical_fixture(
    monkeypatch,
    *,
    black_shot: str = "",
    caption: str = "",
    with_plate: bool = False,
    motion_required: bool = False,
    frozen_shot: str = "",
):
    from PIL import Image, ImageDraw

    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.common import ensure_product
    from product_creative.contracts.creative_artifacts import (
        MediaExecutionPlanArtifact,
        ProductPlateArtifact,
        ProductionBibleArtifact,
    )
    from product_creative.runtime.media_compositor import (
        compose_final_video,
        render_shot,
    )
    from product_creative.runtime.media_dependencies import resolve_media_tool
    from product_creative.runtime.professional_artifacts import (
        save_professional_artifact,
    )

    _configure_local_media_tools(monkeypatch)
    fixture_duration = 2.0 if frozen_shot else 0.8
    create_product("honeydew", "周十五蜂蜜露")
    product_root = ensure_product("honeydew")
    plate = None
    if with_plate:
        plate_path = product_root / "artifacts" / "product_plates" / "m14-plate.png"
        plate_path.parent.mkdir(parents=True, exist_ok=True)
        plate_image = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        plate_draw = ImageDraw.Draw(plate_image)
        plate_draw.rounded_rectangle(
            (6, 8, 74, 72),
            radius=15,
            fill=(238, 55, 135, 255),
            outline=(255, 255, 255, 255),
            width=3,
        )
        plate_draw.rectangle((20, 28, 60, 34), fill=(255, 255, 255, 255))
        plate_draw.rectangle((25, 43, 55, 49), fill=(255, 255, 255, 255))
        plate_image.save(plate_path)
        plate_hash = hashlib.sha256(plate_path.read_bytes()).hexdigest()
        plate = ProductPlateArtifact(
            **_base(
                "product-plate-task-m14",
                "product_creative.product_plate.v1",
            ),
            source_material_id="material-main",
            source_content_hash=plate_hash,
            plate_relative_path=str(plate_path.relative_to(product_root)),
            plate_content_hash=plate_hash,
            mask_mode="source_alpha",
            source_size=[80, 80],
            plate_size=[80, 80],
            allowed_transforms=[
                "uniform_scale",
                "translate",
                "alpha_composite",
            ],
            forbidden_transforms=["redraw", "change_packaging_text"],
        )
        save_professional_artifact(plate)
    bible = ProductionBibleArtifact(
        **_base(
            "production-bible-task-m14",
            "product_creative.production_bible.v1",
        ),
        specification={
            "aspect_ratio": "2:3",
            "canvas": [160, 240],
            "fps": 8,
        },
        shots=[
            {
                "shot_id": "shot-01",
                "duration_seconds": fixture_duration,
                "composition": "medium shot",
                "action": "主角发现问题并停下动作",
                "characters": ["主角"],
                "scene": "明亮室内",
                "input_materials": [],
                "caption": "",
                "narrative_function": "视觉钩子与问题建立",
            },
            {
                "shot_id": "shot-02",
                "duration_seconds": fixture_duration,
                "composition": "product close-up",
                "action": "产品介入并完成情绪收束",
                "characters": ["主角"],
                "scene": "明亮室内",
                "input_materials": ["material-main"] if with_plate else [],
                "caption": caption,
                "narrative_function": "产品转折与结尾收束",
            },
        ],
        asset_roles=(
            {"material-main": "immutable_product_plate"}
            if with_plate
            else {"fixture-background": "generated_background"}
        ),
        packaging_strategy=(
            "exact-main-composite" if with_plate else "background-only"
        ),
        continuity_rules=["主角身份、服装与空间在相邻镜头保持一致"],
        provider_mapping={"shot_backgrounds": "local-fixture"},
        retry_policy={"max_retries_per_shot": 1},
        delivery_requirements=["可播放 MP4", "叙事有钩子、推进和结尾"],
    )
    save_professional_artifact(bible)
    plan = MediaExecutionPlanArtifact(
        **_base(
            "media-plan-task-m14",
            "product_creative.media_execution_plan.v1",
        ),
        production_bible_id="production-bible-task-m14",
        production_bible_hash=bible.content_hash,
        dependency_report_id="media-dependencies-task-m14",
        product_plate_id=plate.artifact_id if plate else "",
        aspect_ratio="2:3",
        canvas=[160, 240],
        fps=8,
        shots=[
            {
                "shot_id": "shot-01",
                "ordinal": 1,
                "duration_seconds": fixture_duration,
                "execution_mode": "local_motion",
                "product_plate_required": False,
                "prompt": "fixture scene one",
                "motion_required": motion_required,
                "motion_description": "主角发现问题并停下动作",
                "maximum_freeze_ratio": 0.65,
                "caption": "",
                "input_materials": [],
                "max_attempts": 2,
                "idempotency_key": "task-m14:shot-01",
            },
            {
                "shot_id": "shot-02",
                "ordinal": 2,
                "duration_seconds": fixture_duration,
                "execution_mode": "local_motion",
                "product_plate_required": with_plate,
                "prompt": "fixture scene two",
                "motion_required": motion_required,
                "motion_description": "产品介入并完成情绪收束",
                "maximum_freeze_ratio": 0.65,
                "caption": caption,
                "input_materials": [],
                "max_attempts": 2,
                "idempotency_key": "task-m14:shot-02",
            },
        ],
        output_requirements={
            "codec": "h264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "subtitle_mode": "deterministic_ass",
        },
        call_budget={"image": 0, "video": 0},
    )
    save_professional_artifact(plan)
    sources = product_root / "artifacts" / "m14-fixtures"
    sources.mkdir(parents=True, exist_ok=True)
    rendered = []
    for index, shot in enumerate(plan.shots, 1):
        if shot.shot_id == black_shot:
            source = sources / f"{shot.shot_id}.png"
            image = Image.new("RGB", plan.canvas, (0, 0, 0))
            image.save(source)
        elif frozen_shot:
            source = sources / f"{shot.shot_id}.mp4"
            ffmpeg = resolve_media_tool("ffmpeg")
            assert ffmpeg
            import subprocess

            lavfi = (
                f"color=c=pink:size=160x240:rate=8:duration={fixture_duration:g}"
                if shot.shot_id == frozen_shot
                else (
                    "testsrc2=size=160x240:rate=8:"
                    f"duration={fixture_duration:g}"
                )
            )
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    lavfi,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(source),
                ],
                check=True,
                capture_output=True,
            )
        else:
            source = sources / f"{shot.shot_id}.png"
            color = (40, 160, 220) if index == 1 else (230, 110, 160)
            image = Image.new("RGB", plan.canvas, color)
            draw = ImageDraw.Draw(image)
            draw.rectangle((20, 30, 140, 210), outline=(255, 255, 255), width=8)
            draw.ellipse((55, 80, 105, 130), fill=(255, 210, 30))
            image.save(source)
        rendered.append(
            render_shot(
                "honeydew",
                plan=plan,
                shot=shot,
                source_media=source,
                product_plate=plate,
                attempt=1,
            )
        )
    assert all(item.execution_status == "COMPLETED" for item in rendered)
    manifest = compose_final_video(
        "honeydew",
        plan=plan,
        shot_results=rendered,
    )
    return plan, rendered, manifest, plate


def test_m14_media_qa_artifacts_are_registered_and_tamper_evident():
    from product_creative.contracts.creative_artifacts import (
        MediaHumanOverrideArtifact,
        MediaQaReportArtifact,
        MediaRepairDecisionArtifact,
        professional_artifact_model,
    )

    report = MediaQaReportArtifact.model_validate(
        {
            **_base(
                "media-qa-task-m14-run-1",
                "product_creative.media_qa_report.v1",
            ),
            "status": "PASS",
            "plan_id": "media-plan-task-m14",
            "manifest_id": "media-composite-task-m14",
            "qa_run": 1,
            "overall_result": "PASS",
            "checks": [_check()],
            "failed_shot_ids": [],
            "hard_blockers": [],
            "warnings": [],
            "evidence_refs": ["media-composite-task-m14"],
            "model_provenance": {"mode": "deterministic"},
        }
    )
    repair = MediaRepairDecisionArtifact.model_validate(
        {
            **_base(
                "media-repair-task-m14-round-1",
                "product_creative.media_repair_decision.v1",
            ),
            "status": "NEEDS_REVISION",
            "qa_report_id": "media-qa-task-m14-run-2",
            "decision": "LOCAL_REPAIR",
            "repair_round": 1,
            "shot_repairs": [
                {
                    "shot_id": "shot-02",
                    "check_ids": ["subtitle-readable"],
                    "action": "rerender_subtitle",
                    "reason": "subtitle is clipped",
                    "provider_call_required": False,
                }
            ],
            "preserved_shot_ids": ["shot-01", "shot-03"],
            "estimated_provider_calls": 0,
            "authorization_required": False,
            "reason": "Only the deterministic subtitle layer must be rendered again.",
        }
    )
    override = MediaHumanOverrideArtifact.model_validate(
        {
            **_base(
                "media-override-task-m14-run-1",
                "product_creative.media_human_override.v1",
            ),
            "status": "PASS",
            "qa_report_id": report.artifact_id,
            "decision": "approve",
            "reason": "Reviewed the complete media output.",
            "actor": "internal-operator",
            "confirmation_id": "confirmation-m14",
            "receipt_id": "receipt-m14",
        }
    )

    for artifact in (report, repair, override):
        model = professional_artifact_model(artifact.schema_name)
        assert model is type(artifact)
        assert len(artifact.content_hash) == 64
        with pytest.raises(ValidationError, match="content_hash"):
            model.model_validate(
                {
                    **artifact.model_dump(mode="json"),
                    "content_hash": "0" * 64,
                }
            )


def test_media_qa_pass_rejects_unknown_or_failed_checks():
    from product_creative.contracts.creative_artifacts import MediaQaReportArtifact

    for check in (
        _check(status="UNKNOWN", severity="high"),
        _check(status="FAIL", severity="critical"),
    ):
        with pytest.raises(
            ValidationError,
            match="PASS media QA report",
        ):
            MediaQaReportArtifact.model_validate(
                {
                    **_base(
                        "media-qa-task-m14-run-1",
                        "product_creative.media_qa_report.v1",
                    ),
                    "status": "PASS",
                    "plan_id": "media-plan-task-m14",
                    "manifest_id": "media-composite-task-m14",
                    "qa_run": 1,
                    "overall_result": "PASS",
                    "checks": [check],
                    "failed_shot_ids": [],
                    "hard_blockers": [],
                    "warnings": [],
                    "evidence_refs": ["media-composite-task-m14"],
                    "model_provenance": {"mode": "deterministic"},
                }
            )


def test_media_qa_repair_requires_repairable_failed_shot():
    from product_creative.contracts.creative_artifacts import MediaQaReportArtifact

    with pytest.raises(
        ValidationError,
        match="REPAIR media QA report",
    ):
        MediaQaReportArtifact.model_validate(
            {
                **_base(
                    "media-qa-task-m14-run-1",
                    "product_creative.media_qa_report.v1",
                ),
                "status": "NEEDS_REVISION",
                "plan_id": "media-plan-task-m14",
                "manifest_id": "media-composite-task-m14",
                "qa_run": 1,
                "overall_result": "REPAIR",
                "checks": [
                    _check(
                        check_id="packaging-fidelity",
                        status="FAIL",
                        severity="critical",
                        shot_id="shot-02",
                        repairable=False,
                    )
                ],
                "failed_shot_ids": ["shot-02"],
                "hard_blockers": ["Packaging fidelity cannot be proven."],
                "warnings": [],
                "evidence_refs": ["frame:shot-02:1.0"],
                "model_provenance": {"mode": "deterministic"},
            }
        )


def test_media_qa_failed_shot_ids_must_match_failed_checks():
    from product_creative.contracts.creative_artifacts import MediaQaReportArtifact

    with pytest.raises(
        ValidationError,
        match="failed_shot_ids",
    ):
        MediaQaReportArtifact.model_validate(
            {
                **_base(
                    "media-qa-task-m14-run-1",
                    "product_creative.media_qa_report.v1",
                ),
                "status": "NEEDS_REVISION",
                "plan_id": "media-plan-task-m14",
                "manifest_id": "media-composite-task-m14",
                "qa_run": 1,
                "overall_result": "REPAIR",
                "checks": [
                    _check(
                        check_id="subtitle-readable",
                        status="FAIL",
                        severity="high",
                        shot_id="shot-02",
                        repairable=True,
                    )
                ],
                "failed_shot_ids": ["shot-03"],
                "hard_blockers": [],
                "warnings": [],
                "evidence_refs": ["subtitle:shot-02"],
                "model_provenance": {"mode": "deterministic"},
            }
        )


def test_media_repair_decision_preserves_unaffected_shots_and_authorization_boundary():
    from product_creative.contracts.creative_artifacts import (
        MediaRepairDecisionArtifact,
    )

    with pytest.raises(
        ValidationError,
        match="authorization_required",
    ):
        MediaRepairDecisionArtifact.model_validate(
            {
                **_base(
                    "media-repair-task-m14-round-1",
                    "product_creative.media_repair_decision.v1",
                ),
                "status": "NEEDS_REVISION",
                "qa_report_id": "media-qa-task-m14-run-1",
                "decision": "PROVIDER_REPAIR",
                "repair_round": 1,
                "shot_repairs": [
                    {
                        "shot_id": "shot-02",
                        "check_ids": ["character-continuity"],
                        "action": "regenerate_background",
                        "reason": "character identity changed",
                        "provider_call_required": True,
                    }
                ],
                "preserved_shot_ids": ["shot-01", "shot-03"],
                "estimated_provider_calls": 1,
                "authorization_required": False,
                "reason": "A provider-generated background must be replaced.",
            }
        )

    with pytest.raises(
        ValidationError,
        match="preserved shots",
    ):
        MediaRepairDecisionArtifact.model_validate(
            {
                **_base(
                    "media-repair-task-m14-round-1",
                    "product_creative.media_repair_decision.v1",
                ),
                "status": "NEEDS_REVISION",
                "qa_report_id": "media-qa-task-m14-run-1",
                "decision": "LOCAL_REPAIR",
                "repair_round": 1,
                "shot_repairs": [
                    {
                        "shot_id": "shot-02",
                        "check_ids": ["subtitle-readable"],
                        "action": "rerender_subtitle",
                        "reason": "subtitle is clipped",
                        "provider_call_required": False,
                    }
                ],
                "preserved_shot_ids": ["shot-01", "shot-02"],
                "estimated_provider_calls": 0,
                "authorization_required": False,
                "reason": "Only the subtitle layer must be replaced.",
            }
        )


def test_media_qa_contracts_reject_extra_fields_and_sensitive_model_metadata():
    from product_creative.contracts.creative_artifacts import MediaQaReportArtifact

    payload = {
        **_base(
            "media-qa-task-m14-run-1",
            "product_creative.media_qa_report.v1",
        ),
        "status": "PASS",
        "plan_id": "media-plan-task-m14",
        "manifest_id": "media-composite-task-m14",
        "qa_run": 1,
        "overall_result": "PASS",
        "checks": [_check()],
        "failed_shot_ids": [],
        "hard_blockers": [],
        "warnings": [],
        "evidence_refs": ["media-composite-task-m14"],
        "model_provenance": {"mode": "deterministic"},
    }
    with pytest.raises(ValidationError, match="extra_forbidden"):
        MediaQaReportArtifact.model_validate({**payload, "unexpected": True})
    with pytest.raises(ValidationError, match="sensitive"):
        MediaQaReportArtifact.model_validate(
            {
                **payload,
                "model_provenance": {
                    "mode": "vlm",
                    "api_key": "must-not-be-stored",
                },
            }
        )


def test_technical_media_qa_passes_required_container_stream_and_timing_checks(
    monkeypatch,
):
    from product_creative.runtime.media_technical_qa import (
        inspect_media_technical_quality,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)
    checks = inspect_media_technical_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
    )
    by_id = {item.check_id: item for item in checks}

    for check_id in (
        "final-file-readable",
        "final-video-codec",
        "final-pixel-format",
        "final-audio-codec",
        "final-canvas",
        "final-fps",
        "final-duration",
        "final-faststart",
        "shot-order",
    ):
        assert by_id[check_id].status == "PASS"
    assert all(
        by_id[f"shot-duration:{shot.shot_id}"].status == "PASS"
        for shot in plan.shots
    )


def test_technical_media_qa_detects_black_shot_with_repair_target(monkeypatch):
    from product_creative.runtime.media_technical_qa import (
        inspect_media_technical_quality,
    )

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        black_shot="shot-01",
    )
    checks = inspect_media_technical_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
    )
    black = next(item for item in checks if item.check_id == "black-frame:shot-01")

    assert black.status == "FAIL"
    assert black.severity == "high"
    assert black.shot_id == "shot-01"
    assert black.repairable is True
    assert black.evidence


def test_motion_required_freeze_ratio_is_a_hard_repairable_failure(
    tmp_path,
    monkeypatch,
):
    import product_creative.runtime.media_technical_qa as technical_qa

    monkeypatch.setattr(
        technical_qa,
        "_ffmpeg_analysis",
        lambda *_args, **_kwargs: "freeze_duration: 0.90",
    )

    check = technical_qa._freeze_check(
        tmp_path / "dynamic-shot.mp4",
        shot_id="shot-01",
        duration=1.0,
        motion_required=True,
        maximum_freeze_ratio=0.65,
    )

    assert check.status == "FAIL"
    assert check.severity == "high"
    assert check.repairable is True
    assert check.expected["motion_required"] is True
    assert check.expected["maximum_freeze_ratio"] == pytest.approx(0.65)


def test_technical_media_qa_rejects_manifest_shot_order_drift(monkeypatch):
    from product_creative.contracts.creative_artifacts import (
        MediaCompositeManifestArtifact,
    )
    from product_creative.runtime.media_technical_qa import (
        inspect_media_technical_quality,
    )
    from product_creative.runtime.professional_artifacts import (
        save_professional_artifact,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)
    payload = manifest.model_dump(mode="json", exclude={"content_hash"})
    payload["artifact_id"] = "media-composite-task-m14-reordered"
    payload["shot_result_ids"] = list(reversed(payload["shot_result_ids"]))
    reordered = MediaCompositeManifestArtifact.model_validate(payload)
    save_professional_artifact(reordered)

    checks = inspect_media_technical_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=reordered.artifact_id,
    )
    order = next(item for item in checks if item.check_id == "shot-order")

    assert order.status == "FAIL"
    assert order.severity == "critical"
    assert order.repairable is False
    assert order.expected["shot_ids"] == ["shot-01", "shot-02"]
    assert order.observed["shot_ids"] == ["shot-02", "shot-01"]


def test_subtitle_qa_is_unknown_without_a_real_ocr_adapter(monkeypatch):
    from product_creative.runtime.media_text_qa import inspect_media_text_quality

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        caption="准备好，再出发",
    )
    checks = inspect_media_text_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=None,
    )
    source = next(item for item in checks if item.check_id == "subtitle-source:shot-02")
    visible = next(item for item in checks if item.check_id == "subtitle-visible:shot-02")

    assert source.status == "PASS"
    assert visible.status == "UNKNOWN"
    assert visible.severity == "high"
    assert visible.repairable is False


def test_subtitle_qa_accepts_high_confidence_visible_text_in_safe_area(monkeypatch):
    from product_creative.runtime.media_text_qa import inspect_media_text_quality

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        caption="准备好，再出发",
    )

    def fixture_ocr(**_kwargs):
        return {
            "observed_text": "准备好，再出发",
            "confidence": 0.98,
            "bounding_box": [0.15, 0.78, 0.70, 0.10],
            "visible_duration_seconds": 0.8,
            "evidence_refs": ["ocr-fixture:shot-02"],
        }

    checks = inspect_media_text_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=fixture_ocr,
    )
    by_id = {item.check_id: item for item in checks}

    assert by_id["subtitle-visible:shot-02"].status == "PASS"
    assert by_id["subtitle-safe-area:shot-02"].status == "PASS"
    assert by_id["subtitle-duration:shot-02"].status == "PASS"


def test_subtitle_qa_detects_garbled_ass_source(monkeypatch):
    from product_creative.common import ensure_product
    from product_creative.runtime.media_text_qa import inspect_media_text_quality

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        caption="准备好，再出发",
    )
    subtitle = (
        ensure_product("honeydew")
        / "artifacts"
        / "media_shots"
        / plan.artifact_id
        / "02-shot-02.ass"
    )
    text = subtitle.read_text(encoding="utf-8-sig")
    subtitle.write_text(
        text.replace("准备好，再出发", "���???"),
        encoding="utf-8-sig",
    )

    checks = inspect_media_text_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=None,
    )
    source = next(item for item in checks if item.check_id == "subtitle-source:shot-02")

    assert source.status == "FAIL"
    assert source.severity == "critical"
    assert source.repairable is True


def test_packaging_visual_qa_passes_immutable_plate_composite(monkeypatch):
    from product_creative.runtime.packaging_visual_qa import (
        inspect_packaging_visual_quality,
    )

    plan, _shots, manifest, plate = _technical_fixture(
        monkeypatch,
        with_plate=True,
    )
    checks = inspect_packaging_visual_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        product_plate_id=plate.artifact_id,
    )
    by_id = {item.check_id: item for item in checks}

    assert by_id["packaging-source-integrity:shot-02"].status == "PASS"
    assert by_id["packaging-compositor-provenance:shot-02"].status == "PASS"
    assert by_id["packaging-fidelity:shot-02"].status == "PASS"
    assert by_id["packaging-fidelity:shot-02"].observed["mean_absolute_error"] < 24


def test_packaging_visual_qa_detects_occluded_product_region(monkeypatch):
    from product_creative.common import ensure_product
    from product_creative.contracts.creative_artifacts import (
        MediaShotResultArtifact,
    )
    from product_creative.runtime.media_compositor import compose_final_video
    from product_creative.runtime.media_dependencies import resolve_media_tool
    from product_creative.runtime.packaging_visual_qa import (
        inspect_packaging_visual_quality,
    )
    from product_creative.runtime.professional_artifacts import (
        save_professional_artifact,
    )

    plan, shots, _manifest, plate = _technical_fixture(
        monkeypatch,
        with_plate=True,
    )
    product_root = ensure_product("honeydew")
    original = product_root / shots[1].output_relative_path
    tampered = original.with_name("02-shot-02-occluded.mp4")
    ffmpeg = resolve_media_tool("ffmpeg")
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(original),
        "-vf",
        "drawbox=x=40:y=140:w=80:h=80:color=green:t=fill",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(tampered),
    ]
    import subprocess

    subprocess.run(command, check=True, capture_output=True)
    tampered_result = MediaShotResultArtifact(
        **_base(
            "media-shot-task-m14-shot-02-attempt-2",
            "product_creative.media_shot_result.v1",
        ),
        plan_id=plan.artifact_id,
        shot_id="shot-02",
        attempt=2,
        execution_status="COMPLETED",
        provider="local-compositor",
        external_call_performed=False,
        input_hashes=dict(shots[1].input_hashes),
        output_relative_path=str(tampered.relative_to(product_root)),
        output_content_hash=hashlib.sha256(tampered.read_bytes()).hexdigest(),
        duration_seconds=shots[1].duration_seconds,
        command_summary=list(shots[1].command_summary),
    )
    save_professional_artifact(tampered_result)
    manifest = compose_final_video(
        "honeydew",
        plan=plan,
        shot_results=[shots[0], tampered_result],
    )

    checks = inspect_packaging_visual_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        product_plate_id=plate.artifact_id,
    )
    fidelity = next(
        item
        for item in checks
        if item.check_id == "packaging-fidelity:shot-02"
    )

    assert fidelity.status == "FAIL"
    assert fidelity.severity == "critical"
    assert fidelity.shot_id == "shot-02"
    assert fidelity.repairable is True


def test_story_continuity_qa_passes_structure_and_fixture_visual_observations(
    monkeypatch,
):
    from product_creative.runtime.story_continuity_qa import (
        inspect_story_continuity_quality,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.97,
            "characters": ["主角"],
            "scene": "明亮室内",
            "product_visible": kwargs["shot_id"] == "shot-02",
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    checks = inspect_story_continuity_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        visual_adapter=fixture_visual,
    )
    by_id = {item.check_id: item for item in checks}

    assert by_id["story-structure"].status == "PASS"
    assert by_id["story-shot-coverage"].status == "PASS"
    assert by_id["visual-continuity:shot-01:shot-02"].status == "PASS"


def test_story_continuity_qa_fails_closed_without_visual_adapter(monkeypatch):
    from product_creative.runtime.story_continuity_qa import (
        inspect_story_continuity_quality,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)
    checks = inspect_story_continuity_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        visual_adapter=None,
    )
    visual = next(
        item
        for item in checks
        if item.check_id == "visual-continuity:shot-01:shot-02"
    )

    assert visual.status == "UNKNOWN"
    assert visual.severity == "high"
    assert visual.repairable is False


def test_story_action_fulfillment_fails_when_planned_motion_did_not_complete(
    monkeypatch,
):
    from product_creative.runtime.story_continuity_qa import (
        inspect_story_continuity_quality,
    )

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        motion_required=True,
    )

    def fixture_visual(**kwargs):
        completed = kwargs["shot_id"] != "shot-01"
        return {
            "confidence": 0.97,
            "characters": ["主角"],
            "scene": "明亮室内",
            "product_visible": kwargs["shot_id"] == "shot-02",
            "observed_action": (
                "主角静止站立" if not completed else kwargs["expected_action"]
            ),
            "action_completed": completed,
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    checks = inspect_story_continuity_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        visual_adapter=fixture_visual,
    )
    by_id = {item.check_id: item for item in checks}

    assert by_id["action-fulfillment:shot-01"].status == "FAIL"
    assert by_id["action-fulfillment:shot-01"].severity == "high"
    assert by_id["action-fulfillment:shot-01"].repairable is True
    assert by_id["action-fulfillment:shot-02"].status == "PASS"


def test_story_action_fulfillment_is_unknown_without_an_adapter(monkeypatch):
    from product_creative.runtime.story_continuity_qa import (
        inspect_story_continuity_quality,
    )

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        motion_required=True,
    )
    checks = inspect_story_continuity_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        visual_adapter=None,
    )

    action = next(
        item
        for item in checks
        if item.check_id == "action-fulfillment:shot-01"
    )
    assert action.status == "UNKNOWN"
    assert action.severity == "high"
    assert action.repairable is False


def test_story_action_fulfillment_is_unknown_below_confidence_gate(monkeypatch):
    from product_creative.runtime.story_continuity_qa import (
        inspect_story_continuity_quality,
    )

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        motion_required=True,
    )

    def low_confidence_visual(**kwargs):
        return {
            "confidence": 0.4,
            "characters": list(kwargs["expected_characters"]),
            "scene": kwargs["expected_scene"],
            "product_visible": kwargs["expected_product_visible"],
            "observed_action": kwargs["expected_action"],
            "action_completed": True,
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    checks = inspect_story_continuity_quality(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        visual_adapter=low_confidence_visual,
    )
    action = next(
        item
        for item in checks
        if item.check_id == "action-fulfillment:shot-01"
    )

    assert action.status == "UNKNOWN"
    assert action.observed["confidence"] == pytest.approx(0.4)


def test_frozen_dynamic_shot_creates_scoped_provider_repair(monkeypatch):
    from product_creative.runtime.media_qa import run_media_qa
    from product_creative.runtime.media_repair import plan_media_repair

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        motion_required=True,
        frozen_shot="shot-01",
    )

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": list(kwargs["expected_characters"]),
            "scene": kwargs["expected_scene"],
            "product_visible": kwargs["expected_product_visible"],
            "observed_action": kwargs["expected_action"],
            "action_completed": True,
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    report = run_media_qa(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=None,
        visual_adapter=fixture_visual,
    )
    by_id = {item.check_id: item for item in report.checks}
    assert by_id["freeze-frame:shot-01"].status == "FAIL", [
        (item.check_id, item.status, item.observed)
        for item in report.checks
        if item.status != "PASS"
    ]
    assert by_id["freeze-frame:shot-02"].status == "PASS"
    assert report.overall_result == "REPAIR"
    assert report.failed_shot_ids == ["shot-01"]
    decision = plan_media_repair(
        "honeydew",
        qa_report_id=report.artifact_id,
        repair_round=1,
    )
    assert [item.shot_id for item in decision.shot_repairs] == ["shot-01"]
    assert decision.shot_repairs[0].action == "regenerate_background"
    assert decision.preserved_shot_ids == ["shot-02"]


def test_unified_media_qa_persists_pass_report_with_fixture_adapters(monkeypatch):
    from product_creative.runtime.media_qa import run_media_qa
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": ["主角"],
            "scene": "明亮室内",
            "product_visible": kwargs["shot_id"] == "shot-02",
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    report = run_media_qa(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=None,
        visual_adapter=fixture_visual,
    )
    persisted = load_professional_artifact("honeydew", report.artifact_id)

    assert report.overall_result == "PASS"
    assert report.status == "PASS"
    assert persisted.content_hash == report.content_hash
    assert all(item.status != "UNKNOWN" for item in report.checks)


def test_unified_media_qa_routes_black_shot_to_repair(monkeypatch):
    from product_creative.runtime.media_qa import run_media_qa
    from product_creative.runtime.media_repair import plan_media_repair

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        black_shot="shot-01",
    )

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": ["主角"],
            "scene": "明亮室内",
            "product_visible": kwargs["shot_id"] == "shot-02",
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    report = run_media_qa(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=None,
        visual_adapter=fixture_visual,
    )
    decision = plan_media_repair(
        "honeydew",
        qa_report_id=report.artifact_id,
        repair_round=1,
    )

    assert report.overall_result == "REPAIR"
    assert report.failed_shot_ids == ["shot-01"]
    assert decision.decision == "PROVIDER_REPAIR"
    assert [item.shot_id for item in decision.shot_repairs] == ["shot-01"]
    assert decision.preserved_shot_ids == ["shot-02"]
    assert decision.estimated_provider_calls == 1
    assert decision.authorization_required is True


def test_media_repair_stops_after_two_automatic_rounds(monkeypatch):
    from product_creative.runtime.media_qa import run_media_qa
    from product_creative.runtime.media_repair import plan_media_repair

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        black_shot="shot-01",
    )

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": ["主角"],
            "scene": "明亮室内",
            "product_visible": kwargs["shot_id"] == "shot-02",
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    report = run_media_qa(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=None,
        visual_adapter=fixture_visual,
        qa_run=3,
    )
    decision = plan_media_repair(
        "honeydew",
        qa_report_id=report.artifact_id,
        repair_round=3,
    )

    assert decision.decision == "HUMAN_REVIEW"
    assert decision.shot_repairs == []
    assert decision.preserved_shot_ids == ["shot-02"]
    assert decision.estimated_provider_calls == 0
    assert decision.authorization_required is False


def test_creative_task_enters_awaiting_feedback_only_after_media_qa_pass(
    monkeypatch,
):
    from types import SimpleNamespace

    from product_creative.runtime.media_production import (
        apply_media_quality_gate,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)
    task = SimpleNamespace(
        product_id="honeydew",
        task_id="task-m14",
        professional_artifacts={
            "media_execution_plan": plan.artifact_id,
            "media_composite_manifest": manifest.artifact_id,
        },
        status="GENERATING",
        current_stage="GENERATING",
        blocked_reason="",
        result_descriptors=[],
        updated_at=NOW,
    )

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": ["主角"],
            "scene": "明亮室内",
            "product_visible": kwargs["shot_id"] == "shot-02",
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    outcome = apply_media_quality_gate(
        task,
        manifest=manifest,
        authorization=None,
        ocr_adapter=None,
        visual_adapter=fixture_visual,
    )

    assert outcome["status"] == "PASS"
    assert task.status == "AWAITING_FEEDBACK"
    assert task.current_stage == "AWAITING_FEEDBACK"
    assert task.professional_artifacts["media_qa_report"]
    assert task.professional_artifacts["media_qa_reports"] == [
        task.professional_artifacts["media_qa_report"]
    ]


def test_creative_task_stays_in_quality_review_when_visual_qa_is_unknown(
    monkeypatch,
):
    from types import SimpleNamespace

    from product_creative.runtime.media_production import (
        apply_media_quality_gate,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)
    task = SimpleNamespace(
        product_id="honeydew",
        task_id="task-m14",
        professional_artifacts={
            "media_execution_plan": plan.artifact_id,
            "media_composite_manifest": manifest.artifact_id,
        },
        status="GENERATING",
        current_stage="GENERATING",
        blocked_reason="",
        result_descriptors=[],
        updated_at=NOW,
    )

    outcome = apply_media_quality_gate(
        task,
        manifest=manifest,
        authorization=None,
        ocr_adapter=None,
        visual_adapter=None,
    )

    assert outcome["status"] == "HUMAN_REVIEW"
    assert task.status == "READY"
    assert task.current_stage == "QUALITY_REVIEW"
    assert "human review" in task.blocked_reason.lower()


def test_creative_task_repair_requires_authorization_for_provider_shot(
    monkeypatch,
):
    from types import SimpleNamespace

    from product_creative.runtime.media_production import (
        apply_media_quality_gate,
    )

    plan, _shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        black_shot="shot-01",
    )
    task = SimpleNamespace(
        product_id="honeydew",
        task_id="task-m14",
        professional_artifacts={
            "media_execution_plan": plan.artifact_id,
            "media_composite_manifest": manifest.artifact_id,
        },
        status="GENERATING",
        current_stage="GENERATING",
        blocked_reason="",
        result_descriptors=[],
        updated_at=NOW,
    )

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": ["主角"],
            "scene": "明亮室内",
            "product_visible": kwargs["shot_id"] == "shot-02",
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    outcome = apply_media_quality_gate(
        task,
        manifest=manifest,
        authorization=None,
        ocr_adapter=None,
        visual_adapter=fixture_visual,
    )

    assert outcome["status"] == "BLOCKED_AUTHORIZATION"
    assert task.status == "BLOCKED_AUTHORIZATION"
    assert task.current_stage == "QUALITY_REVIEW"
    assert task.professional_artifacts["media_repair_decision"]


def test_repeated_confirmation_cannot_bypass_exhausted_provider_repair_budget(
    monkeypatch,
):
    from types import SimpleNamespace

    import product_creative.runtime.creative_tasks as creative_tasks
    import product_creative.runtime.media_production as media_production
    from product_creative.contracts.creative_artifacts import (
        MediaRepairDecisionArtifact,
    )
    from product_creative.runtime.professional_artifacts import (
        save_professional_artifact,
    )

    plan, _shots, _manifest, _plate = _technical_fixture(monkeypatch)
    repair = MediaRepairDecisionArtifact.model_validate(
        {
            **_base(
                "media-repair-task-m14-exhausted",
                "product_creative.media_repair_decision.v1",
            ),
            "status": "NEEDS_REVISION",
            "qa_report_id": "media-qa-task-m14-exhausted",
            "decision": "PROVIDER_REPAIR",
            "repair_round": 1,
            "shot_repairs": [
                {
                    "shot_id": "shot-01",
                    "check_ids": ["visual-continuity:shot-01"],
                    "action": "regenerate_background",
                    "reason": "character continuity failed",
                    "provider_call_required": True,
                }
            ],
            "preserved_shot_ids": ["shot-02"],
            "estimated_provider_calls": 1,
            "authorization_required": True,
            "reason": "One background requires Provider repair.",
        }
    )
    save_professional_artifact(repair)
    task = SimpleNamespace(
        product_id="honeydew",
        task_id="task-m14",
        authorization_id="authorization-exhausted",
        current_stage="AWAITING_FEEDBACK",
        status="AWAITING_FEEDBACK",
        blocked_reason="Provider repair budget is exhausted.",
        professional_artifacts={
            "media_execution_plan": plan.artifact_id,
            "media_repair_decision": repair.artifact_id,
        },
        updated_at=NOW,
    )
    monkeypatch.setattr(
        creative_tasks,
        "load_task_authorization",
        lambda *_args: SimpleNamespace(authorization_id="authorization-exhausted"),
    )
    monkeypatch.setattr(
        media_production,
        "_repair_authorized",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        media_production,
        "resume_reliable_media_production",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("exhausted repair must not reach Provider execution")
        ),
    )

    handled = creative_tasks._continue_media_quality_repair(
        task,
        "再次确认继续返修",
        force=True,
    )

    assert handled is True
    assert task.status == "BLOCKED_AUTHORIZATION"
    assert task.current_stage == "QUALITY_REVIEW"
    assert "exhausted" in task.blocked_reason.lower()


def test_media_qa_human_override_requires_confirmation_and_is_audited(
    monkeypatch,
):
    from product_creative.ports.runtime_repositories import recovery
    from product_creative.runtime.media_qa import run_media_qa
    from product_creative.runtime.media_review import (
        record_media_qa_decision,
    )
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )

    plan, _shots, manifest, _plate = _technical_fixture(monkeypatch)
    report = run_media_qa(
        "honeydew",
        plan_id=plan.artifact_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=None,
        visual_adapter=None,
    )
    original_hash = report.content_hash
    confirmation_id = recovery().request_confirmation(
        "honeydew",
        "product_media_qa_decide",
        report.artifact_id,
        "medium",
        "trace-m14-review",
    )
    result = record_media_qa_decision(
        "honeydew",
        qa_report_id=report.artifact_id,
        decision="accept_with_warning",
        reason="本地 fixture 无真实 VLM，但技术检查与剧情结构已通过。",
        actor="test-reviewer",
        confirmation_id=confirmation_id,
        trace_id="trace-m14-review",
    )
    override = load_professional_artifact(
        "honeydew",
        result["override"]["artifact_id"],
    )
    unchanged = load_professional_artifact(
        "honeydew",
        report.artifact_id,
    )
    replay = record_media_qa_decision(
        "honeydew",
        qa_report_id=report.artifact_id,
        decision="accept_with_warning",
        reason="本地 fixture 无真实 VLM，但技术检查与剧情结构已通过。",
        actor="test-reviewer",
        confirmation_id=confirmation_id,
        trace_id="trace-m14-review",
    )

    assert result["action_receipt"].startswith("sqlite:///")
    assert override.decision == "accept_with_warning"
    assert override.confirmation_id == confirmation_id
    assert unchanged.content_hash == original_hash
    assert replay["idempotent_replay"] is True
    assert replay["action_receipt"] == result["action_receipt"]


def test_local_subtitle_repair_reuses_retained_source_and_rechecks_full_video(
    monkeypatch,
):
    from types import SimpleNamespace

    from product_creative.common import ensure_product
    from product_creative.runtime.media_production import (
        apply_media_quality_gate,
        resume_reliable_media_production,
    )

    plan, shots, manifest, _plate = _technical_fixture(
        monkeypatch,
        caption="准备好，再出发",
    )
    product_root = ensure_product("honeydew")
    subtitle = (
        product_root
        / "artifacts"
        / "media_shots"
        / plan.artifact_id
        / "02-shot-02.ass"
    )
    subtitle.write_text("���???", encoding="utf-8-sig")
    task = SimpleNamespace(
        product_id="honeydew",
        task_id="task-m14",
        professional_artifacts={
            "media_execution_plan": plan.artifact_id,
            "media_composite_manifest": manifest.artifact_id,
            "media_shot_results": [
                item.artifact_id for item in shots
            ],
        },
        status="GENERATING",
        current_stage="GENERATING",
        blocked_reason="",
        result_descriptors=[],
        updated_at=NOW,
    )

    def fixture_ocr(**kwargs):
        return {
            "observed_text": kwargs["expected_text"],
            "confidence": 0.99,
            "bounding_box": [0.08, 0.78, 0.84, 0.10],
            "visible_duration_seconds": (
                kwargs["end_seconds"] - kwargs["start_seconds"]
            ),
            "evidence_refs": [f"ocr-fixture:{kwargs['shot_id']}"],
        }

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": list(kwargs["expected_characters"]),
            "scene": kwargs["expected_scene"],
            "product_visible": kwargs["expected_product_visible"],
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    first = apply_media_quality_gate(
        task,
        manifest=manifest,
        authorization=None,
        ocr_adapter=fixture_ocr,
        visual_adapter=fixture_visual,
    )
    repaired = resume_reliable_media_production(
        task,
        provider="local-fixture",
        mode="fixture",
        authorization=None,
        ocr_adapter=fixture_ocr,
        visual_adapter=fixture_visual,
        repair_decision_id=task.professional_artifacts[
            "media_repair_decision"
        ],
    )

    assert first["status"] == "LOCAL_REPAIR"
    assert repaired["status"] == "COMPLETED"
    assert task.status == "AWAITING_FEEDBACK"
    assert len(task.professional_artifacts["media_qa_reports"]) == 2
    assert len(task.professional_artifacts["media_shot_results"]) == 3
    assert task.professional_artifacts["media_shot_results"][0] == (
        shots[0].artifact_id
    )


def test_media_qa_artifacts_and_evidence_are_workspace_isolated(
    tmp_path,
    monkeypatch,
):
    from product_creative.runtime.media_qa import run_media_qa
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    def fixture_visual(**kwargs):
        return {
            "confidence": 0.99,
            "characters": list(kwargs["expected_characters"]),
            "scene": kwargs["expected_scene"],
            "product_visible": kwargs["expected_product_visible"],
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    workspace_a = tmp_path / "workspace-a"
    workspace_b = tmp_path / "workspace-b"
    workspace_a.mkdir()
    workspace_b.mkdir()
    with workspace_scope(workspace_a):
        plan_a, _shots_a, manifest_a, _plate_a = _technical_fixture(
            monkeypatch,
        )
        report_a = run_media_qa(
            "honeydew",
            plan_id=plan_a.artifact_id,
            manifest_id=manifest_a.artifact_id,
            ocr_adapter=None,
            visual_adapter=fixture_visual,
        )
    with workspace_scope(workspace_b):
        plan_b, _shots_b, manifest_b, _plate_b = _technical_fixture(
            monkeypatch,
            black_shot="shot-01",
        )
        report_b = run_media_qa(
            "honeydew",
            plan_id=plan_b.artifact_id,
            manifest_id=manifest_b.artifact_id,
            ocr_adapter=None,
            visual_adapter=fixture_visual,
        )
        assert report_b.overall_result == "REPAIR"
        assert load_professional_artifact(
            "honeydew",
            report_b.artifact_id,
        ).content_hash == report_b.content_hash
    with workspace_scope(workspace_a):
        restored_a = load_professional_artifact(
            "honeydew",
            report_a.artifact_id,
        )
        assert restored_a.overall_result == "PASS"
        assert restored_a.content_hash == report_a.content_hash
        assert restored_a.content_hash != report_b.content_hash


def test_doubao_media_qa_reuses_one_observation_for_ocr_and_visual(
    tmp_path,
    monkeypatch,
):
    from product_creative.capabilities.product.workspace_service import (
        create_product,
    )
    from product_creative.common import ensure_product
    import product_creative.runtime.media_vlm_qa as media_vlm_qa

    create_product("honeydew", "周十五蜂蜜露")
    product_root = ensure_product("honeydew")
    media_path = product_root / "artifacts" / "media_shots" / "shot-01.mp4"
    media_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_bytes(b"fixture-video")
    contact_sheet = (
        product_root
        / "artifacts"
        / "media_qa"
        / "contact-sheets"
        / "shot-01.jpg"
    )
    contact_sheet.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet.write_bytes(b"fixture-image")
    calls = []

    monkeypatch.setattr(
        media_vlm_qa,
        "_extract_contact_sheet",
        lambda *_args, **_kwargs: contact_sheet,
    )

    def observe(**kwargs):
        calls.append(kwargs)
        return {
            "observed_text": "温和陪伴，轻松出发",
            "subtitle_bbox": [0.12, 0.76, 0.76, 0.12],
            "subtitle_visible_ratio": 1.0,
            "confidence": 0.94,
            "characters": ["孕期女性"],
            "scene": "明亮居家空间",
            "product_visible": True,
            "continuity_notes": ["人物和空间稳定"],
            "risk_flags": [],
            "provider": "volcengine-ark-vlm",
            "model": "doubao-seed-2-1-pro-260628",
            "usage": {"input_tokens": 10},
        }

    monkeypatch.setattr(
        media_vlm_qa,
        "_request_doubao_observation",
        observe,
    )
    adapter = media_vlm_qa.DoubaoMediaQaAdapter(max_calls=5)

    ocr = adapter.ocr(
        product_id="honeydew",
        shot_id="shot-01",
        media_path=media_path,
        expected_text="温和陪伴，轻松出发",
        start_seconds=0.0,
        end_seconds=2.0,
    )
    visual = adapter.visual(
        product_id="honeydew",
        shot_id="shot-01",
        media_path=media_path,
        expected_characters=["孕期女性"],
        expected_scene="明亮居家空间",
        expected_product_visible=True,
    )

    assert len(calls) == 1
    assert adapter.call_count == 1
    assert ocr["observed_text"] == "温和陪伴，轻松出发"
    assert ocr["bounding_box"] == [0.12, 0.76, 0.76, 0.12]
    assert ocr["visible_duration_seconds"] == pytest.approx(2.0)
    assert visual["characters"] == ["孕期女性"]
    assert visual["scene"] == "明亮居家空间"
    assert visual["product_visible"] is True
    assert ocr["evidence_refs"] == visual["evidence_refs"]
    evidence_path = product_root / ocr["evidence_refs"][0].removeprefix(
        "media_qa:"
    )
    assert evidence_path.is_file()


def test_doubao_media_qa_enforces_the_real_call_limit(
    tmp_path,
    monkeypatch,
):
    from product_creative.capabilities.product.workspace_service import (
        create_product,
    )
    from product_creative.common import ensure_product
    import product_creative.runtime.media_vlm_qa as media_vlm_qa

    create_product("honeydew", "周十五蜂蜜露")
    product_root = ensure_product("honeydew")
    media_paths = []
    for shot_id in ("shot-01", "shot-02"):
        media_path = (
            product_root
            / "artifacts"
            / "media_shots"
            / f"{shot_id}.mp4"
        )
        media_path.parent.mkdir(parents=True, exist_ok=True)
        media_path.write_bytes(shot_id.encode("utf-8"))
        media_paths.append(media_path)
    contact_sheet = product_root / "artifacts" / "media_qa" / "sheet.jpg"
    contact_sheet.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet.write_bytes(b"fixture")
    calls = []
    monkeypatch.setattr(
        media_vlm_qa,
        "_extract_contact_sheet",
        lambda *_args, **_kwargs: contact_sheet,
    )
    monkeypatch.setattr(
        media_vlm_qa,
        "_request_doubao_observation",
        lambda **kwargs: calls.append(kwargs)
        or {
            "observed_text": "",
            "subtitle_bbox": [],
            "subtitle_visible_ratio": 0,
            "confidence": 0.9,
            "characters": [],
            "scene": "室内",
            "product_visible": False,
            "continuity_notes": [],
            "risk_flags": [],
        },
    )
    adapter = media_vlm_qa.DoubaoMediaQaAdapter(max_calls=1)

    adapter.visual(
        product_id="honeydew",
        shot_id="shot-01",
        media_path=media_paths[0],
        expected_characters=[],
        expected_scene="室内",
        expected_product_visible=False,
    )
    with pytest.raises(RuntimeError, match="call limit"):
        adapter.visual(
            product_id="honeydew",
            shot_id="shot-02",
            media_path=media_paths[1],
            expected_characters=[],
            expected_scene="室内",
            expected_product_visible=False,
        )

    assert len(calls) == 1
    assert adapter.call_count == 1


def test_doubao_media_qa_request_uses_responses_vlm_and_primary_key(
    tmp_path,
    monkeypatch,
):
    from product_creative.capabilities.material import visual_service
    import product_creative.runtime.media_vlm_qa as media_vlm_qa

    contact_sheet = tmp_path / "contact-sheet.jpg"
    contact_sheet.write_bytes(b"fixture-image")
    captured = {}
    monkeypatch.setenv("DOUBAO_API_KEY", "primary-doubao-key")
    monkeypatch.setenv("ARK_API_KEY", "fallback-key")

    def post_json(endpoint, body, api_key, timeout_seconds=120):
        captured.update(
            {
                "endpoint": endpoint,
                "body": body,
                "api_key": api_key,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                '{"observed_text":"字幕","subtitle_bbox":'
                                '[0.1,0.7,0.8,0.1],"subtitle_visible_ratio":1,'
                                '"confidence":0.91,"characters":["主角"],'
                                '"scene":"室内","product_visible":true,'
                                '"continuity_notes":[],"risk_flags":[]}'
                            ),
                        }
                    ]
                }
            ],
            "usage": {"input_tokens": 12},
        }

    monkeypatch.setattr(visual_service, "_post_json", post_json)

    result = media_vlm_qa._request_doubao_observation(
        provider_name="volcengine-ark-vlm",
        contact_sheet=contact_sheet,
        prompt="只输出 JSON",
    )

    assert captured["endpoint"].endswith("/api/v3/responses")
    assert captured["api_key"] == "primary-doubao-key"
    assert captured["body"]["model"] == "doubao-seed-2-1-pro-260628"
    image_input = captured["body"]["input"][0]["content"][0]
    assert image_input["type"] == "input_image"
    assert image_input["image_url"].startswith("data:image/jpeg;base64,")
    assert result["observed_text"] == "字幕"
    assert result["provider"] == "volcengine-ark-vlm"
    assert result["model"] == "doubao-seed-2-1-pro-260628"


def test_live_media_production_autowires_bounded_doubao_qa(
    monkeypatch,
):
    import product_creative.runtime.media_production as media_production
    import product_creative.runtime.media_vlm_qa as media_vlm_qa

    created = []
    expected_ocr = lambda **_kwargs: {}
    expected_visual = lambda **_kwargs: {}
    monkeypatch.setenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", "1")
    monkeypatch.setattr(
        media_vlm_qa,
        "create_doubao_media_qa_adapters",
        lambda *, max_calls: created.append(max_calls)
        or (expected_ocr, expected_visual),
    )

    ocr, visual = media_production._resolve_media_qa_adapters(
        mode="live",
        shot_count=8,
        ocr_adapter=None,
        visual_adapter=None,
    )

    assert created == [5]
    assert ocr is expected_ocr
    assert visual is expected_visual
