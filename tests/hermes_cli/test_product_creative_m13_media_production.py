from __future__ import annotations

import base64
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENT = ROOT / ".hermes" / "plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))


NOW = "2026-07-16T00:00:00+00:00"
HEX_A = "a" * 64
HEX_B = "b" * 64


@pytest.fixture(autouse=True)
def _isolated_product_creative_workspace(tmp_path):
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        yield


def _base(artifact_id: str, schema_name: str) -> dict:
    return {
        "schema_name": schema_name,
        "artifact_id": artifact_id,
        "task_id": "task-m13",
        "product_id": "honeydew",
        "created_at": NOW,
        "source_refs": ["production-bible-task-m13"],
        "status": "READY",
    }


def _shot_plan() -> dict:
    return {
        "shot_id": "shot-01",
        "ordinal": 1,
        "duration_seconds": 2.0,
        "execution_mode": "video_background",
        "product_plate_required": False,
        "prompt": "清晨玄关背景，只生成人物与场景，不生成产品包装、品牌文字或字幕。",
        "caption": "",
        "input_materials": [],
        "max_attempts": 2,
        "idempotency_key": "task-m13:shot-01:provider:video",
    }


def test_m13_media_artifacts_are_registered_and_tamper_evident():
    from product_creative.contracts.creative_artifacts import (
        MediaCompositeManifestArtifact,
        MediaDependencyReportArtifact,
        MediaExecutionPlanArtifact,
        MediaShotResultArtifact,
        ProductPlateArtifact,
        professional_artifact_model,
    )

    dependency = MediaDependencyReportArtifact.model_validate(
        {
            **_base(
                "media-dependencies-task-m13",
                "product_creative.media_dependency_report.v1",
            ),
            "overall_status": "READY",
            "checks": [
                {
                    "name": "ffmpeg",
                    "status": "READY",
                    "detail": "ffmpeg is available",
                    "metadata": {"version": "fixture"},
                }
            ],
            "blockers": [],
            "warnings": [],
        }
    )
    plate = ProductPlateArtifact.model_validate(
        {
            **_base("product-plate-task-m13", "product_creative.product_plate.v1"),
            "source_material_id": "material-main",
            "source_content_hash": HEX_A,
            "plate_relative_path": "artifacts/product_plates/product-plate-task-m13.png",
            "plate_content_hash": HEX_B,
            "mask_mode": "source_alpha",
            "source_size": [800, 800],
            "plate_size": [800, 800],
            "allowed_transforms": ["uniform_scale", "translate", "alpha_composite"],
            "forbidden_transforms": ["redraw", "change_packaging_text"],
        }
    )
    plan = MediaExecutionPlanArtifact.model_validate(
        {
            **_base(
                "media-plan-task-m13",
                "product_creative.media_execution_plan.v1",
            ),
            "production_bible_id": "production-bible-task-m13",
            "production_bible_hash": HEX_A,
            "dependency_report_id": dependency.artifact_id,
            "product_plate_id": plate.artifact_id,
            "aspect_ratio": "9:16",
            "canvas": [1080, 1920],
            "fps": 24,
            "shots": [_shot_plan(), {**_shot_plan(), "shot_id": "shot-02", "ordinal": 2}],
            "output_requirements": {"codec": "h264", "subtitle_mode": "deterministic_ass"},
            "call_budget": {"image": 5, "video": 5},
        }
    )
    shot_result = MediaShotResultArtifact.model_validate(
        {
            **_base(
                "media-shot-task-m13-shot-01-attempt-1",
                "product_creative.media_shot_result.v1",
            ),
            "plan_id": plan.artifact_id,
            "shot_id": "shot-01",
            "attempt": 1,
            "execution_status": "COMPLETED",
            "provider": "fixture-video",
            "external_call_performed": False,
            "provider_task_id": "",
            "input_hashes": {"background": HEX_A},
            "output_relative_path": "artifacts/media_shots/shot-01.mp4",
            "output_content_hash": HEX_B,
            "duration_seconds": 2.0,
            "error_code": "",
            "error_detail": "",
        }
    )
    manifest = MediaCompositeManifestArtifact.model_validate(
        {
            **_base(
                "media-composite-task-m13",
                "product_creative.media_composite_manifest.v1",
            ),
            "plan_id": plan.artifact_id,
            "shot_result_ids": [
                shot_result.artifact_id,
                "media-shot-task-m13-shot-02-attempt-1",
            ],
            "output_relative_path": "artifacts/generated_videos/final.mp4",
            "output_content_hash": HEX_A,
            "duration_seconds": 4.0,
            "codec": "h264",
            "audio_codec": "aac",
            "subtitle_mode": "deterministic_ass",
            "command_summary": ["normalize shot-01", "concat 2 shots"],
        }
    )

    for artifact in (dependency, plate, plan, shot_result, manifest):
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


def test_failed_media_shot_cannot_claim_a_completed_output():
    from product_creative.contracts.creative_artifacts import MediaShotResultArtifact

    with pytest.raises(
        ValidationError,
        match="failed media shot cannot claim output",
    ):
        MediaShotResultArtifact.model_validate(
            {
                **_base(
                    "media-shot-task-m13-shot-01-attempt-1",
                    "product_creative.media_shot_result.v1",
                ),
                "status": "BLOCKED",
                "plan_id": "media-plan-task-m13",
                "shot_id": "shot-01",
                "attempt": 1,
                "execution_status": "FAILED_RETRYABLE",
                "provider": "fixture-video",
                "external_call_performed": False,
                "provider_task_id": "",
                "input_hashes": {"background": HEX_A},
                "output_relative_path": "artifacts/media_shots/partial.mp4",
                "output_content_hash": HEX_B,
                "duration_seconds": 0,
                "error_code": "fixture_failure",
                "error_detail": "injected failure",
            }
        )


def test_completed_media_shot_requires_output_hash_and_path():
    from product_creative.contracts.creative_artifacts import MediaShotResultArtifact

    with pytest.raises(
        ValidationError,
        match="completed media shot requires output",
    ):
        MediaShotResultArtifact.model_validate(
            {
                **_base(
                    "media-shot-task-m13-shot-01-attempt-1",
                    "product_creative.media_shot_result.v1",
                ),
                "plan_id": "media-plan-task-m13",
                "shot_id": "shot-01",
                "attempt": 1,
                "execution_status": "COMPLETED",
                "provider": "fixture-video",
                "external_call_performed": False,
                "provider_task_id": "",
                "input_hashes": {"background": HEX_A},
                "output_relative_path": "",
                "output_content_hash": "",
                "duration_seconds": 2,
                "error_code": "",
                "error_detail": "",
            }
        )


def test_media_execution_plan_requires_unique_ordered_shots():
    from product_creative.contracts.creative_artifacts import MediaExecutionPlanArtifact

    duplicate = _shot_plan()
    with pytest.raises(
        ValidationError,
        match="unique and ordered",
    ):
        MediaExecutionPlanArtifact.model_validate(
            {
                **_base(
                    "media-plan-task-m13",
                    "product_creative.media_execution_plan.v1",
                ),
                "production_bible_id": "production-bible-task-m13",
                "production_bible_hash": HEX_A,
                "dependency_report_id": "media-dependencies-task-m13",
                "product_plate_id": "",
                "aspect_ratio": "9:16",
                "canvas": [1080, 1920],
                "fps": 24,
                "shots": [duplicate, duplicate],
                "output_requirements": {},
                "call_budget": {"image": 5, "video": 5},
            }
        )


def test_dependency_report_cannot_be_ready_with_blockers():
    from product_creative.contracts.creative_artifacts import (
        MediaDependencyReportArtifact,
    )

    with pytest.raises(
        ValidationError,
        match="READY dependency report cannot contain blockers",
    ):
        MediaDependencyReportArtifact.model_validate(
            {
                **_base(
                    "media-dependencies-task-m13",
                    "product_creative.media_dependency_report.v1",
                ),
                "overall_status": "READY",
                "checks": [
                    {
                        "name": "ffmpeg",
                        "status": "BLOCKED",
                        "detail": "missing",
                        "metadata": {},
                    }
                ],
                "blockers": ["ffmpeg is missing"],
                "warnings": [],
            }
        )


def _setup_dependency_product(tmp_path):
    from product_creative.capabilities.material.asset_service import (
        register_material_asset,
    )
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.contracts.creative_artifacts import ProductionBibleArtifact
    from product_creative.runtime.professional_artifacts import (
        save_professional_artifact,
    )

    create_product("honeydew", "周十五蜂蜜露")
    image_path = tmp_path / "current-main.png"
    image_path.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    )
    material = register_material_asset(
        "honeydew",
        str(image_path),
        "current_main_image",
        "已确认当前包装主图",
        ["product_reference", "video_first_frame"],
    )
    bible = ProductionBibleArtifact(
        artifact_id="production-bible-task-m13",
        task_id="task-m13",
        product_id="honeydew",
        created_at=NOW,
        source_refs=[f"material:{material['material_id']}"],
        status="READY",
        specification={
            "aspect_ratio": "9:16",
            "canvas": [270, 480],
            "fps": 12,
            "subtitle_rendering": "deterministic_post_composite",
        },
        shots=[
            {
                "shot_id": "shot-01",
                "duration_seconds": 2,
                "composition": "竖屏中景",
                "action": "主角停在门口",
                "characters": ["小周"],
                "scene": "清晨玄关",
                "input_materials": [],
                "caption": "",
                "narrative_function": "视觉钩子",
            },
            {
                "shot_id": "shot-02",
                "duration_seconds": 2,
                "composition": "产品近景",
                "action": "产品进入画面",
                "characters": [],
                "scene": "随身包",
                "input_materials": [material["material_id"]],
                "caption": "准备好，再出发",
                "narrative_function": "产品转折与结尾收束",
            },
        ],
        asset_roles={
            material["material_id"]: "immutable_product_plate",
            "generated-background": "background_only",
        },
        packaging_strategy="exact-main-composite",
        continuity_rules=["包装与包装文字不得改变"],
        provider_mapping={
            "background": "image",
            "motion": "video",
            "final": "compositor",
        },
        retry_policy={"max_retries_per_shot": 1},
        delivery_requirements=["可播放 MP4"],
    )
    save_professional_artifact(bible)
    return material, bible


def test_media_dependency_inspection_records_ready_capabilities(
    tmp_path,
    monkeypatch,
):
    material, bible = _setup_dependency_product(tmp_path)
    import product_creative.runtime.media_dependencies as dependencies

    monkeypatch.delenv("PRODUCT_CREATIVE_FFMPEG_PATH", raising=False)
    monkeypatch.delenv("PRODUCT_CREATIVE_FFPROBE_PATH", raising=False)
    monkeypatch.setattr(
        dependencies.shutil,
        "which",
        lambda name: f"C:\\tools\\{name}.exe",
    )
    monkeypatch.setattr(dependencies, "_common_media_tool_candidates", lambda _name: ())
    def tool_result(command, **_kwargs):
        if command[0].endswith("ffprobe.exe"):
            return SimpleNamespace(
                returncode=0,
                stdout="ffprobe version fixture\n",
                stderr="",
            )
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "ffmpeg version fixture\n"
                " V..... libx264 H.264 encoder\n"
                " A..... aac AAC encoder\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(dependencies.subprocess, "run", tool_result)
    monkeypatch.setattr(
        dependencies,
        "_find_chinese_font",
        lambda: Path(r"C:\Windows\Fonts\msyh.ttc"),
    )
    monkeypatch.setattr(
        dependencies.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=1_000_000_000),
    )

    report = dependencies.inspect_media_dependencies(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
        production_bible_id=bible.artifact_id,
    )

    assert report.overall_status == "READY"
    assert report.blockers == []
    assert {
        "ffmpeg",
        "ffprobe",
        "video_codecs",
        "pillow",
        "chinese_font",
        "disk_space",
        "material",
        "production_bible",
        "provider_capability",
    }.issubset({check.name for check in report.checks})


def test_media_dependency_inspection_rejects_ffmpeg_binary_named_ffprobe(
    tmp_path,
    monkeypatch,
):
    material, bible = _setup_dependency_product(tmp_path)
    import product_creative.runtime.media_dependencies as dependencies

    monkeypatch.delenv("PRODUCT_CREATIVE_FFMPEG_PATH", raising=False)
    monkeypatch.delenv("PRODUCT_CREATIVE_FFPROBE_PATH", raising=False)
    monkeypatch.setattr(
        dependencies.shutil,
        "which",
        lambda name: f"C:\\tools\\{name}.exe",
    )
    monkeypatch.setattr(dependencies, "_common_media_tool_candidates", lambda _name: ())

    def wrong_probe(command, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "ffmpeg version fixture\n"
                " V..... libx264 H.264 encoder\n"
                " A..... aac AAC encoder\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(dependencies.subprocess, "run", wrong_probe)
    monkeypatch.setattr(
        dependencies,
        "_find_chinese_font",
        lambda: Path(r"C:\Windows\Fonts\msyh.ttc"),
    )
    monkeypatch.setattr(
        dependencies.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=1_000_000_000),
    )

    report = dependencies.inspect_media_dependencies(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
        production_bible_id=bible.artifact_id,
    )

    assert report.overall_status == "BLOCKED"
    codecs = next(check for check in report.checks if check.name == "video_codecs")
    assert codecs.status == "BLOCKED"
    assert codecs.metadata["ffprobe_usable"] is False


def test_resolve_media_tool_skips_misidentified_path_candidate(
    tmp_path,
    monkeypatch,
):
    import product_creative.runtime.media_dependencies as dependencies

    path_dir = tmp_path / "path"
    packaged_dir = tmp_path / "packaged"
    path_dir.mkdir()
    packaged_dir.mkdir()
    wrong_probe = path_dir / "ffprobe.exe"
    valid_probe = packaged_dir / "ffprobe.exe"
    wrong_probe.write_bytes(b"fixture")
    valid_probe.write_bytes(b"fixture")

    monkeypatch.delenv("PRODUCT_CREATIVE_FFPROBE_PATH", raising=False)
    monkeypatch.setattr(
        dependencies.shutil,
        "which",
        lambda name: str(wrong_probe) if name == "ffprobe" else None,
    )
    monkeypatch.setattr(
        dependencies,
        "_common_media_tool_candidates",
        lambda name: (valid_probe,) if name == "ffprobe" else (),
    )

    def identify(command, **_kwargs):
        executable = Path(command[0])
        first_line = (
            "ffprobe version fixture\n"
            if executable == valid_probe
            else "ffmpeg version wrong-shim\n"
        )
        return SimpleNamespace(returncode=0, stdout=first_line, stderr="")

    monkeypatch.setattr(dependencies.subprocess, "run", identify)

    assert dependencies.resolve_media_tool("ffprobe") == str(valid_probe)


def test_media_dependency_inspection_blocks_before_subprocess_when_ffmpeg_missing(
    tmp_path,
    monkeypatch,
):
    material, bible = _setup_dependency_product(tmp_path)
    import product_creative.runtime.media_dependencies as dependencies

    monkeypatch.delenv("PRODUCT_CREATIVE_FFMPEG_PATH", raising=False)
    monkeypatch.delenv("PRODUCT_CREATIVE_FFPROBE_PATH", raising=False)
    monkeypatch.setattr(
        dependencies.shutil,
        "which",
        lambda name: None if name == "ffmpeg" else f"C:\\tools\\{name}.exe",
    )
    monkeypatch.setattr(dependencies, "_common_media_tool_candidates", lambda _name: ())
    subprocess_commands = []

    def identity_only(command, **_kwargs):
        subprocess_commands.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout="ffprobe version fixture\n",
            stderr="",
        )

    monkeypatch.setattr(dependencies.subprocess, "run", identity_only)
    monkeypatch.setattr(
        dependencies,
        "_find_chinese_font",
        lambda: Path(r"C:\Windows\Fonts\msyh.ttc"),
    )
    monkeypatch.setattr(
        dependencies.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=1_000_000_000),
    )

    report = dependencies.inspect_media_dependencies(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
        production_bible_id=bible.artifact_id,
    )

    assert report.overall_status == "BLOCKED"
    assert any("ffmpeg is not available" in item for item in report.blockers)
    assert not any("-encoders" in command for command in subprocess_commands)


def _register_plate_material(tmp_path, *, mode: str):
    from PIL import Image
    from product_creative.capabilities.material.asset_service import (
        register_material_asset,
    )
    from product_creative.capabilities.product.workspace_service import create_product

    create_product("honeydew", "周十五蜂蜜露")
    source = tmp_path / f"{mode}.png"
    if mode == "source_alpha":
        image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for x in range(2, 6):
            for y in range(2, 6):
                image.putpixel((x, y), (220, 20, 90, 255))
    elif mode == "edge_connected_background":
        image = Image.new("RGB", (8, 8), (250, 250, 250))
        for x in range(2, 6):
            for y in range(2, 6):
                image.putpixel((x, y), (220, 20, 90))
    else:
        image = Image.new("RGB", (8, 8), (25, 50, 75))
        edge_colors = [
            (20, 40, 60),
            (220, 210, 30),
            (120, 20, 180),
            (20, 180, 140),
        ]
        for x in range(8):
            image.putpixel((x, 0), edge_colors[x % 4])
            image.putpixel((x, 7), edge_colors[(x + 1) % 4])
        for y in range(8):
            image.putpixel((0, y), edge_colors[(y + 2) % 4])
            image.putpixel((7, y), edge_colors[(y + 3) % 4])
        for x in range(2, 6):
            for y in range(2, 6):
                image.putpixel((x, y), (220, 20, 90))
    image.save(source)
    material = register_material_asset(
        "honeydew",
        str(source),
        "current_main_image",
        f"M13 {mode} fixture",
        ["product_reference", "video_first_frame"],
    )
    return source, material


@pytest.mark.parametrize(
    ("source_mode", "expected_mask"),
    [
        ("source_alpha", "source_alpha"),
        ("edge_connected_background", "edge_connected_background"),
    ],
)
def test_product_plate_preserves_foreground_pixels_and_selects_safe_mask(
    tmp_path,
    source_mode,
    expected_mask,
):
    from PIL import Image
    from product_creative.runtime.product_plate import ensure_product_plate
    from product_creative.common import ensure_product

    source, material = _register_plate_material(tmp_path, mode=source_mode)
    source_before = source.read_bytes()

    plate = ensure_product_plate(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
    )

    base = ensure_product("honeydew")
    output = base / plate.plate_relative_path
    rendered = Image.open(output).convert("RGBA")
    assert plate.mask_mode == expected_mask
    assert rendered.getpixel((3, 3))[:3] == (220, 20, 90)
    assert rendered.getpixel((0, 0))[3] == 0
    assert source.read_bytes() == source_before


def test_product_plate_falls_back_to_full_rect_for_ambiguous_edges(tmp_path):
    from PIL import Image
    from product_creative.common import ensure_product
    from product_creative.runtime.product_plate import ensure_product_plate

    _source, material = _register_plate_material(tmp_path, mode="ambiguous")
    plate = ensure_product_plate(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
    )

    rendered = Image.open(
        ensure_product("honeydew") / plate.plate_relative_path
    ).convert("RGBA")
    assert plate.mask_mode == "full_rect"
    pixels = (
        rendered.get_flattened_data()
        if hasattr(rendered, "get_flattened_data")
        else rendered.getdata()
    )
    assert all(pixel[3] == 255 for pixel in pixels)
    assert plate.warnings


def test_product_material_resolution_rejects_cross_workspace_path(tmp_path):
    from product_creative.runtime.product_plate import resolve_product_material

    _source, _material = _register_plate_material(
        tmp_path,
        mode="source_alpha",
    )
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not-an-image")

    with pytest.raises(ValueError, match="inside the product workspace"):
        resolve_product_material("honeydew", str(outside))


def _ready_dependency_report():
    from product_creative.contracts.creative_artifacts import (
        MediaDependencyReportArtifact,
    )

    return MediaDependencyReportArtifact(
        **_base(
            "media-dependencies-task-m13",
            "product_creative.media_dependency_report.v1",
        ),
        overall_status="READY",
        checks=[
            {
                "name": "offline-fixture",
                "status": "READY",
                "detail": "fixture media production is available",
                "metadata": {},
            }
        ],
        blockers=[],
        warnings=[],
    )


def test_media_plan_compiles_shot_graph_without_provider_text_or_product_redraw(
    tmp_path,
):
    from product_creative.runtime.media_plan import compile_media_execution_plan
    from product_creative.runtime.product_plate import ensure_product_plate

    material, bible = _setup_dependency_product(tmp_path)
    plate = ensure_product_plate(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
    )
    task = SimpleNamespace(
        task_id="task-m13",
        product_id="honeydew",
        request=SimpleNamespace(preserve_exact_packaging=True),
        professional_artifacts={"production_bible": bible.artifact_id},
    )

    plan = compile_media_execution_plan(
        task,
        dependency_report=_ready_dependency_report(),
        product_plate=plate,
        provider="volcengine-ark-video",
    )

    assert [shot.ordinal for shot in plan.shots] == [1, 2]
    assert sum(shot.duration_seconds for shot in plan.shots) == pytest.approx(4)
    assert [shot.product_plate_required for shot in plan.shots] == [False, True]
    assert plan.shots[1].caption == "准备好，再出发"
    assert "准备好，再出发" not in plan.shots[1].prompt
    assert "不得生成产品包装" in plan.shots[1].prompt
    assert "不得生成字幕" in plan.shots[1].prompt
    assert all(shot.execution_mode == "video_background" for shot in plan.shots)
    assert [shot.motion_required for shot in plan.shots] == [True, True]
    assert [shot.motion_description for shot in plan.shots] == [
        "主角停在门口",
        "产品进入画面",
    ]
    assert [shot.product_plate_motion for shot in plan.shots] == [
        "none",
        "subtle_entrance",
    ]
    assert all(
        shot.maximum_freeze_ratio == pytest.approx(0.65)
        for shot in plan.shots
    )
    assert all(shot.max_attempts == 2 for shot in plan.shots)
    assert task.professional_artifacts["media_execution_plan"] == plan.artifact_id


def test_image_media_plan_declares_first_shot_character_reference_chain(tmp_path):
    from product_creative.runtime.media_plan import compile_media_execution_plan
    from product_creative.runtime.product_plate import ensure_product_plate

    material, bible = _setup_dependency_product(tmp_path)
    plate = ensure_product_plate(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
    )
    task = SimpleNamespace(
        task_id="task-m13",
        product_id="honeydew",
        request=SimpleNamespace(preserve_exact_packaging=True),
        professional_artifacts={"production_bible": bible.artifact_id},
    )

    plan = compile_media_execution_plan(
        task,
        dependency_report=_ready_dependency_report(),
        product_plate=plate,
        provider="volcengine-ark-image",
    )

    assert plan.output_requirements["continuity_strategy"] == (
        "first-shot-reference-chain"
    )
    assert plan.output_requirements["continuity_anchor_shot_id"] == "shot-01"
    assert all(
        "同一主角身份" in shot.prompt and "服装与随身配饰" in shot.prompt
        for shot in plan.shots
    )
    assert all(shot.execution_mode == "image_background" for shot in plan.shots)


def test_offline_exact_main_preparation_uses_reliable_image_provider(
    monkeypatch,
):
    import product_creative.runtime.creative_tasks as creative_tasks
    import product_creative.runtime.media_production as media_production

    calls = []
    step = SimpleNamespace(
        stage="GENERATING",
        action="compose_exact_main_video",
        status="PENDING",
        guard="task_authorization",
    )
    task = SimpleNamespace(
        task_id="task-m13-exact-image-plan",
        product_id="honeydew",
        provider="volcengine-ark-video",
        authorization_id="",
        readiness=SimpleNamespace(ready=True),
        request=SimpleNamespace(
            deliverables=["video"],
            preserve_exact_packaging=True,
        ),
        plan=SimpleNamespace(actions=[step], stages=["GENERATING"]),
        professional_artifacts={"production_bible": "bible-m13"},
        completed_stages=[],
        result_descriptors=[],
        status="READY",
        current_stage="GENERATING",
        blocked_reason="",
        updated_at=NOW,
    )

    monkeypatch.setattr(
        creative_tasks,
        "professional_provider_gate",
        lambda _task: (True, ""),
    )
    monkeypatch.setattr(
        creative_tasks,
        "_reliable_media_provider",
        lambda _task: "volcengine-ark-image",
    )

    def prepare(received_task, *, provider, mode):
        calls.append((received_task.task_id, provider, mode))
        received_task.professional_artifacts["media_execution_plan"] = "plan-image"
        return {"status": "READY"}

    monkeypatch.setattr(
        media_production,
        "prepare_reliable_media_production",
        prepare,
    )

    creative_tasks.advance_offline_preparation(task)

    assert calls == [
        ("task-m13-exact-image-plan", "volcengine-ark-image", "live")
    ]
    assert task.status == "BLOCKED_AUTHORIZATION"


def test_exact_main_video_selects_dynamic_video_provider_by_default():
    import product_creative.runtime.creative_tasks as creative_tasks

    task = SimpleNamespace(
        provider="volcengine-ark-image",
        product_id="honeydew",
        request=SimpleNamespace(
            deliverables=["video"],
            preserve_exact_packaging=True,
        ),
        professional_artifacts={},
    )

    assert creative_tasks._reliable_media_provider(task) == (
        "volcengine-ark-video"
    )


def test_unapproved_media_plan_is_recompiled_when_provider_route_changes(
    monkeypatch,
):
    import product_creative.runtime.creative_tasks as creative_tasks

    task = SimpleNamespace(
        task_id="task-m13-route-change",
        product_id="honeydew",
        provider="volcengine-ark-video",
        authorization_id="",
        request=SimpleNamespace(preserve_exact_packaging=True),
        status="BLOCKED_AUTHORIZATION",
        current_stage="GENERATING",
        blocked_reason="waiting for authorization",
        professional_artifacts={
            "media_execution_plan": "media-plan-video",
            "media_shot_results": [],
        },
        result_descriptors=[],
    )
    plan = SimpleNamespace(
        artifact_id="media-plan-video",
        output_requirements={"provider": "volcengine-ark-video"},
    )
    monkeypatch.setattr(
        creative_tasks,
        "load_professional_artifact",
        lambda _product_id, _artifact_id: plan,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_reliable_media_provider",
        lambda _task: "volcengine-ark-image",
    )

    changed = creative_tasks._reconcile_unsubmitted_media_plan_provider(task)

    assert changed is True
    assert "media_execution_plan" not in task.professional_artifacts
    assert task.status == "READY"
    assert task.result_descriptors[-1]["from_provider"] == "volcengine-ark-video"
    assert task.result_descriptors[-1]["to_provider"] == "volcengine-ark-image"


def test_media_plan_idempotency_keys_are_stable_and_provider_specific(tmp_path):
    from product_creative.runtime.media_plan import compile_media_execution_plan
    from product_creative.runtime.product_plate import ensure_product_plate

    material, bible = _setup_dependency_product(tmp_path)
    plate = ensure_product_plate(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
    )

    def task():
        return SimpleNamespace(
            task_id="task-m13",
            product_id="honeydew",
            request=SimpleNamespace(preserve_exact_packaging=True),
            professional_artifacts={"production_bible": bible.artifact_id},
        )

    first = compile_media_execution_plan(
        task(),
        dependency_report=_ready_dependency_report(),
        product_plate=plate,
        provider="volcengine-ark-video",
    )
    second = compile_media_execution_plan(
        task(),
        dependency_report=_ready_dependency_report(),
        product_plate=plate,
        provider="volcengine-ark-video",
    )
    fixture = compile_media_execution_plan(
        task(),
        dependency_report=_ready_dependency_report(),
        product_plate=plate,
        provider="local-fixture",
    )

    assert [shot.idempotency_key for shot in first.shots] == [
        shot.idempotency_key for shot in second.shots
    ]
    assert first.shots[0].idempotency_key != fixture.shots[0].idempotency_key
    assert first.artifact_id != fixture.artifact_id
    assert all(shot.execution_mode == "local_motion" for shot in fixture.shots)


def test_media_plan_blocks_exact_packaging_without_product_plate(tmp_path):
    from product_creative.runtime.media_plan import compile_media_execution_plan

    _material, bible = _setup_dependency_product(tmp_path)
    task = SimpleNamespace(
        task_id="task-m13",
        product_id="honeydew",
        request=SimpleNamespace(preserve_exact_packaging=True),
        professional_artifacts={"production_bible": bible.artifact_id},
    )

    with pytest.raises(ValueError, match="product plate"):
        compile_media_execution_plan(
            task,
            dependency_report=_ready_dependency_report(),
            product_plate=None,
            provider="local-fixture",
        )


def test_local_motion_repair_requires_task_authorization_but_not_paid_video(
    tmp_path,
):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    from product_creative.runtime.media_production import _repair_authorized

    plan = _fixture_media_plan(tmp_path, provider="local-fixture")
    authorization = SimpleNamespace(
        status="ACTIVE",
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        allow_paid_image=False,
        allow_paid_video=False,
        used_image_calls=0,
        used_video_calls=0,
        max_image_calls=0,
        max_video_calls=0,
    )

    assert _repair_authorized(
        authorization,
        plan=plan,
        failed_shot_ids=["shot-01"],
    ) is True
    assert _repair_authorized(
        None,
        plan=plan,
        failed_shot_ids=["shot-01"],
    ) is False


def _fixture_media_plan(tmp_path, *, provider="local-fixture"):
    from product_creative.runtime.media_plan import compile_media_execution_plan
    from product_creative.runtime.product_plate import ensure_product_plate

    material, bible = _setup_dependency_product(tmp_path)
    plate = ensure_product_plate(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
    )
    task = SimpleNamespace(
        task_id="task-m13",
        product_id="honeydew",
        request=SimpleNamespace(preserve_exact_packaging=True),
        professional_artifacts={"production_bible": bible.artifact_id},
    )
    plan = compile_media_execution_plan(
        task,
        dependency_report=_ready_dependency_report(),
        product_plate=plate,
        provider=provider,
    )
    return plan


def test_media_shot_payload_contains_only_scene_generation_requirements(tmp_path):
    from product_creative.provider_gateway import DefaultGenerationProviderGateway

    plan = _fixture_media_plan(
        tmp_path,
        provider="volcengine-ark-video",
    )
    gateway = DefaultGenerationProviderGateway()
    result = gateway.prepare_media_shot(
        "honeydew",
        plan.artifact_id,
        "shot-02",
        "volcengine-ark-video",
        "video",
    )
    payload = result["payload"]
    request = payload["request"]

    assert payload["source_media_plan_id"] == plan.artifact_id
    assert payload["source_shot_id"] == "shot-02"
    assert "准备好，再出发" not in request["prompt"]
    assert "不得生成产品包装" in request["prompt"]
    assert "不得生成字幕" in request["prompt"]
    assert "前2秒内完成" in request["prompt"]
    assert request["text_to_render"] == []
    assert request["reference_assets"] == []
    assert request["planned_duration_seconds"] == pytest.approx(2)
    assert request["provider_duration_seconds"] == 4
    assert request["trim_to_seconds"] == pytest.approx(2)
    assert request["storyboard"][0]["duration"] == "4s"
    assert request["provider_request_draft"]["body"]["duration"] == 4
    assert request["prompt_adapter"]["duration_seconds"] == 4
    assert "product_plate" not in str(request).lower()
    assert payload["external_call_performed"] is False
    assert len(result["payload_id"]) <= 64
    assert Path(result["files"]["json"]).is_file()


def test_later_image_shot_uses_first_generated_scene_as_continuity_reference(
    tmp_path,
):
    from PIL import Image
    from product_creative.common import ensure_product
    from product_creative.contracts.creative_artifacts import MediaShotResultArtifact
    from product_creative.provider_gateway import DefaultGenerationProviderGateway
    from product_creative.runtime.professional_artifacts import (
        save_professional_artifact,
    )

    plan = _fixture_media_plan(
        tmp_path,
        provider="volcengine-ark-image",
    )
    product_root = ensure_product("honeydew")
    source = product_root / "artifacts" / "media_shot_sources" / "anchor.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 48), (12, 34, 56)).save(source)
    content_hash = __import__("hashlib").sha256(source.read_bytes()).hexdigest()
    first = MediaShotResultArtifact(
        **{
            **_base(
                "media-shot-task-m13-shot-01-attempt-1",
                "product_creative.media_shot_result.v1",
            ),
            "source_refs": [plan.artifact_id],
        },
        plan_id=plan.artifact_id,
        shot_id="shot-01",
        attempt=1,
        execution_status="COMPLETED",
        provider="volcengine-ark-image",
        external_call_performed=True,
        input_hashes={"scene": content_hash},
        source_relative_path=str(source.relative_to(product_root)),
        output_relative_path=str(source.relative_to(product_root)),
        output_content_hash=content_hash,
        duration_seconds=2,
    )
    save_professional_artifact(first)

    gateway = DefaultGenerationProviderGateway()
    prepared = gateway.prepare_media_shot(
        "honeydew",
        plan.artifact_id,
        "shot-02",
        "volcengine-ark-image",
        "image",
    )
    request = prepared["payload"]["request"]

    assert request["image"].startswith("data:image/png;base64,")
    assert request["continuity_reference"]["shot_id"] == "shot-01"
    assert request["continuity_reference"]["content_hash"] == content_hash
    assert request["reference_assets"] == [
        {
            "role": "character_continuity_reference",
            "shot_id": "shot-01",
            "content_hash": content_hash,
        }
    ]
    assert "product_plate" not in str(request).lower()


def test_live_image_body_forwards_continuity_reference_without_batch_mode():
    from product_creative.provider_generation import _live_image_body

    image = "data:image/png;base64,ZmFrZQ=="
    body = _live_image_body(
        {"request": {"prompt": "same protagonist", "image": image}},
        {
            "model": "doubao-seedream-test",
            "request_defaults": {
                "response_format": "url",
                "size": "2K",
                "sequential_image_generation": "disabled",
            },
        },
    )

    assert body["image"] == image
    assert body["sequential_image_generation"] == "disabled"


def test_local_fixture_media_shot_is_real_file_and_idempotent(tmp_path):
    from PIL import Image
    from product_creative.common import ensure_product
    from product_creative.provider_gateway import DefaultGenerationProviderGateway

    plan = _fixture_media_plan(tmp_path)
    gateway = DefaultGenerationProviderGateway()
    prepared = gateway.prepare_media_shot(
        "honeydew",
        plan.artifact_id,
        "shot-01",
        "local-fixture",
        "image",
    )
    first = gateway.submit_media_shot(
        "honeydew",
        prepared["payload_id"],
        "local-fixture",
        "fixture",
    )
    second = gateway.submit_media_shot(
        "honeydew",
        prepared["payload_id"],
        "local-fixture",
        "fixture",
    )

    output = ensure_product("honeydew") / first["source_media"]
    with Image.open(output) as image:
        assert image.size == tuple(plan.canvas)
    assert output.is_file()
    assert first["external_call_performed"] is False
    assert first["content_hash"] == second["content_hash"]
    assert first["source_media"] == second["source_media"]


def test_m13_task_authorization_defaults_to_five_paid_media_calls(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.runtime.authorization import (
        create_task_authorization_request,
    )

    create_product("honeydew", "周十五蜂蜜露")
    task = SimpleNamespace(
        task_id="task-m13",
        product_id="honeydew",
        request=SimpleNamespace(
            raw_message="搜索今天的灵感并生成图片和视频",
            requires_fresh_inspiration=True,
            deliverables=["image", "video"],
        ),
    )

    request = create_task_authorization_request(task)

    assert request.max_image_calls == 5
    assert request.max_video_calls == 5


def test_video_task_authorization_includes_required_image_dependencies(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.runtime.authorization import (
        create_task_authorization_request,
    )

    create_product("honeydew", "周十五蜂蜜露")
    task = SimpleNamespace(
        task_id="task-video-with-image-dependencies",
        product_id="honeydew",
        request=SimpleNamespace(
            raw_message="用当前主图生成一个产品视频",
            requires_fresh_inspiration=False,
            deliverables=["video"],
        ),
    )

    request = create_task_authorization_request(task)

    assert request.allow_paid_image is True
    assert request.max_image_calls == 5
    assert request.allow_paid_video is True
    assert request.max_video_calls == 5


def test_exact_main_authorization_includes_dynamic_video_provider_budget():
    from product_creative.runtime.authorization import task_authorization_scope

    task = SimpleNamespace(
        task_id="task-exact-main-authorization",
        product_id="honeydew",
        request=SimpleNamespace(
            raw_message="用当前主图生成视频，包装不能变",
            requires_fresh_inspiration=False,
            deliverables=["video"],
        ),
        plan=SimpleNamespace(
            actions=[SimpleNamespace(action="compose_exact_main_video")],
        ),
    )

    request = task_authorization_scope(task)

    assert request["allow_paid_image"] is True
    assert request["max_image_calls"] == 5
    assert request["allow_paid_video"] is True
    assert request["max_video_calls"] == 5


def test_replacement_task_authorization_expires_previous_pending_request(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import artifacts
    from product_creative.runtime.authorization import create_task_authorization_request

    create_product("honeydew", "周十五蜂蜜露")
    task = SimpleNamespace(
        task_id="task-replacement-authorization",
        product_id="honeydew",
        request=SimpleNamespace(
            raw_message="生成一个产品视频",
            requires_fresh_inspiration=False,
            deliverables=["video"],
        ),
        plan=SimpleNamespace(
            actions=[SimpleNamespace(action="submit_video_generation_task")],
        ),
    )

    first = create_task_authorization_request(task)
    second = create_task_authorization_request(task)

    assert first.request_id != second.request_id
    assert artifacts().get("honeydew", first.request_id)["status"] == "EXPIRED"
    assert artifacts().get("honeydew", second.request_id)["status"] == "PENDING"


def test_pending_video_authorization_is_refreshed_when_image_scope_is_stale(
    tmp_path,
):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.common import write_json
    from product_creative.ports.runtime_repositories import artifacts
    from product_creative.runtime.authorization import (
        create_task_authorization_request,
    )
    from product_creative.runtime.creative_tasks import (
        _ensure_authorization_request,
    )

    create_product("honeydew", "周十五蜂蜜露")
    task = SimpleNamespace(
        task_id="task-refresh-video-authorization",
        product_id="honeydew",
        request=SimpleNamespace(
            raw_message="用当前主图生成一个产品视频",
            requires_fresh_inspiration=False,
            deliverables=["video"],
        ),
        plan=SimpleNamespace(
            actions=[SimpleNamespace(guard="task_authorization")],
        ),
        readiness=SimpleNamespace(ready=True),
        authorization_request_id="",
    )
    stale = create_task_authorization_request(task)
    stale.allow_paid_image = False
    stale.max_image_calls = 0
    write_json(Path(stale.artifact_path), stale.model_dump(mode="json"))
    task.authorization_request_id = stale.request_id

    _ensure_authorization_request(task)

    refreshed = artifacts().get("honeydew", task.authorization_request_id)
    expired = artifacts().get("honeydew", stale.request_id)
    assert task.authorization_request_id != stale.request_id
    assert refreshed["allow_paid_image"] is True
    assert refreshed["max_image_calls"] == 5
    assert expired["status"] == "EXPIRED"


def _configure_local_media_tools(monkeypatch):
    import shutil

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
        pytest.skip("local ffmpeg/ffprobe are required for real MP4 verification")
    monkeypatch.setenv("PRODUCT_CREATIVE_FFMPEG_PATH", str(ffmpeg))
    monkeypatch.setenv("PRODUCT_CREATIVE_FFPROBE_PATH", str(ffprobe))


def _small_compositor_plan(tmp_path):
    from product_creative.contracts.creative_artifacts import (
        MediaExecutionPlanArtifact,
    )
    from product_creative.runtime.product_plate import ensure_product_plate
    from product_creative.runtime.professional_artifacts import (
        save_professional_artifact,
    )

    _source, material = _register_plate_material(
        tmp_path,
        mode="source_alpha",
    )
    plate = ensure_product_plate(
        "honeydew",
        task_id="task-m13",
        material_id=material["material_id"],
    )
    plan = MediaExecutionPlanArtifact(
        **_base(
            "media-plan-task-m13",
            "product_creative.media_execution_plan.v1",
        ),
        production_bible_id="production-bible-task-m13",
        production_bible_hash=HEX_A,
        dependency_report_id="media-dependencies-task-m13",
        product_plate_id=plate.artifact_id,
        aspect_ratio="9:16",
        canvas=[270, 480],
        fps=12,
        shots=[
            {
                **_shot_plan(),
                "duration_seconds": 1,
                "execution_mode": "local_motion",
            },
            {
                **_shot_plan(),
                "shot_id": "shot-02",
                "ordinal": 2,
                "duration_seconds": 1,
                "execution_mode": "local_motion",
                "product_plate_required": True,
                "product_plate_motion": "subtle_entrance",
                "caption": "准备好，再出发",
                "idempotency_key": "task-m13:shot-02:fixture",
            },
        ],
        output_requirements={
            "codec": "h264",
            "audio_codec": "aac",
            "subtitle_mode": "deterministic_ass",
        },
        call_budget={"image": 0, "video": 0},
    )
    save_professional_artifact(plan)
    return plan, plate


def test_media_compositor_outputs_verified_h264_aac_mp4_and_ass(
    tmp_path,
    monkeypatch,
):
    from product_creative.common import ensure_product
    from product_creative.provider_gateway import DefaultGenerationProviderGateway
    from product_creative.runtime.media_compositor import (
        compose_final_video,
        probe_media,
        render_shot,
    )

    _configure_local_media_tools(monkeypatch)
    plan, plate = _small_compositor_plan(tmp_path)
    gateway = DefaultGenerationProviderGateway()
    rendered = []
    for shot in plan.shots:
        prepared = gateway.prepare_media_shot(
            "honeydew",
            plan.artifact_id,
            shot.shot_id,
            "local-fixture",
            "image",
        )
        source = gateway.submit_media_shot(
            "honeydew",
            prepared["payload_id"],
            "local-fixture",
            "fixture",
        )
        rendered.append(
            render_shot(
                "honeydew",
                plan=plan,
                shot=shot,
                source_media=ensure_product("honeydew") / source["source_media"],
                product_plate=plate,
                attempt=1,
            )
        )

    assert all(item.execution_status == "COMPLETED" for item in rendered)
    assert "uniform-scale and alpha-overlay" in " ".join(
        rendered[1].command_summary
    )
    assert "0.30s vertical entrance" in " ".join(
        rendered[1].command_summary
    )
    subtitle_path = (
        ensure_product("honeydew")
        / "artifacts"
        / "media_shots"
        / plan.artifact_id
        / "02-shot-02.ass"
    )
    assert "准备好，再出发" in subtitle_path.read_text(encoding="utf-8-sig")

    manifest = compose_final_video(
        "honeydew",
        plan=plan,
        shot_results=list(reversed(rendered)),
    )
    output = ensure_product("honeydew") / manifest.output_relative_path
    probe = probe_media(output)
    video = next(
        item for item in probe["streams"] if item["codec_type"] == "video"
    )
    audio = next(
        item for item in probe["streams"] if item["codec_type"] == "audio"
    )
    assert output.is_file()
    assert (video["width"], video["height"]) == (270, 480)
    assert video["codec_name"] == "h264"
    assert video["pix_fmt"] == "yuv420p"
    assert audio["codec_name"] == "aac"
    assert manifest.shot_result_ids == [item.artifact_id for item in rendered]
    assert manifest.duration_seconds == pytest.approx(2, abs=0.25)


def _engine_task(material_id, bible_id):
    return SimpleNamespace(
        task_id="task-m13",
        product_id="honeydew",
        request=SimpleNamespace(preserve_exact_packaging=True),
        selected_materials=[{"material_id": material_id}],
        professional_artifacts={"production_bible": bible_id},
        result_descriptors=[],
        status="READY",
        current_stage="PREPARING_ASSETS",
        blocked_reason="",
        updated_at=NOW,
        artifact_path="",
    )


def test_reliable_media_prepare_does_not_call_provider(
    tmp_path,
    monkeypatch,
):
    from product_creative.provider_gateway import (
        DefaultGenerationProviderGateway,
        configure_generation_provider_gateway,
        generation_provider_gateway,
    )
    from product_creative.runtime.media_production import (
        prepare_reliable_media_production,
    )

    _configure_local_media_tools(monkeypatch)
    material, bible = _setup_dependency_product(tmp_path)
    task = _engine_task(material["material_id"], bible.artifact_id)
    original = generation_provider_gateway()

    class NoProviderCalls(DefaultGenerationProviderGateway):
        def prepare_media_shot(self, *_args, **_kwargs):
            raise AssertionError("prepare phase must not prepare provider payloads")

        def submit_media_shot(self, *_args, **_kwargs):
            raise AssertionError("prepare phase must not submit provider work")

    configure_generation_provider_gateway(NoProviderCalls())
    try:
        result = prepare_reliable_media_production(
            task,
            provider="local-fixture",
            mode="fixture",
        )
    finally:
        configure_generation_provider_gateway(original)

    assert result["status"] == "READY"
    assert task.professional_artifacts["media_dependency_report"]
    assert task.professional_artifacts["product_plate"]
    assert task.professional_artifacts["media_execution_plan"]
    assert task.professional_artifacts.get("media_shot_results", []) == []


def test_unsubmitted_media_plan_can_recompile_for_a_corrected_provider(
    tmp_path,
    monkeypatch,
):
    from product_creative.runtime.media_production import (
        execute_reliable_media_production,
        prepare_reliable_media_production,
    )
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )

    _configure_local_media_tools(monkeypatch)
    material, bible = _setup_dependency_product(tmp_path)
    task = _engine_task(material["material_id"], bible.artifact_id)
    prepared = prepare_reliable_media_production(
        task,
        provider="volcengine-ark-video",
        mode="live",
    )
    old_plan_id = prepared["plan"]["artifact_id"]

    completed = execute_reliable_media_production(
        task,
        provider="local-fixture",
        mode="fixture",
        authorization=None,
    )
    new_plan_id = task.professional_artifacts["media_execution_plan"]

    assert completed["status"] == "HUMAN_REVIEW", completed
    assert new_plan_id != old_plan_id
    assert load_professional_artifact("honeydew", old_plan_id).artifact_id == old_plan_id
    assert load_professional_artifact("honeydew", new_plan_id).artifact_id == new_plan_id


def test_reliable_media_resume_retries_only_failed_shot(
    tmp_path,
    monkeypatch,
):
    import product_creative.provider_shots as provider_shots
    from product_creative.common import ensure_product
    from product_creative.runtime.media_production import (
        execute_reliable_media_production,
        prepare_reliable_media_production,
        resume_reliable_media_production,
    )

    _configure_local_media_tools(monkeypatch)
    material, bible = _setup_dependency_product(tmp_path)
    task = _engine_task(material["material_id"], bible.artifact_id)
    prepare_reliable_media_production(
        task,
        provider="local-fixture",
        mode="fixture",
    )
    real_fixture = provider_shots._fixture_image
    calls = {"shot-01": 0, "shot-02": 0}
    fail_second_once = True

    def flaky_fixture(product_root, payload):
        nonlocal fail_second_once
        shot_id = payload["source_shot_id"]
        calls[shot_id] += 1
        if shot_id == "shot-02" and fail_second_once:
            fail_second_once = False
            raise RuntimeError("injected shot-02 provider failure")
        return real_fixture(product_root, payload)

    monkeypatch.setattr(provider_shots, "_fixture_image", flaky_fixture)
    failed = execute_reliable_media_production(
        task,
        provider="local-fixture",
        mode="fixture",
        authorization=None,
    )

    assert failed["status"] == "FAILED_RETRYABLE"
    assert calls == {"shot-01": 1, "shot-02": 1}

    completed = resume_reliable_media_production(
        task,
        provider="local-fixture",
        mode="fixture",
        authorization=None,
    )

    assert completed["status"] == "HUMAN_REVIEW"
    assert calls == {"shot-01": 1, "shot-02": 2}
    manifest_path = (
        ensure_product("honeydew")
        / completed["manifest"]["output_relative_path"]
    )
    assert manifest_path.is_file()
    assert task.status == "READY"
    assert task.current_stage == "QUALITY_REVIEW"
    assert task.professional_artifacts["media_qa_report"]
    assert len(task.professional_artifacts["media_shot_results"]) == 3


def test_live_async_media_resume_polls_each_submitted_shot_without_resubmitting(
    tmp_path,
    monkeypatch,
):
    from product_creative.common import ensure_product, write_json
    from product_creative.contracts.models import (
        CreativeTaskRequest,
        TaskAuthorizationRecord,
    )
    from product_creative.provider_gateway import (
        DefaultGenerationProviderGateway,
        configure_generation_provider_gateway,
        generation_provider_gateway,
    )
    from product_creative.runtime.media_production import (
        execute_reliable_media_production,
        prepare_reliable_media_production,
        resume_reliable_media_production,
    )
    from product_creative.runtime.media_dependencies import resolve_media_tool

    _configure_local_media_tools(monkeypatch)
    material, bible = _setup_dependency_product(tmp_path)
    task = _engine_task(material["material_id"], bible.artifact_id)
    task.request = CreativeTaskRequest.from_message(
        "使用当前主图，包装和文字不能改变，生成一条有真实人物动作的竖版产品视频"
    )
    prepare_reliable_media_production(
        task,
        provider="volcengine-ark-video",
        mode="live",
    )
    product_root = ensure_product("honeydew")
    authorization_path = (
        product_root
        / "artifacts"
        / "task_authorizations"
        / "authorization-live-m13.json"
    )
    authorization = TaskAuthorizationRecord(
        authorization_id="authorization-live-m13",
        request_id="authorization-request-live-m13",
        task_id=task.task_id,
        product_id=task.product_id,
        allow_paid_video=True,
        max_video_calls=5,
        created_at=NOW,
        expires_at="2099-01-01T00:00:00+00:00",
        artifact_path=str(authorization_path),
    )
    write_json(
        authorization_path,
        authorization.model_dump(mode="json"),
    )

    original = generation_provider_gateway()

    class AsyncGateway(DefaultGenerationProviderGateway):
        def __init__(self):
            self.submits: list[str] = []
            self.polls: list[str] = []

        def prepare_media_shot(
            self,
            _product_id,
            _plan_id,
            shot_id,
            _provider,
            _media_kind,
        ):
            return {"payload_id": f"payload-{shot_id}"}

        def submit_media_shot(
            self,
            _product_id,
            payload_id,
            _provider,
            _mode,
            _execution_policy_id="",
        ):
            shot_id = payload_id.removeprefix("payload-")
            self.submits.append(shot_id)
            return {
                "success": True,
                "video_task": {
                    "video_task_id": f"video-task-{shot_id}",
                    "remote_task_id": f"remote-{shot_id}",
                },
            }

        def check_video_task(
            self,
            _product_id,
            task_id,
            _provider,
            _download,
        ):
            shot_id = task_id.removeprefix("video-task-")
            self.polls.append(shot_id)
            source_dir = product_root / "artifacts" / "generated_videos"
            source_dir.mkdir(parents=True, exist_ok=True)
            source = source_dir / f"{shot_id}.mp4"
            ffmpeg = resolve_media_tool("ffmpeg")
            assert ffmpeg
            import subprocess

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
                    "testsrc2=size=270x480:rate=12:duration=4",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(source),
                ],
                check=True,
                capture_output=True,
            )
            return {
                "success": True,
                "normalized_status": "completed",
                "video_task_id": task_id,
                "result": {
                    "result_id": f"result-{shot_id}",
                    "outputs": [
                        {
                            "type": "video",
                            "path": str(source.relative_to(product_root)),
                        }
                    ],
                },
            }

    gateway = AsyncGateway()

    def fixture_ocr(**kwargs):
        return {
            "observed_text": kwargs["expected_text"],
            "confidence": 0.99,
            "bounding_box": [0.15, 0.78, 0.70, 0.10],
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
            "observed_action": kwargs["expected_action"],
            "action_completed": True,
            "evidence_refs": [f"visual-fixture:{kwargs['shot_id']}"],
        }

    configure_generation_provider_gateway(gateway)
    try:
        first = execute_reliable_media_production(
            task,
            provider="volcengine-ark-video",
            mode="live",
            authorization=authorization,
            ocr_adapter=fixture_ocr,
            visual_adapter=fixture_visual,
        )
        second = resume_reliable_media_production(
            task,
            provider="volcengine-ark-video",
            mode="live",
            authorization=authorization,
            ocr_adapter=fixture_ocr,
            visual_adapter=fixture_visual,
        )
        third = resume_reliable_media_production(
            task,
            provider="volcengine-ark-video",
            mode="live",
            authorization=authorization,
            ocr_adapter=fixture_ocr,
            visual_adapter=fixture_visual,
        )
    finally:
        configure_generation_provider_gateway(original)

    assert first["status"] == "BLOCKED_PROVIDER"
    assert first["pending_shot"] == "shot-01"
    assert second["status"] == "BLOCKED_PROVIDER"
    assert second["pending_shot"] == "shot-02"
    blocking_checks = [
        (item["check_id"], item["status"], item["observed"])
        for item in third["quality"]["qa_report"]["checks"]
        if item["status"] != "PASS"
    ]
    assert third["status"] == "COMPLETED", blocking_checks
    assert gateway.submits == ["shot-01", "shot-02"]
    assert gateway.polls == ["shot-01", "shot-02"]
    assert authorization.used_video_calls == 2
    assert task.professional_artifacts.get("pending_media_shots") == {}
    assert task.professional_artifacts["media_composite_manifest"]
    quality_checks = {
        item["check_id"]: item
        for item in third["quality"]["qa_report"]["checks"]
    }
    assert quality_checks["freeze-frame:shot-01"]["status"] == "PASS"
    assert quality_checks["freeze-frame:shot-02"]["status"] == "PASS"
    assert quality_checks["action-fulfillment:shot-01"]["status"] == "PASS"
    assert quality_checks["action-fulfillment:shot-02"]["status"] == "PASS"


def test_authorized_live_generation_resumes_a_pending_media_shot(
    monkeypatch,
):
    import product_creative.runtime.creative_tasks as creative_tasks
    import product_creative.runtime.media_production as media_production

    authorization = SimpleNamespace(
        authorization_id="authorization-live-m13",
    )
    calls = []
    task = SimpleNamespace(
        task_id="task-m13-resume",
        product_id="honeydew",
        provider="volcengine-ark-video",
        authorization_id=authorization.authorization_id,
        status="BLOCKED_PROVIDER",
        blocked_reason="shot-01 is still processing",
        professional_artifacts={
            "pending_media_shots": {
                "shot-01": {
                    "video_task_id": "video-task-shot-01",
                }
            }
        },
        plan=SimpleNamespace(
            actions=[
                SimpleNamespace(
                    action="compose_exact_main_video",
                    status="PENDING",
                )
            ]
        ),
        result_descriptors=[],
        updated_at=NOW,
    )

    monkeypatch.setenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", "1")
    monkeypatch.setattr(
        creative_tasks,
        "load_task_authorization",
        lambda _product_id, _authorization_id: authorization,
    )

    def resume_pending(
        received_task,
        *,
        provider,
        mode,
        authorization,
    ):
        calls.append(
            (
                received_task.task_id,
                provider,
                mode,
                authorization.authorization_id,
            )
        )
        return {
            "status": "BLOCKED_PROVIDER",
            "pending_shot": "shot-01",
        }

    monkeypatch.setattr(
        media_production,
        "execute_reliable_media_production",
        resume_pending,
    )

    creative_tasks.execute_authorized_live_generation(task)

    assert calls == [
        (
            "task-m13-resume",
            "volcengine-ark-video",
            "live",
            "authorization-live-m13",
        )
    ]


def test_authorized_live_generation_retries_dependency_preflight_without_shots(
    monkeypatch,
):
    import product_creative.runtime.creative_tasks as creative_tasks
    import product_creative.runtime.media_production as media_production

    authorization = SimpleNamespace(
        authorization_id="authorization-live-m13",
    )
    calls = []
    task = SimpleNamespace(
        task_id="task-m13-preflight-resume",
        product_id="honeydew",
        provider="volcengine-ark-video",
        authorization_id=authorization.authorization_id,
        request=SimpleNamespace(preserve_exact_packaging=True),
        status="BLOCKED_PROVIDER",
        blocked_reason="ffmpeg is not available",
        professional_artifacts={
            "media_dependency_report": "media-dependencies-task-m13",
            "media_shot_results": [],
        },
        plan=SimpleNamespace(
            actions=[
                SimpleNamespace(
                    action="compose_exact_main_video",
                    status="PENDING",
                )
            ]
        ),
        result_descriptors=[],
        updated_at=NOW,
    )

    monkeypatch.setenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", "1")
    monkeypatch.setattr(
        creative_tasks,
        "load_task_authorization",
        lambda _product_id, _authorization_id: authorization,
    )

    def retry_preflight(received_task, *, provider, mode, authorization):
        calls.append((received_task.task_id, provider, mode))
        return {"status": "READY", "provider_calls": 0}

    monkeypatch.setattr(
        media_production,
        "execute_reliable_media_production",
        retry_preflight,
    )

    creative_tasks.execute_authorized_live_generation(task)

    assert calls == [
        ("task-m13-preflight-resume", "volcengine-ark-video", "live")
    ]


def test_continue_creative_task_routes_pending_provider_media_to_resume(
    tmp_path,
    monkeypatch,
):
    import product_creative.runtime.creative_tasks as creative_tasks

    task_path = tmp_path / "task-m13-resume.json"
    calls = []
    task = SimpleNamespace(
        task_id="task-m13-resume",
        product_id="honeydew",
        authorization_id="authorization-live-m13",
        authorization_request_id="",
        pending_proposal_id="",
        pending_proposal_kind="",
        status="BLOCKED_PROVIDER",
        current_stage="GENERATING",
        questions=[],
        artifact_path=str(task_path),
        professional_artifacts={
            "pending_media_shots": {
                "shot-01": {
                    "video_task_id": "video-task-shot-01",
                }
            }
        },
        updated_at=NOW,
        model_dump=lambda mode="json": {
            "task_id": "task-m13-resume",
            "status": "BLOCKED_PROVIDER",
        },
    )

    monkeypatch.setattr(
        creative_tasks,
        "load_creative_task",
        lambda _product_id, _task_id: task,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_load_or_start_discovery_session",
        lambda _task: SimpleNamespace(),
    )
    monkeypatch.setattr(
        creative_tasks,
        "_ensure_authorization_request",
        lambda _task, **_kwargs: None,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_continue_media_quality_repair",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_continue_production_approval",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_continue_creative_preview",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        creative_tasks,
        "execute_authorized_mock_generation",
        lambda received_task: calls.append(("mock", received_task.task_id)),
    )
    monkeypatch.setattr(
        creative_tasks,
        "execute_authorized_live_generation",
        lambda received_task: calls.append(("live", received_task.task_id)),
    )

    returned = creative_tasks.continue_creative_task(
        "honeydew",
        task.task_id,
        "继续生成刚才的视频",
    )

    assert returned is task
    assert calls == [
        ("mock", "task-m13-resume"),
        ("live", "task-m13-resume"),
    ]


def test_continue_creative_task_retries_unapproved_local_dependency_preflight(
    tmp_path,
    monkeypatch,
):
    import product_creative.runtime.creative_tasks as creative_tasks

    task_path = tmp_path / "task-m13-local-preflight.json"
    calls = []
    task = SimpleNamespace(
        task_id="task-m13-local-preflight",
        product_id="honeydew",
        authorization_id="",
        authorization_request_id="authorization-request-m13",
        pending_proposal_id="",
        pending_proposal_kind="",
        status="BLOCKED_PROVIDER",
        current_stage="PREPARING_ASSETS",
        blocked_reason="ffprobe is not usable",
        request=SimpleNamespace(preserve_exact_packaging=True),
        questions=[],
        artifact_path=str(task_path),
        professional_artifacts={
            "media_dependency_report": "media-dependencies-task-m13",
            "media_shot_results": [],
        },
        updated_at=NOW,
        model_dump=lambda mode="json": {
            "task_id": "task-m13-local-preflight",
            "status": task.status,
        },
    )

    monkeypatch.setattr(
        creative_tasks,
        "load_creative_task",
        lambda _product_id, _task_id: task,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_load_or_start_discovery_session",
        lambda _task: SimpleNamespace(),
    )
    monkeypatch.setattr(
        creative_tasks,
        "_ensure_authorization_request",
        lambda _task, **_kwargs: None,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_continue_media_quality_repair",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_continue_production_approval",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        creative_tasks,
        "_continue_creative_preview",
        lambda *_args, **_kwargs: False,
    )

    def retry_local_preflight(received_task):
        calls.append(received_task.task_id)
        received_task.status = "BLOCKED_AUTHORIZATION"
        received_task.current_stage = "GENERATING"
        received_task.blocked_reason = "compose_exact_main_video is waiting for task authorization."

    monkeypatch.setattr(
        creative_tasks,
        "advance_offline_preparation",
        retry_local_preflight,
    )

    returned = creative_tasks.continue_creative_task(
        "honeydew",
        task.task_id,
        "继续现有任务",
    )

    assert returned is task
    assert calls == ["task-m13-local-preflight"]
    assert task.status == "BLOCKED_AUTHORIZATION"


def test_exact_packaging_natural_language_plan_uses_task_authorization():
    from product_creative.application.planner import GoalPlanner
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message(
        "使用当前主图，包装和文字不能改变，生成一条竖版产品视频"
    )
    action = next(
        item
        for item in GoalPlanner().creative_task_actions(request)
        if item.action == "compose_exact_main_video"
    )

    assert action.guard == "task_authorization"


def test_desktop_professional_summary_projects_m13_media_state():
    from product_creative.application.console_queries import (
        _professional_summary,
    )

    summary = _professional_summary(
        {"professional_artifact_status": "complete"},
        {
            "media_dependency_report": {
                "overall_status": "READY",
                "blockers": [],
                "warnings": ["using configured ffmpeg path"],
            },
            "product_plate": {"artifact_id": "plate-1"},
            "media_execution_plan": {
                "artifact_id": "plan-1",
                "shots": [{"shot_id": "shot-01"}, {"shot_id": "shot-02"}],
            },
            "media_shot_results": [
                {
                    "shot_id": "shot-01",
                    "execution_status": "COMPLETED",
                },
                {
                    "shot_id": "shot-02",
                    "execution_status": "FAILED_RETRYABLE",
                    "error_detail": "temporary provider failure",
                },
            ],
            "media_composite_manifest": {},
        },
    )

    assert summary["media"]["dependency_status"] == "READY"
    assert summary["media"]["shots_completed"] == 1
    assert summary["media"]["shots_total"] == 2
    assert summary["media"]["current_failure"] == "temporary provider failure"
