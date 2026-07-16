from __future__ import annotations

import base64
from copy import deepcopy
import json
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENT = ROOT / ".hermes" / "plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))


def _create_mature_video_product(tmp_path):
    from product_creative.capabilities.material.asset_service import register_material_asset
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import product_brains

    create_product("honeydew", "周十五蜂蜜露")
    current = product_brains().current("honeydew")
    state = deepcopy(current["state"])
    state["basic"] = {"sku": "500mL 当前包装"}
    state["compliance"] = {
        "allowed_claims": ["清甜口感"],
        "forbidden_claims": ["医疗功效"],
    }
    product_brains().commit_state(
        "honeydew",
        state,
        change_kind="test_confirmed_product_fixture",
    )
    image_path = tmp_path / "current-main.png"
    image_path.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    )
    return register_material_asset(
        "honeydew",
        str(image_path),
        "current_main_image",
        "已确认当前包装主图",
        ["product_reference", "video_first_frame"],
    )


def test_natural_language_goal_becomes_a_general_creative_task_request():
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message(
        "帮我做一个今天能发的产品视频，先给我看方案，包装不能变化"
    )

    assert request.deliverables == ["video"]
    assert request.autonomy_mode == "preview_first"
    assert request.requires_fresh_inspiration is True
    assert request.preserve_exact_packaging is True
    assert request.raw_message.startswith("帮我做一个今天")


def test_exact_packaging_video_uses_existing_local_composer_not_live_video_provider():
    from product_creative.application.planner import GoalPlanner
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message("用当前主图做一个产品视频，主图不能变，包装不能重绘")
    actions = [step.action for step in GoalPlanner().creative_task_actions(request)]

    assert "compose_exact_main_video" in actions
    assert "submit_video_generation_task" not in actions
    assert "build_video_provider_payload" not in actions


def test_exact_packaging_detects_pixel_lock_and_forbidden_redraw_language():
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message(
        "主图和包装必须逐帧保持原始像素内容，不得重绘、改字、裁剪或风格化"
    )

    assert request.preserve_exact_packaging is True


def test_authorization_blocked_video_can_be_replanned_to_exact_packaging(tmp_path):
    from product_creative.runtime.creative_tasks import (
        _apply_task_constraint_revision,
        start_creative_task,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前主图做一个10秒产品视频",
            provider="volcengine-ark-video",
        )

        changed = _apply_task_constraint_revision(
            task,
            "补充硬约束：主图和包装必须逐帧保持原始像素，不得重绘、改字或裁剪",
        )

    actions = [step.action for step in task.plan.actions]
    assert changed is True
    assert task.request.preserve_exact_packaging is True
    assert task.revision_messages[-1].startswith("补充硬约束")
    assert "compose_exact_main_video" in actions
    assert "submit_video_generation_task" not in actions
    assert task.authorization_request_id == ""
    assert task.authorization_id == ""


def test_exact_main_video_story_is_product_neutral_without_confirmed_selling_points():
    from product_creative.capabilities.video.exact_video_service import _story_claims

    story = _story_claims(
        {
            "name": "周十五益生菌蜂蜜露",
            "generation_safe": {
                "product_name": "周十五益生菌蜂蜜露",
                "selling_points": [],
            },
        },
        {"visual_observations": {}, "provider_output": {}},
        "anime_story",
    )

    rendered = json.dumps(story, ensure_ascii=False)
    for forbidden in ("喝", "酸甜", "清爽", "口感", "配料", "开袋", "入口"):
        assert forbidden not in rendered
    assert story["product_name"] == "周十五益生菌蜂蜜露"


def test_readiness_for_a_new_video_product_asks_only_the_highest_value_questions(tmp_path):
    from product_creative.brain.discovery import assess_product_readiness
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.contracts.models import CreativeTaskRequest
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        before = product_brains().current("honeydew")

        report = assess_product_readiness(
            "honeydew",
            CreativeTaskRequest.from_message("帮我做一个今天能发的产品视频，包装不能变化"),
            task_id="task-video-1",
        )

        after = product_brains().current("honeydew")

    assert report.schema_version == "product_creative.product_readiness.v1"
    assert report.ready is False
    assert {item.key for item in report.fields if item.status == "UNKNOWN"} >= {
        "product_sku",
        "current_packaging",
        "claim_boundaries",
    }
    assert 1 <= len(report.questions) <= 3
    assert report.questions[0].field_key == "claim_boundaries"
    assert before["brain_version_id"] == after["brain_version_id"]
    assert before["content_hash"] == after["content_hash"]
    assert Path(report.artifact_path).is_file()


def test_creative_task_persists_the_original_goal_and_a_bounded_cross_domain_plan(tmp_path):
    from product_creative.capabilities.registry import action_descriptors
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        task = start_creative_task(
            "honeydew",
            "帮我做一个今天能发的产品视频，自动找灵感和本地主图，包装不能变化",
        )

    assert task.schema_version == "product_creative.creative_task.v1"
    assert task.status == "NEEDS_INPUT"
    assert task.current_stage == "UNDERSTANDING"
    assert task.request.raw_message.startswith("帮我做一个今天")
    assert task.plan.stages == [
        "UNDERSTANDING",
        "RESEARCHING",
        "IDEATING",
        "PREPARING_ASSETS",
        "GENERATING",
        "DELIVERING",
        "AWAITING_FEEDBACK",
    ]
    actions = [step.action for step in task.plan.actions]
    assert set(actions) <= set(action_descriptors())
    assert actions[:3] == [
        "collect_external_source_snapshot",
        "create_inspiration_candidates",
        "create_inspiration_pack",
    ]
    assert "prepare_task_material_pack" in actions
    assert "compose_exact_main_video" in actions
    assert "resolve_video_intent" not in actions
    assert "submit_video_generation_task" not in actions
    assert len(actions) <= 20
    assert 1 <= len(task.questions) <= 3
    assert Path(task.artifact_path).is_file()


def test_product_workflow_run_starts_a_recoverable_task_for_a_natural_language_goal(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        result = product_agent_turn(
            product_id="honeydew",
            message="帮我做一个今天能发的产品视频，包装不能变化",
        )

    assert result["success"] is True
    assert result["task_id"].startswith("task-")
    assert result["task_status"] == "NEEDS_INPUT"
    assert result["current_stage"] == "UNDERSTANDING"
    assert result["interpreted_goal"] == "帮我做一个今天能发的产品视频，包装不能变化"
    assert result["deliverables"] == ["video"]
    assert 1 <= len(result["questions"]) <= 3
    assert result["workflow_run_id"] == ""


def test_continuing_a_task_preserves_unknown_without_mutating_canonical_brain(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.runtime.creative_tasks import load_discovery_session
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        started = product_agent_turn(
            product_id="honeydew",
            message="帮我做一个今天能发的产品视频，包装不能变化",
        )
        before = product_brains().current("honeydew")
        continued = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="这个我不确定",
        )
        after = product_brains().current("honeydew")
        session = load_discovery_session("honeydew", started["task_id"])

    assert continued["task_id"] == started["task_id"]
    assert continued["task_status"] == "NEEDS_INPUT"
    assert "claim_boundaries" not in {
        item["field_key"] for item in continued["questions"]
    }
    assert session.schema_version == "product_creative.discovery_session.v1"
    assert session.turns[-1]["answer_status"] == "UNKNOWN"
    assert session.turns[-1]["field_key"] == "claim_boundaries"
    assert before["brain_version_id"] == after["brain_version_id"]
    assert before["content_hash"] == after["content_hash"]


def test_claim_boundary_parser_preserves_words_containing_conjunction_characters():
    from product_creative.brain.discovery import _claim_lists

    allowed, forbidden = _claim_lists(
        "允许使用产品名称周十五益生菌蜂蜜露、包装外观可爱、方便随身携带；"
        "禁止使用快速有效通便、温和不刺激、安全有效、孕妇适用、治疗便秘。"
    )

    assert allowed == ["产品名称周十五益生菌蜂蜜露", "包装外观可爱", "方便随身携带"]
    assert forbidden == ["使用快速有效通便", "温和不刺激", "安全有效", "孕妇适用", "治疗便秘"]


def test_video_task_reuses_existing_image_analysis_when_alignment_is_missing(tmp_path):
    from product_creative.capabilities.material.visual_service import analyze_image_asset
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        material = _create_mature_video_product(tmp_path)
        analysis = analyze_image_asset(
            "honeydew",
            material["material_id"],
            "mock-vision",
        )

        task = start_creative_task("honeydew", "生成一个产品视频")

    alignment_results = [
        item
        for item in task.result_descriptors
        if item.get("type") == "capability_result"
        and item.get("action") == "align_visual_analysis"
    ]
    assert alignment_results
    assert (
        alignment_results[-1]["output"]["alignment"]["source_analysis_id"]
        == analysis["analysis_id"]
    )


def test_blocked_product_task_rechecks_local_preparation_after_prerequisite_changes(tmp_path):
    from product_creative.common import write_json
    from product_creative.runtime.creative_tasks import (
        continue_creative_task,
        start_creative_task,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        task = start_creative_task("honeydew", "生成一个产品视频")
        before_resolves = sum(
            1
            for item in task.result_descriptors
            if item.get("type") == "capability_result"
            and item.get("action") == "resolve_video_intent"
        )
        task.status = "BLOCKED_PRODUCT"
        task.current_stage = "IDEATING"
        task.blocked_reason = "A previously missing local prerequisite was added."
        write_json(Path(task.artifact_path), task.model_dump(mode="json"))

        resumed = continue_creative_task(
            "honeydew",
            task.task_id,
            "前置条件已经补齐，请继续",
        )

    after_resolves = sum(
        1
        for item in resumed.result_descriptors
        if item.get("type") == "capability_result"
        and item.get("action") == "resolve_video_intent"
    )
    assert resumed.status != "BLOCKED_PRODUCT"
    assert after_resolves > before_resolves


def test_non_use_video_storyboard_is_generic_and_never_invents_food_or_audience_usage():
    from product_creative.capabilities.video.brief_creation_service import (
        _needs_non_use_storyboard,
        _non_use_storyboard,
    )

    assert _needs_non_use_storyboard([], "生成产品视频") is True
    assert _needs_non_use_storyboard(
        ["方便随身携带"],
        "不得出现任何疗效、孕妇适用或使用动作",
    ) is True

    storyboard = _non_use_storyboard("测试产品", "产品短视频")
    positive_text = " ".join(
        str(shot.get(key) or "")
        for shot in storyboard
        for key in (
            "purpose",
            "scene",
            "action",
            "audio",
            "caption",
            "visual_prompt",
            "key_message",
        )
    )
    for forbidden in ("孕妇", "妇女节", "饮用", "享用", "开瓶", "入杯", "核心卖点"):
        assert forbidden not in positive_text


def test_background_only_image_brief_keeps_product_and_audience_out_of_generation_prompt():
    from product_creative.capabilities.image.brief_service import (
        _apply_image_intent_to_brief,
    )

    brief = {
        "source_variant": 1,
        "product": {"name": "测试产品"},
        "target": {},
        "copy": {"headline": "旧占位", "subheadline": "旧占位"},
        "visual": {},
        "generation_contract": {},
    }
    image_intent = {
        "product_id": "test-product",
        "message": (
            "生成一张9:16竖屏背景图片，只生成粉紫色桌面、自然光影和云朵装饰；"
            "不要生成或重绘产品、包装、文字、人物或使用动作"
        ),
        "style_direction": "干净、柔和、低干扰",
    }

    updated = _apply_image_intent_to_brief(brief, image_intent)
    prompt = updated["generation_contract"]["prompt"]

    assert "独立背景素材" in prompt
    assert "不要生成或重绘产品" in prompt
    assert updated["copy"]["headline"] == ""
    assert updated["copy"]["text_to_render"] == []
    assert "background_only" in updated["generation_contract"]["must_preserve"]
    for forbidden in ("孕妇", "妇女节", "黄色半透明", "女性群像"):
        assert forbidden not in prompt


def test_readiness_does_not_promote_mutable_draft_state_to_confirmed_product_fact(tmp_path):
    from product_creative.brain.discovery import assess_product_readiness
    from product_creative.capabilities.product.ingestion_service import ingest_product
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.contracts.models import CreativeTaskRequest
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        before = product_brains().current("honeydew")
        ingestion = ingest_product(
            "honeydew",
            "这是用户刚提供但还没有字段级确认的产品资料，主打清甜口感。",
        )
        after = product_brains().current("honeydew")

        report = assess_product_readiness(
            "honeydew",
            CreativeTaskRequest.from_message("生成一个产品视频"),
            task_id="canonical-boundary",
        )

    fields = {item.key: item for item in report.fields}
    assert fields["product_sku"].status == "UNKNOWN"
    assert fields["claim_boundaries"].status == "UNKNOWN"
    assert before["brain_version_id"] == after["brain_version_id"]
    assert before["content_hash"] == after["content_hash"]
    assert Path(ingestion["draft_product_state"]).is_file()


def test_discovery_answer_requires_field_confirmation_before_canonical_writeback(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        started = product_agent_turn(
            product_id="honeydew",
            message="帮我生成一个产品视频",
        )
        before = product_brains().current("honeydew")
        proposed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="允许使用清甜口感，禁止医疗功效和治疗表述",
        )
        after_proposal = product_brains().current("honeydew")

        confirmed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认写入这项产品信息",
            confirmed=True,
            proposal_id=proposed["pending_proposal_id"],
        )
        after_confirmation = product_brains().current("honeydew")

    assert proposed["pending_proposal_id"].startswith("proposal-")
    assert before["brain_version_id"] == after_proposal["brain_version_id"]
    assert before["content_hash"] == after_proposal["content_hash"]
    assert after_confirmation["brain_version_id"] != before["brain_version_id"]
    assert after_confirmation["state"]["compliance"] == {
        "allowed_claims": ["清甜口感"],
        "forbidden_claims": ["医疗功效", "治疗表述"],
    }
    assert confirmed["pending_proposal_id"] == ""
    assert confirmed["task_status"] == "NEEDS_INPUT"


def test_task_authorization_is_scoped_and_never_includes_product_brain_writeback(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.authorization import (
        approve_task_authorization,
        authorization_allows,
        create_task_authorization_request,
    )
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        task = start_creative_task("honeydew", "帮我做一个今天能发的产品视频")
        before = product_brains().current("honeydew")
        request = create_task_authorization_request(task)
        authorization = approve_task_authorization(
            "honeydew",
            task.task_id,
            request.request_id,
            confirmed=True,
        )
        after = product_brains().current("honeydew")

    assert request.data_sources == ["web"]
    assert request.allow_paid_video is True
    assert authorization.task_id == task.task_id
    assert authorization.product_brain_writeback is False
    assert authorization_allows(authorization, "collect_external_source_snapshot", source="web")
    assert not authorization_allows(authorization, "collect_external_source_snapshot", source="xiaohongshu")
    assert authorization_allows(authorization, "submit_video_generation_task")
    assert not authorization_allows(authorization, "apply_evolution_proposal")
    assert before["content_hash"] == after["content_hash"]


def test_consumed_video_submit_authorization_still_allows_non_billable_status_recovery(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.runtime.authorization import (
        approve_task_authorization,
        authorization_allows,
        consume_task_authorization,
        create_task_authorization_request,
    )
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        task = start_creative_task("honeydew", "帮我生成一个产品视频")
        request = create_task_authorization_request(task)
        authorization = approve_task_authorization(
            "honeydew", task.task_id, request.request_id, confirmed=True
        )
        consume_task_authorization(authorization, "submit_video_generation_task")

    assert authorization.status == "CONSUMED"
    assert not authorization_allows(authorization, "submit_video_generation_task")
    assert authorization_allows(authorization, "check_video_task_status")
    assert not authorization_allows(
        authorization, "collect_external_source_snapshot", source="web"
    )


def test_live_video_runner_submits_once_and_recovers_status_through_a_fake_gateway(tmp_path):
    from product_creative.provider_gateway import (
        DefaultGenerationProviderGateway,
        configure_generation_provider_gateway,
    )
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    class FakeLiveGateway:
        def __init__(self):
            self.submits = 0
            self.polls = 0

        def prepare_payload(self, product_id, brief_id, provider, kind):
            return {"success": True, "payload_id": "payload-live-video", "provider": provider}

        def check_video_reference_readiness(self, product_id, payload_id):
            return {"success": True, "ready_for_provider": True, "blockers": []}

        def check_live_readiness(self, product_id, provider, kind, payload_id):
            return {"success": True, "ready_for_live": True, "blockers": []}

        def create_video_execution_policy(self, product_id, payload_id, provider, mode, confirmed, note):
            return {"success": True, "policy_id": "policy-live-video", "external_call_allowed": True}

        def submit_video(self, product_id, payload_id, provider, mode, execution_policy_id):
            self.submits += 1
            return {
                "success": True,
                "status": "submitted",
                "external_call_performed": True,
                "video_task": {"video_task_id": "remote-video-task-1"},
            }

        def check_video_task(self, product_id, task_id, provider, download):
            self.polls += 1
            return {
                "success": True,
                "normalized_status": "processing",
                "video_task_id": task_id,
                "external_call_performed": True,
            }

    gateway = FakeLiveGateway()
    try:
        configure_generation_provider_gateway(gateway)
        with patch.dict("os.environ", {"PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER": "1"}):
            with workspace_scope(tmp_path):
                _create_mature_video_product(tmp_path)
                started = product_agent_turn(
                    product_id="honeydew",
                    message="用当前主图生成一个产品视频",
                    provider="volcengine-ark-video",
                )
                submitted = product_agent_turn(
                    product_id="honeydew",
                    task_id=started["task_id"],
                    message="确认本任务允许一次真实视频生成",
                    confirmed=True,
                    authorization_id=started["authorization_request"]["request_id"],
                )
                polled = product_agent_turn(
                    product_id="honeydew",
                    task_id=started["task_id"],
                    message="继续查询视频状态",
                )
    finally:
        configure_generation_provider_gateway(DefaultGenerationProviderGateway())

    assert submitted["task_status"] == "GENERATING", submitted["blocked_reason"]
    assert "continue this task" in submitted["blocked_reason"]
    assert polled["task_status"] == "GENERATING"
    assert "processing" in polled["blocked_reason"]
    assert gateway.submits == 1
    assert gateway.polls == 1


def test_authorized_mature_video_task_selects_material_and_prepares_provider_payload_offline(tmp_path):
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)

        started = product_agent_turn(
            product_id="honeydew",
            message="用当前主图帮我生成一个抖音产品视频，本测试允许生成模型改编画面",
        )
        advanced = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务允许一次视频模型调用",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )

    actions = [
        item.get("action")
        for item in advanced["result_descriptors"]
        if item.get("type") == "capability_result"
    ]
    assert advanced["selected_materials"][0]["role"] == "current_main_image"
    assert "prepare_task_material_pack" in actions
    assert "resolve_video_intent" in actions
    assert "create_video_brief" in actions
    assert "build_video_provider_payload" in actions
    assert "submit_video_generation_task" not in actions
    assert advanced["task_status"] in {"BLOCKED_PROVIDER", "READY"}


def test_authorized_fresh_research_resumes_from_imported_snapshot_without_promoting_it_to_fact(tmp_path):
    from product_creative.capabilities.inspiration.collection_service import (
        collect_external_source_snapshot,
    )
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="帮我做一个今天能发的产品视频，自动搜索最新灵感",
        )
        researching = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务可搜索网页并调用一次视频模型",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )
        before_import = product_brains().current("honeydew")
        snapshot = collect_external_source_snapshot(
            "honeydew",
            "manual-import",
            "周十五蜂蜜露 今日短视频灵感",
            "web",
            "import",
            3,
            "",
            "2026-07-15 夏日饮品短视频趋势：前三秒用冰凉反差开场。",
            "https://example.invalid/fixture",
            "",
            5,
            0,
            False,
        )
        resumed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="继续刚才的视频任务",
        )
        after_import = product_brains().current("honeydew")

    actions = [
        item.get("action")
        for item in resumed["result_descriptors"]
        if item.get("type") == "capability_result"
    ]
    assert researching["task_status"] == "RESEARCHING"
    assert researching["agent_action_request"]["tool"] == "web_search"
    assert snapshot["snapshot"]["not_product_fact"] is True
    assert "create_inspiration_candidates" in actions
    assert "create_inspiration_pack" in actions
    assert before_import["content_hash"] == after_import["content_hash"]


def test_mock_video_generation_is_task_authorized_idempotent_and_has_no_external_call(tmp_path):
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="用当前主图生成一个产品视频",
            provider="mock-video",
        )
        generated = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务允许一次 mock 视频生成",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )
        replayed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="重复确认不应再次生成",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )

    submissions = [
        item
        for item in generated["result_descriptors"]
        if item.get("action") == "submit_video_generation_task"
    ]
    replayed_submissions = [
        item
        for item in replayed["result_descriptors"]
        if item.get("action") == "submit_video_generation_task"
    ]
    assert generated["task_status"] == "AWAITING_FEEDBACK"
    assert len(submissions) == 1
    assert submissions[0]["output"]["external_call_performed"] is False
    assert submissions[0]["output"]["result_id"]
    assert len(replayed_submissions) == 1


def test_text_and_mock_image_share_the_same_natural_language_task_entry(tmp_path):
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        text_task = product_agent_turn(
            product_id="honeydew",
            message="帮我写一版电商主图文案",
        )
        image_started = product_agent_turn(
            product_id="honeydew",
            message="帮我生成一张产品图片，产品主体和包装不能变化",
            provider="mock-image",
        )
        image_generated = product_agent_turn(
            product_id="honeydew",
            task_id=image_started["task_id"],
            message="确认本任务允许一次 mock 图片生成",
            confirmed=True,
            authorization_id=image_started["authorization_request"]["request_id"],
        )

    text_actions = [
        item.get("action")
        for item in text_task["result_descriptors"]
        if item.get("type") == "capability_result"
    ]
    image_submissions = [
        item
        for item in image_generated["result_descriptors"]
        if item.get("action") == "submit_image_generation_job"
    ]
    assert text_task["deliverables"] == ["text"]
    assert text_task["task_status"] == "AWAITING_FEEDBACK"
    assert "run_channel_review" in text_actions
    assert image_generated["deliverables"] == ["image"]
    assert image_generated["task_status"] == "AWAITING_FEEDBACK", image_generated["blocked_reason"]
    assert len(image_submissions) == 1
    assert image_submissions[0]["output"]["external_call_count"] == 0


def test_live_image_result_id_is_bound_into_delivery_review(tmp_path):
    from product_creative.runtime.creative_tasks import _offline_action_args, start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "帮我生成一张产品图片，产品主体和包装不能变化",
            provider="volcengine-ark-image",
        )
        task.result_descriptors.append(
            {
                "type": "capability_result",
                "action": "submit_image_generation_job",
                "status": "succeeded",
                "output": {
                    "image_generation_run": {
                        "jobs": [{"result_id": "image-result-live-001", "status": "completed"}]
                    }
                },
            }
        )

        args = _offline_action_args(task, "review_generated_result")

    assert args == {"product_id": "honeydew", "result_id": "image-result-live-001"}


def test_failed_local_delivery_resumes_without_resubmitting_live_generation(tmp_path):
    from product_creative.common import write_json
    from product_creative.runtime.creative_tasks import continue_creative_task, start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "帮我生成一张产品图片，产品主体和包装不能变化",
            provider="volcengine-ark-image",
        )
        for step in task.plan.actions:
            step.status = "COMPLETED"
        review_step = next(step for step in task.plan.actions if step.action == "review_generated_result")
        review_step.status = "FAILED"
        task.status = "FAILED_FINAL"
        task.current_stage = "DELIVERING"
        task.blocked_reason = "review_generated_result failed: result id or path is required"
        task.result_descriptors.append(
            {
                "type": "capability_result",
                "action": "submit_image_generation_job",
                "status": "succeeded",
                "output": {
                    "image_generation_run": {
                        "jobs": [{"result_id": "image-result-live-001", "status": "completed"}]
                    }
                },
            }
        )
        product_root = Path(task.artifact_path).parents[2]
        write_json(
            product_root / "artifacts" / "generated_images" / "image-result-live-001.json",
            {
                "result_id": "image-result-live-001",
                "product_id": "honeydew",
                "brief_type": "image",
                "provider": "volcengine-ark-image",
                "mode": "live",
                "status": "completed",
                "outputs": [],
            },
        )
        write_json(Path(task.artifact_path), task.model_dump(mode="json"))

        resumed = continue_creative_task("honeydew", task.task_id, "继续刚才失败的交付步骤")

    submissions = [
        item for item in resumed.result_descriptors if item.get("action") == "submit_image_generation_job"
    ]
    reviews = [item for item in resumed.result_descriptors if item.get("action") == "review_generated_result"]
    assert resumed.status == "AWAITING_FEEDBACK"
    assert len(submissions) == 1
    assert reviews[-1]["output"]["package"]["source_result_id"] == "image-result-live-001"


def test_mixed_mock_image_and_video_task_runs_in_dependency_order(tmp_path):
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="先生成一张产品首帧图片，再生成一个产品视频",
            provider="mock",
        )
        generated = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务允许各一次 mock 图片和视频生成",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )

    submissions = [
        item
        for item in generated["result_descriptors"]
        if item.get("action") in {
            "submit_image_generation_job",
            "submit_video_generation_task",
        }
    ]
    assert generated["deliverables"] == ["image", "video"]
    assert [item["action"] for item in submissions] == [
        "submit_image_generation_job",
        "submit_video_generation_task",
    ]
    assert all(
        item["output"].get("external_call_performed") is False
        or item["output"].get("external_call_count") == 0
        for item in submissions
    )
    assert generated["task_status"] == "AWAITING_FEEDBACK"


def test_one_time_result_revision_stays_task_scoped_and_requests_fresh_authorization(tmp_path):
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="用当前主图生成一个产品视频",
            provider="mock-video",
        )
        generated = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务允许一次 mock 视频生成",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )
        before = product_brains().current("honeydew")
        revised = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="只改这一次：前三秒节奏更快，但不要长期记住",
        )
        after = product_brains().current("honeydew")

    assert generated["task_status"] == "AWAITING_FEEDBACK"
    assert revised["task_status"] == "BLOCKED_AUTHORIZATION"
    assert revised["pending_proposal_id"] == ""
    assert revised["authorization_request"]["request_id"] != started["authorization_request"]["request_id"]
    revisions = [
        item for item in revised["result_descriptors"]
        if item.get("type") == "task_revision"
    ]
    assert revisions[-1]["scope"] == "current_task"
    assert revisions[-1]["message"].startswith("只改这一次")
    assert before["brain_version_id"] == after["brain_version_id"]
    assert before["content_hash"] == after["content_hash"]


def test_long_term_result_feedback_requires_proposal_confirmation_before_brain_writeback(tmp_path):
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="用当前主图生成一个产品视频",
            provider="mock-video",
        )
        generated = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务允许一次 mock 视频生成",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )
        before = product_brains().current("honeydew")
        proposed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="以后所有产品视频前三秒都要更快，请长期记住",
        )
        after_proposal = product_brains().current("honeydew")
        confirmed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认将这条长期偏好写入 Product Brain",
            confirmed=True,
            proposal_id=proposed["pending_proposal_id"],
        )
        after_confirmation = product_brains().current("honeydew")

    assert generated["task_status"] == "AWAITING_FEEDBACK"
    assert proposed["pending_proposal_id"].startswith("proposal-")
    assert proposed["pending_proposal_kind"] == "learning"
    assert before["brain_version_id"] == after_proposal["brain_version_id"]
    assert before["content_hash"] == after_proposal["content_hash"]
    assert confirmed["pending_proposal_id"] == ""
    assert confirmed["task_status"] == "COMPLETED"
    assert after_confirmation["brain_version_id"] != before["brain_version_id"]
    assert any(
        "前三秒都要更快" in item
        for item in after_confirmation["state"]["learning"]["video_script_preferences"]
    ), after_confirmation["state"]["learning"]


def test_desktop_read_model_exposes_product_scoped_creative_tasks(tmp_path):
    from product_creative.application.console_queries import ProductCreativeConsoleQueries
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    other_workspace = tmp_path / "other-workspace"
    other_workspace.mkdir()
    queries = ProductCreativeConsoleQueries()

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="用当前主图生成一个产品视频",
            provider="mock-video",
        )
        tasks = queries.creative_tasks("honeydew")
        detail = queries.creative_task("honeydew", started["task_id"])

    with workspace_scope(other_workspace):
        isolated = queries.creative_tasks("honeydew")

    assert [item["task_id"] for item in tasks] == [started["task_id"]]
    assert detail["request"]["raw_message"] == "用当前主图生成一个产品视频"
    assert detail["readiness"]["schema_version"] == "product_creative.product_readiness.v1"
    assert isolated == []


def test_real_hermes_agent_loop_routes_natural_language_through_product_workflow_tool(tmp_path):
    from product_creative.capabilities.product.commands import command_descriptors
    from product_creative.runtime.creative_tasks import load_creative_task
    from product_creative.workspace import workspace_scope
    from run_agent import AIAgent
    from tools.registry import registry

    user_message = "帮我给周十五蜂蜜露做一个今天能发的视频，包装不能变化"
    descriptor = next(
        item for item in command_descriptors()
        if item.name == "product_workflow_run"
    )
    previous = registry._tools.get(descriptor.name)
    registry.register(
        name=descriptor.name,
        toolset="product_creative",
        schema=descriptor.schema,
        handler=descriptor.handler,
        check_fn=lambda: True,
    )

    def response(content="", *, tool_calls=None, finish_reason="stop"):
        message = SimpleNamespace(
            content=content,
            tool_calls=tool_calls,
            refusal=None,
            reasoning=None,
            reasoning_content=None,
            reasoning_details=None,
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
            usage=None,
            model="fixture/hermes-product-agent",
        )

    tool_call = SimpleNamespace(
        id="call-product-workflow-1",
        type="function",
        function=SimpleNamespace(
            name="product_workflow_run",
            arguments=json.dumps(
                {
                    "product_id": "honeydew",
                    "message": user_message,
                    "autonomy_mode": "adaptive",
                },
                ensure_ascii=False,
            ),
        ),
    )
    responses = [
        response(tool_calls=[tool_call], finish_reason="tool_calls"),
        response("已建立可恢复的产品创作任务，并提出当前最关键的问题。"),
    ]
    api_calls = []
    logging_dependency = SimpleNamespace(
        ConcurrentRotatingFileHandler=RotatingFileHandler
    )
    logging_patch = patch.dict(
        sys.modules,
        {"concurrent_log_handler": logging_dependency},
    )
    logging_patch.start()

    try:
        with workspace_scope(tmp_path):
            from product_creative.capabilities.product.workspace_service import create_product

            create_product("honeydew", "周十五蜂蜜露")
            exact_tool_definition = {
                "type": "function",
                "function": descriptor.schema,
            }
            with patch("run_agent.OpenAI"), patch(
                "run_agent.get_tool_definitions",
                return_value=[exact_tool_definition],
            ), patch(
                "run_agent.check_toolset_requirements",
                return_value={},
            ), patch(
                "agent.model_metadata.get_model_context_length",
                return_value=128_000,
            ):
                agent = AIAgent(
                    model="fixture/hermes-product-agent",
                    api_key="fixture-key",
                    base_url="http://127.0.0.1:1/v1",
                    enabled_toolsets=["product_creative"],
                    max_iterations=4,
                    tool_delay=0,
                    quiet_mode=True,
                    skip_context_files=True,
                    skip_memory=True,
                )
            agent.client = MagicMock()
            agent._persist_session = lambda *args, **kwargs: None
            agent._save_trajectory = lambda *args, **kwargs: None

            def fixture_llm(api_kwargs):
                api_calls.append(api_kwargs)
                return responses.pop(0)

            agent._interruptible_api_call = fixture_llm
            result = agent.run_conversation(user_message, conversation_history=[])
            tool_messages = [
                message
                for message in api_calls[-1]["messages"]
                if message.get("role") == "tool"
            ]
            tool_payload = json.loads(tool_messages[-1]["content"])
            task = load_creative_task("honeydew", tool_payload["task_id"])
    finally:
        logging_patch.stop()
        if previous is None:
            registry.deregister(descriptor.name)
        else:
            registry._tools[descriptor.name] = previous

    assert result["completed"] is True
    assert result["final_response"].startswith("已建立可恢复")
    assert len(api_calls) == 2
    assert any(
        item.get("role") == "user" and user_message in str(item.get("content"))
        for item in api_calls[0]["messages"]
    )
    assert tool_payload["success"] is True
    assert tool_payload["task_status"] == "NEEDS_INPUT"
    assert task.request.raw_message == user_message
    assert task.schema_version == "product_creative.creative_task.v1"


def test_product_understanding_goal_does_not_require_a_fake_media_deliverable(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.contracts.models import CreativeTaskRequest
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.brain.discovery import assess_product_readiness
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        current = product_brains().current("honeydew")
        state = deepcopy(current["state"])
        state["basic"] = {"sku": "500mL 当前包装"}
        state["compliance"] = {
            "allowed_claims": ["清甜口感"],
            "forbidden_claims": ["医疗功效"],
        }
        product_brains().commit_state(
            "honeydew", state, change_kind="test_confirmed_product_fixture"
        )
        report = assess_product_readiness(
            "honeydew",
            CreativeTaskRequest.from_message("先继续了解这个产品，完善产品大脑"),
            task_id="understanding-only",
        )

    delivery = next(item for item in report.fields if item.key == "delivery_spec")
    assert delivery.status == "CONFIRMED"
    assert delivery.value == ["understanding"]
    assert report.ready is True


def test_delivery_answer_replans_the_same_task_without_canonical_writeback(tmp_path):
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="帮我做点内容",
            provider="mock-video",
        )
        before = product_brains().current("honeydew")
        continued = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="最终需要一个产品视频",
        )
        after = product_brains().current("honeydew")

    assert started["questions"][0]["field_key"] == "delivery_spec"
    assert continued["deliverables"] == ["video"]
    assert continued["authorization_request"]["allow_paid_video"] is True


def test_plain_text_cannot_be_promoted_as_current_packaging_evidence(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        current = product_brains().current("honeydew")
        state = deepcopy(current["state"])
        state["basic"] = {"sku": "500mL 当前包装"}
        state["compliance"] = {
            "allowed_claims": ["清甜口感"],
            "forbidden_claims": ["医疗功效"],
        }
        product_brains().commit_state("honeydew", state, change_kind="test_fixture")
        started = product_agent_turn(
            product_id="honeydew",
            message="帮我生成一个产品视频，包装不能变化",
        )
        before = product_brains().current("honeydew")
        continued = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="就用最新包装",
        )
        after = product_brains().current("honeydew")

    assert started["questions"][0]["field_key"] == "current_packaging"
    assert continued["task_status"] == "NEEDS_INPUT"
    assert continued["pending_proposal_id"] == ""
    assert "actual registered material" in continued["blocked_reason"]
    assert before["content_hash"] == after["content_hash"]
    assert any(
        item.get("action") == "submit_video_generation_task"
        for item in continued["result_descriptors"]
    ) is False
    assert before["content_hash"] == after["content_hash"]


def test_channel_name_alone_does_not_authorize_platform_scraping(tmp_path):
    from product_creative.runtime.authorization import create_task_authorization_request
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        channel_task = start_creative_task(
            "honeydew",
            "用当前主图生成一个抖音产品视频",
        )
        research_task = start_creative_task(
            "honeydew",
            "搜索抖音最新爆款灵感，再用当前主图生成产品视频",
        )
        channel_authorization = create_task_authorization_request(channel_task)
        research_authorization = create_task_authorization_request(research_task)

    assert channel_authorization.data_sources == []
    assert channel_authorization.allow_browser_cookies is False
    assert research_authorization.data_sources == ["web", "douyin"]
    assert research_authorization.allow_browser_cookies is True


def test_all_research_sources_can_degrade_to_confirmed_brain_without_claiming_freshness(tmp_path):
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_video_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="帮我做一个今天能发的产品视频，自动搜索最新灵感",
            provider="mock-video",
        )
        researching = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务可搜索网页并调用一次 mock 视频模型",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )
        before = product_brains().current("honeydew")
        degraded = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="网页和平台搜索都失败了，继续使用已有 Product Brain，不使用实时信息",
        )
        after = product_brains().current("honeydew")

    assert researching["task_status"] == "RESEARCHING"
    assert degraded["task_status"] == "AWAITING_FEEDBACK"
    fallback = [
        item for item in degraded["result_descriptors"]
        if item.get("type") == "research_fallback"
    ]
    assert fallback[-1]["used_realtime_information"] is False
    assert fallback[-1]["product_brain_writeback"] is False
    assert before["content_hash"] == after["content_hash"]
