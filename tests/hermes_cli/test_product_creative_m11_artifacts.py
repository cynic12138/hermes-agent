from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENT = ROOT / ".hermes" / "plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))


def _local_media_tool(name: str) -> Path:
    known_root = Path(
        r"C:\Program Files\AIMIXMaster\resources\app.asar.unpacked"
        r"\node_modules\ffmpeg-static-all\win\bin"
    )
    packaged = known_root / f"{name}.exe"
    return packaged if packaged.is_file() else Path(shutil.which(name) or "")


def _m12_offline_skill_executor(spec, input_payload, _expected_output_schema):
    if spec.name == "creative-strategy":
        product_name = input_payload.get("product_name") or "周十五蜂蜜露"
        route = input_payload.get("production_route") or "exact-main-composite"
        materials = input_payload.get("required_materials") or []
        shared = {
            "channel_fit": "抖音竖屏剧情短视频",
            "required_materials": materials,
            "production_route": route,
        }
        return {
            "candidates": [
                {
                    **shared,
                    "direction": "stable",
                    "one_liner": f"用出门前被打断的生活冲突，让{product_name}成为恢复行动节奏的随身道具。",
                    "stop_reason": "手机倒计时与停在门把上的手形成动作中断。",
                    "product_role": "产品以当前包装作为剧情转折道具，不承担未经确认的功效承诺。",
                    "target_emotion": "紧张后释然",
                    "hook": "0–3 秒：手机倒计时，手已握住门把却突然停住。",
                    "conflict": "主角必须马上出门，却因临时状况打乱行动节奏。",
                    "progression": ["倒计时催促", "门口停住", "翻包寻找", "产品出现", "恢复从容"],
                    "ending": "主角关门出发，固定产品 plate 克制收尾。",
                    "risks": ["不得展示敏感使用过程", "不得作即时效果承诺"],
                    "estimated_cost": "low",
                    "feasibility": 0.94,
                    "historical_difference": "加入时间压力、寻找和转折，不再使用静态主图配通用字幕。",
                    "novelty_strategy": "用动作中断替代静态产品陈列。",
                },
                {
                    **shared,
                    "direction": "variation",
                    "one_liner": f"把包内最后一个位置变成物件轻喜剧选拔，{product_name}以便携体量进入随身清单。",
                    "stop_reason": "钥匙和耳机同时争抢包内最后一个位置。",
                    "product_role": "产品以固定包装 plate 参与物件小剧场，只承担外观和便携的视觉角色。",
                    "target_emotion": "可爱、轻松",
                    "hook": "0–3 秒：包内俯拍，钥匙和耳机同时滑向最后一个位置。",
                    "conflict": "包内只剩一个位置，常用物件争论谁更值得被带走。",
                    "progression": ["物件争位", "轮流陈述", "主角犹豫", "产品入场", "全员让位"],
                    "ending": "拉链合上，主角拎包出门，固定包装完成品牌识别。",
                    "risks": ["拟人对白不得暗示功效", "包装文字不得重绘"],
                    "estimated_cost": "medium",
                    "feasibility": 0.86,
                    "historical_difference": "以物件拟人和选择冲突区别于真人口播。",
                    "novelty_strategy": "改变冲突主体和产品进入机制。",
                },
                {
                    **shared,
                    "direction": "exploration",
                    "one_liner": f"一分钟后的自己发来提醒，{product_name}成为现实与未来之间的固定视觉锚点。",
                    "stop_reason": "来自一分钟后自己的语音打破普通日常。",
                    "product_role": "产品作为未来提醒携带的日常准备，只承担故事道具和品牌识别。",
                    "target_emotion": "惊喜、未来感",
                    "hook": "0–3 秒：手机收到发送者为“一分钟后的我”的语音。",
                    "conflict": "主角不理解未来提醒，时间却继续倒数。",
                    "progression": ["未来消息", "寻找线索", "镜面闪回", "产品被定位", "时间线恢复"],
                    "ending": "主角走入电梯，固定产品 plate 以扫描线收尾。",
                    "risks": ["科幻效果不得覆盖产品", "避免恐吓式健康叙事"],
                    "estimated_cost": "high",
                    "feasibility": 0.72,
                    "historical_difference": "使用时间错位结构区别于生活记录和产品展示。",
                    "novelty_strategy": "用时间谜题改变钩子、转折和收尾。",
                },
            ]
        }
    if spec.name == "creative-review":
        candidates = input_payload["candidates"]
        requested = input_payload.get("requested_direction") or "stable"
        score_by_direction = {
            "stable": (0.94, 0.90, 0.72, 0.94, 1.0, 0.96),
            "variation": (0.87, 0.91, 0.84, 0.86, 0.96, 0.90),
            "exploration": (0.78, 0.86, 0.96, 0.72, 0.88, 0.86),
        }
        scores = []
        for candidate in candidates:
            values = score_by_direction[candidate["direction"]]
            total = round(sum(values) / len(values), 3)
            if candidate["direction"] == requested:
                total = 0.98
            scores.append(
                {
                    "candidate_id": candidate["artifact_id"],
                    "product_fit": values[0],
                    "channel_fit": values[1],
                    "freshness": values[2],
                    "feasibility": values[3],
                    "packaging_safety": values[4],
                    "compliance_safety": values[5],
                    "total": total,
                }
            )
        selected = max(scores, key=lambda item: item["total"])["candidate_id"]
        return {
            "scores": scores,
            "selected_candidate_id": selected,
            "selection_reason": "综合产品匹配、渠道适配、新鲜度、可制作性和风险后选择。",
            "rejected_candidates": [
                {
                    "candidate_id": item["candidate_id"],
                    "reason": "综合评分或当前执行风险不如选中方向。",
                }
                for item in scores
                if item["candidate_id"] != selected
            ],
            "allowed_deviation": ["对白可在不改变事实和情节功能的前提下微调"],
        }
    if spec.name == "script-writer":
        candidate = input_payload["candidate"]
        direction = candidate["direction"]
        profiles = {
            "stable": {
                "characters": [{"name": "小周", "motivation": "在时间压力下仍从容完成出门安排"}],
                "setting": "清晨卧室、玄关和电梯口",
                "hook_visual": "手机时间跳到 08:59，主角握住门把却突然停住。",
                "hook_audio": "催促提示音在动作中断时突然静音。",
                "incident": "同事发来会议已经开始的消息。",
                "escalation": ["时间继续倒数。", "主角翻包却接连拿出无关物件。"],
                "turn": "镜头找到固定产品 plate，动作和声音从急促转为轻快。",
            },
            "variation": {
                "characters": [
                    {"name": "钥匙", "motivation": "证明自己是出门必需品"},
                    {"name": "耳机", "motivation": "争取包内最后一个位置"},
                    {"name": "小周", "motivation": "完成一次从容选择"},
                ],
                "setting": "打开的随身包内部与清晨玄关",
                "hook_visual": "包内俯拍，钥匙和耳机同时滑向最后一个位置。",
                "hook_audio": "拉链声后两个物件同时说“选我”。",
                "incident": "主角准备合上包，却发现只剩最后一个位置。",
                "escalation": ["钥匙和耳机轮流证明自己必须被带走。", "门外催促声越来越近。"],
                "turn": "固定产品 plate 被看见，两个物件同时安静并让出位置。",
            },
            "exploration": {
                "characters": [
                    {"name": "小周", "motivation": "理解未来提醒"},
                    {"name": "一分钟后的自己", "motivation": "提醒现在的自己做好准备"},
                ],
                "setting": "清晨玄关、镜面反射与电梯口",
                "hook_visual": "手机收到发送者为“一分钟后的我”的语音。",
                "hook_audio": "未来语音说“先别出门”，随后进入倒计时。",
                "incident": "主角必须在一分钟内找出提醒原因。",
                "escalation": ["镜面闪回指向随身包。", "倒计时只剩十秒。"],
                "turn": "固定产品 plate 被定位后，时间线恢复。",
            },
        }
        profile = profiles[direction]
        return {
            "premise": candidate["one_liner"],
            "characters": profile["characters"],
            "setting": profile["setting"],
            "world_rules": ["不展示敏感使用过程", "产品事实只来自 Grounding Pack"],
            "hook_visual": profile["hook_visual"],
            "hook_audio": profile["hook_audio"],
            "inciting_incident": profile["incident"],
            "conflict": candidate["conflict"],
            "escalation": profile["escalation"],
            "turn": profile["turn"],
            "product_intervention": candidate["product_role"],
            "ending": candidate["ending"],
            "dialogue": ["准备好，再出发。"],
            "narrative_functions": ["视觉钩子", "冲突建立", "行动升级", "产品转折", "情绪收束"],
            "prohibited_content": [
                "治疗或保证效果的健康承诺",
                "敏感使用过程",
                "重绘产品包装和文字",
            ],
        }
    if spec.name == "storyboard-director":
        story = input_payload["story"]
        scene = story["setting"]
        characters = [item["name"] for item in story["characters"]]
        return {
            "specification": {
                "style": "现实轻剧情，动作和声音围绕冲突转折推进",
                "audio": story["hook_audio"],
            },
            "shots": [
                {
                    "shot_id": "shot-01",
                    "duration_seconds": 2,
                    "composition": "竖屏中近景，以单一动作建立视觉钩子",
                    "action": story["hook_visual"],
                    "characters": characters,
                    "scene": scene,
                    "input_materials": [],
                    "caption": "",
                    "narrative_function": "0–3 秒视觉钩子",
                },
                {
                    "shot_id": "shot-02",
                    "duration_seconds": 2,
                    "composition": "关键信息与角色反应交替",
                    "action": story["inciting_incident"],
                    "characters": characters,
                    "scene": scene,
                    "input_materials": [],
                    "caption": "",
                    "narrative_function": "建立冲突",
                },
                {
                    "shot_id": "shot-03",
                    "duration_seconds": 2,
                    "composition": "连续动作推进冲突",
                    "action": "；".join(story["escalation"]),
                    "characters": characters,
                    "scene": scene,
                    "input_materials": [],
                    "caption": "",
                    "narrative_function": "冲突升级",
                },
                {
                    "shot_id": "shot-04",
                    "duration_seconds": 2,
                    "composition": "产品固定 plate 与角色动作分层合成",
                    "action": story["turn"],
                    "characters": characters,
                    "scene": scene,
                    "input_materials": [],
                    "caption": story["dialogue"][0],
                    "narrative_function": "产品介入与转折",
                },
                {
                    "shot_id": "shot-05",
                    "duration_seconds": 2,
                    "composition": "情绪结果后切固定产品收尾卡",
                    "action": story["ending"],
                    "characters": characters,
                    "scene": scene,
                    "input_materials": [],
                    "caption": story["dialogue"][0],
                    "narrative_function": "情绪收束与品牌识别",
                },
            ],
            "asset_roles": {},
            "packaging_strategy": "exact-main-composite",
            "continuity_rules": ["角色、服装、空间和产品包装在相邻镜头保持一致"],
            "provider_mapping": {
                "background": "image_provider_or_fixture",
                "character_motion": "video_provider_or_fixture",
                "product_plate": "local_material",
                "subtitles": "deterministic_compositor",
                "final": "compositor",
            },
            "retry_policy": {
                "max_retries_per_shot": 1,
                "fallback": "减少生成运动并保留产品 plate",
                "never_retry_by_redrawing_product": True,
            },
            "delivery_requirements": ["可播放 MP4", "保留镜头来源和结果 descriptor"],
        }
    if spec.name == "compliance-guard":
        return {
            "checks": [
                {
                    "name": "semantic_compliance_review",
                    "status": "PASS",
                    "detail": "离线 fixture 未发现暗示性高风险表述或敏感使用画面。",
                }
            ],
            "warnings": [],
            "blockers": [],
        }
    raise AssertionError(f"unexpected M12 skill in M11 fixture: {spec.name}")


@pytest.fixture(autouse=True)
def _configure_m12_offline_skill_runtime():
    from product_creative.runtime.business_skills import (
        configure_business_skill_executor,
        configure_business_skill_llm,
    )

    configure_business_skill_llm(None)
    configure_business_skill_executor(_m12_offline_skill_executor)
    try:
        yield
    finally:
        configure_business_skill_executor(None)


def _brief_payload() -> dict:
    return {
        "artifact_id": "brief-task-1",
        "task_id": "task-1",
        "product_id": "honeydew",
        "created_at": "2026-07-16T00:00:00+00:00",
        "source_refs": ["user-message:task-1"],
        "status": "READY",
        "original_message": "帮我做一个今天能发的产品视频",
        "interpreted_goal": "为周十五产品制作一条今日可发布的竖屏剧情短视频",
        "deliverables": ["video"],
        "channel": "douyin",
        "duration_seconds": 10,
        "aspect_ratio": "9:16",
        "constraints": ["使用当前确认主图"],
        "prohibited_requirements": ["不得编造产品功效"],
        "unknown_fields": [],
        "assumptions": ["低风险剧情细节由系统决定"],
        "autonomy_mode": "adaptive",
        "authorization_scope": {"data_sources": ["web", "xiaohongshu", "douyin"]},
    }


def _candidate_payload() -> dict:
    return {
        "artifact_id": "candidate-task-1-stable",
        "task_id": "task-1",
        "product_id": "honeydew",
        "created_at": "2026-07-16T00:00:00+00:00",
        "source_refs": ["insight:web-1", "material:main-1"],
        "status": "READY",
        "direction": "stable",
        "one_liner": "把产品作为化解出门前尴尬的小道具，自然进入轻喜剧情。",
        "stop_reason": "前三秒用即将迟到与临时状况制造反差。",
        "product_role": "剧情转折中的真实产品道具，不承担未经确认的功效承诺。",
        "target_emotion": "轻松、被理解",
        "channel_fit": "抖音竖屏短剧情",
        "hook": "0–3 秒：主角看表后突然停住，镜头切到包内的产品轮廓。",
        "conflict": "主角赶时间，但临时状况让她不敢出门。",
        "progression": ["看表", "犹豫", "找到产品", "重新从容"],
        "ending": "主角带着包出门，产品以固定包装 plate 收尾。",
        "required_materials": ["main-1"],
        "production_route": "exact-main-composite",
        "risks": ["避免医疗化和即时效果承诺"],
        "estimated_cost": "low",
        "feasibility": 0.92,
        "historical_difference": "从静态产品展示升级为有冲突和转折的轻剧情。",
    }


def _create_mature_product(tmp_path):
    from product_creative.capabilities.material.asset_service import register_material_asset
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import product_brains

    create_product("honeydew", "周十五蜂蜜露")
    current = product_brains().current("honeydew")
    state = deepcopy(current["state"])
    state["basic"] = {"sku": "周十五益生菌蜂蜜露 当前包装"}
    state["selling_points"] = ["便携", "外观可爱"]
    state["compliance"] = {
        "allowed_claims": ["便携", "外观可爱"],
        "forbidden_claims": ["治疗便秘", "孕妇绝对安全", "快速见效"],
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


def test_professional_artifact_seals_and_rejects_tampering():
    from product_creative.contracts.creative_artifacts import CreativeTaskBriefArtifact

    artifact = CreativeTaskBriefArtifact.model_validate(_brief_payload())
    dumped = artifact.model_dump(mode="json")

    assert artifact.schema_name == "product_creative.creative_task_brief.v1"
    assert artifact.schema_version == "1.0"
    assert len(artifact.content_hash) == 64
    assert CreativeTaskBriefArtifact.model_validate(dumped) == artifact

    tampered = deepcopy(dumped)
    tampered["interpreted_goal"] = "被篡改的目标"
    with pytest.raises(ValueError, match="content_hash"):
        CreativeTaskBriefArtifact.model_validate(tampered)


def test_creative_candidate_rejects_an_empty_generic_story():
    from product_creative.contracts.creative_artifacts import CreativeCandidateArtifact

    payload = _candidate_payload()
    payload["hook"] = ""

    with pytest.raises(ValueError):
        CreativeCandidateArtifact.model_validate(payload)


def test_all_eight_professional_artifact_contracts_round_trip():
    from product_creative.contracts.creative_artifacts import (
        CreativeCandidateArtifact,
        CreativeDecisionArtifact,
        CreativeTaskBriefArtifact,
        ProductGroundingPackArtifact,
        ProductionBibleArtifact,
        QaReportArtifact,
        ResearchInsightPackArtifact,
        StoryPackageArtifact,
        professional_artifact_model,
    )

    common = {
        "task_id": "task-1",
        "product_id": "honeydew",
        "created_at": "2026-07-16T00:00:00+00:00",
        "status": "READY",
    }
    artifacts = [
        CreativeTaskBriefArtifact.model_validate(_brief_payload()),
        ProductGroundingPackArtifact.model_validate(
            {
                **common,
                "artifact_id": "grounding-task-1",
                "source_refs": ["brain:version-1", "material:main-1"],
                "brain_version_id": "version-1",
                "brain_fingerprint": "a" * 64,
                "sku": {"status": "CONFIRMED", "value": "当前 SKU"},
                "packaging": {"status": "CONFIRMED", "material_id": "main-1"},
                "confirmed_claims": ["便携"],
                "forbidden_claims": ["治疗便秘"],
                "selected_materials": [{"material_id": "main-1", "role": "current_main_image"}],
                "field_evidence_refs": {"sku": ["brain:version-1"]},
                "blockers": [],
                "readiness_status": "READY",
            }
        ),
        ResearchInsightPackArtifact.model_validate(
            {
                **common,
                "artifact_id": "research-task-1",
                "source_refs": ["snapshot:web-1", "snapshot:xhs-1", "snapshot:douyin-1"],
                "research_goal": "寻找适合今日短视频的场景与前五秒结构",
                "data_sources": ["web", "xiaohongshu", "douyin"],
                "insights": [
                    {
                        "insight_id": "insight-1",
                        "source_type": "douyin",
                        "source_ref": "snapshot:douyin-1",
                        "summary": "先用临时状况制造悬念，再揭示随身物品。",
                        "published_at": "2026-07-15",
                        "confidence": 0.8,
                    }
                ],
                "degradation_notes": [],
                "not_product_fact": True,
            }
        ),
        CreativeCandidateArtifact.model_validate(_candidate_payload()),
        CreativeDecisionArtifact.model_validate(
            {
                **common,
                "artifact_id": "decision-task-1",
                "source_refs": [
                    "candidate-task-1-stable",
                    "candidate-task-1-variation",
                    "candidate-task-1-exploration",
                ],
                "candidate_ids": [
                    "candidate-task-1-stable",
                    "candidate-task-1-variation",
                    "candidate-task-1-exploration",
                ],
                "scores": [
                    {
                        "candidate_id": "candidate-task-1-stable",
                        "product_fit": 0.9,
                        "channel_fit": 0.9,
                        "freshness": 0.7,
                        "feasibility": 0.9,
                        "packaging_safety": 1.0,
                        "compliance_safety": 0.9,
                        "total": 0.88,
                    },
                    {
                        "candidate_id": "candidate-task-1-variation",
                        "product_fit": 0.8,
                        "channel_fit": 0.9,
                        "freshness": 0.8,
                        "feasibility": 0.7,
                        "packaging_safety": 0.9,
                        "compliance_safety": 0.9,
                        "total": 0.83,
                    },
                    {
                        "candidate_id": "candidate-task-1-exploration",
                        "product_fit": 0.7,
                        "channel_fit": 0.8,
                        "freshness": 0.95,
                        "feasibility": 0.6,
                        "packaging_safety": 0.8,
                        "compliance_safety": 0.8,
                        "total": 0.78,
                    },
                ],
                "selected_candidate_id": "candidate-task-1-stable",
                "selection_reason": "包装安全且能用具体冲突完成轻剧情。",
                "rejected_candidates": [
                    {"candidate_id": "candidate-task-1-variation", "reason": "制作复杂度更高"},
                    {"candidate_id": "candidate-task-1-exploration", "reason": "当前证据不足"},
                ],
                "preview_required": False,
                "allowed_deviation": ["对白措辞可微调"],
            }
        ),
        StoryPackageArtifact.model_validate(
            {
                **common,
                "artifact_id": "story-task-1",
                "source_refs": ["candidate-task-1-stable", "decision-task-1"],
                "premise": "赶时间的运营同事因临时尴尬停下脚步，随身产品成为恢复从容的剧情转折。",
                "characters": [{"name": "小周", "motivation": "准时出门且保持体面"}],
                "setting": "清晨卧室与玄关",
                "world_rules": ["现实轻喜剧", "不展示具体使用过程"],
                "hook_visual": "手机时间跳到 08:59，主角已经握住门把却突然停住。",
                "hook_audio": "急促提示音后瞬间静音。",
                "inciting_incident": "主角意识到临时状况让自己无法安心出门。",
                "conflict": "会议快开始，但她不愿在慌乱中处理尴尬。",
                "escalation": ["同事消息催促", "主角翻包寻找方案"],
                "turn": "包内可爱包装被发现，节奏从紧张转轻松。",
                "product_intervention": "产品只作为随身准备充分的象征出现。",
                "ending": "主角从容关门，固定包装 plate 与克制字幕收尾。",
                "dialogue": ["今天也要从容出门。"],
                "narrative_functions": ["钩子", "冲突", "转折", "产品露出", "收束"],
                "prohibited_content": ["医疗承诺", "使用部位展示", "包装重绘"],
            }
        ),
        ProductionBibleArtifact.model_validate(
            {
                **common,
                "artifact_id": "bible-task-1",
                "source_refs": ["story-task-1", "material:main-1"],
                "specification": {
                    "aspect_ratio": "9:16",
                    "duration_seconds": 10,
                    "language": "zh-CN",
                    "style": "现实轻喜剧",
                    "audio": "轻快节奏",
                },
                "shots": [
                    {
                        "shot_id": "shot-1",
                        "duration_seconds": 2,
                        "composition": "手机与门把手特写",
                        "action": "时间跳到 08:59，手停在门把上",
                        "characters": ["小周"],
                        "scene": "玄关",
                        "input_materials": [],
                        "caption": "",
                        "narrative_function": "钩子",
                    },
                    {
                        "shot_id": "shot-2",
                        "duration_seconds": 2,
                        "composition": "包内俯拍",
                        "action": "固定产品 plate 出现",
                        "characters": [],
                        "scene": "包内",
                        "input_materials": ["main-1"],
                        "caption": "准备好，出门更从容",
                        "narrative_function": "产品转折",
                    },
                ],
                "asset_roles": {
                    "main-1": "immutable_product_plate",
                    "generated_background": "background_only",
                },
                "packaging_strategy": "exact-main-composite",
                "continuity_rules": ["产品 plate 像素不变", "人物服装连续"],
                "provider_mapping": {"background": "image", "motion": "video", "final": "compositor"},
                "retry_policy": {"max_retries_per_shot": 1, "fallback": "static_motion"},
                "delivery_requirements": ["可播放 MP4", "保留来源与 payload"],
            }
        ),
        QaReportArtifact.model_validate(
            {
                **common,
                "artifact_id": "qa-task-1",
                "source_refs": ["grounding-task-1", "decision-task-1", "story-task-1", "bible-task-1"],
                "checks": [
                    {"name": "grounding_complete", "status": "PASS", "detail": "产品与包装已确认"},
                    {"name": "story_specific", "status": "PASS", "detail": "存在钩子、冲突与结尾"},
                ],
                "gate_result": "PASS",
                "blockers": [],
                "warnings": [],
                "evaluated_artifact_ids": [
                    "grounding-task-1",
                    "decision-task-1",
                    "story-task-1",
                    "bible-task-1",
                ],
            }
        ),
    ]

    assert len(artifacts) == 8
    for artifact in artifacts:
        model = professional_artifact_model(artifact.schema_name)
        assert model.model_validate(artifact.model_dump(mode="json")) == artifact


def test_professional_artifact_repository_writes_file_and_sqlite_index(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.contracts.creative_artifacts import CreativeTaskBriefArtifact
    from product_creative.ports.runtime_repositories import artifacts
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
        save_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        artifact = CreativeTaskBriefArtifact.model_validate(_brief_payload())
        path = save_professional_artifact(artifact)
        loaded = load_professional_artifact("honeydew", artifact.artifact_id)
        indexed = artifacts().get("honeydew", artifact.artifact_id)

    assert Path(path).is_file()
    assert loaded == artifact
    assert indexed["content_hash"] == artifact.content_hash


def test_old_creative_task_without_professional_artifacts_is_legacy_incomplete():
    from product_creative.contracts.models import (
        CreativeTaskPlan,
        CreativeTaskRecord,
        CreativeTaskRequest,
        ProductReadinessReport,
    )

    payload = {
        "task_id": "task-old",
        "product_id": "honeydew",
        "created_at": "2026-07-15T00:00:00+00:00",
        "updated_at": "2026-07-15T00:00:00+00:00",
        "status": "READY",
        "current_stage": "IDEATING",
        "request": CreativeTaskRequest(raw_message="做一个视频", deliverables=["video"]).model_dump(mode="json"),
        "readiness": ProductReadinessReport(
            readiness_id="readiness-old",
            task_id="task-old",
            product_id="honeydew",
            created_at="2026-07-15T00:00:00+00:00",
            deliverables=["video"],
            ready=True,
        ).model_dump(mode="json"),
        "plan": CreativeTaskPlan(task_id="task-old").model_dump(mode="json"),
    }

    task = CreativeTaskRecord.model_validate(payload)

    assert task.professional_artifact_status == "legacy_incomplete"
    assert task.professional_artifacts == {}


def test_new_blocked_video_task_still_persists_brief_and_grounding_without_inventing_claims(
    tmp_path,
):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import load_professional_artifact
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        before = product_brains().current("honeydew")
        task = start_creative_task(
            "honeydew",
            "帮我做一个今天能发的抖音产品视频，10秒竖屏，包装不能变化",
        )
        brief = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["creative_task_brief"],
        )
        grounding = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["product_grounding_pack"],
        )
        after = product_brains().current("honeydew")

    assert task.status == "NEEDS_INPUT"
    assert task.professional_artifact_status == "in_progress"
    assert brief.channel == "douyin"
    assert brief.duration_seconds == 10
    assert brief.aspect_ratio == "9:16"
    assert "不得编造产品事实或功效" in brief.prohibited_requirements
    assert grounding.readiness_status == "NEEDS_INPUT"
    assert grounding.confirmed_claims == []
    assert grounding.blockers
    assert before["content_hash"] == after["content_hash"]
    assert before["brain_version_id"] == after["brain_version_id"]


def test_grounding_pack_uses_only_confirmed_brain_and_current_material(tmp_path):
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import load_professional_artifact
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        material = _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前主图做一个10秒竖屏产品视频，包装不能变化",
            provider="mock-video",
        )
        grounding = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["product_grounding_pack"],
        )

    assert grounding.readiness_status == "READY"
    assert grounding.sku["status"] == "CONFIRMED"
    assert grounding.packaging["material_id"] == material["material_id"]
    assert grounding.confirmed_claims == ["便携", "外观可爱"]
    assert grounding.forbidden_claims == ["治疗便秘", "孕妇绝对安全", "快速见效"]
    assert grounding.brain_version_id
    assert len(grounding.brain_fingerprint) == 64


def test_research_pack_preserves_source_specific_insights_and_never_mutates_brain(
    tmp_path,
):
    from product_creative.common import write_json
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        ensure_research_insight_pack,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "帮我做一个今天能发的抖音产品视频，自动搜索最新灵感",
            provider="mock-video",
        )
        before = product_brains().current("honeydew")
        snapshot_dir = (
            tmp_path
            / ".hermes"
            / "product_creative"
            / "products"
            / "honeydew"
            / "artifacts"
            / "external_source_snapshots"
        )
        fixtures = [
            {
                "snapshot_id": "source-web-1",
                "provider": "web",
                "channel": "web",
                "created_at": task.created_at,
                "status": "completed",
                "not_product_fact": True,
                "items": [
                    {
                        "title": "今日出行场景趋势",
                        "text": "近期内容更偏向真实生活中的临时状况。",
                        "url": "https://example.test/web-1",
                        "published_at": "2026-07-16",
                    }
                ],
            },
            {
                "snapshot_id": "source-xhs-1",
                "provider": "xiaohongshu",
                "channel": "xiaohongshu",
                "created_at": task.created_at,
                "status": "completed",
                "not_product_fact": True,
                "items": [
                    {
                        "title": "出门前的尴尬瞬间",
                        "text": "消费者常用“包里备着更安心”描述随身准备。",
                        "url": "https://example.test/xhs-1",
                    }
                ],
            },
            {
                "snapshot_id": "source-douyin-1",
                "provider": "douyin",
                "channel": "douyin",
                "created_at": task.created_at,
                "status": "completed",
                "not_product_fact": True,
                "items": [
                    {
                        "title": "反差开场短视频",
                        "transcript": "已经要迟到了，她却在门口突然停下。",
                        "first5_analysis": {
                            "summary": "前五秒先用倒计时制造紧张，再用包内物品完成反转。"
                        },
                        "url": "https://example.test/douyin-1",
                    }
                ],
            },
        ]
        for snapshot in fixtures:
            write_json(snapshot_dir / f"{snapshot['snapshot_id']}.json", snapshot)

        pack = ensure_research_insight_pack(task)
        after = product_brains().current("honeydew")

    assert pack.not_product_fact is True
    assert {item.source_type for item in pack.insights} == {
        "web",
        "xiaohongshu",
        "douyin",
    }
    summaries = {item.source_type: item.summary for item in pack.insights}
    assert "事件/时效背景" in summaries["web"]
    assert "消费者语言/使用场景" in summaries["xiaohongshu"]
    assert "前5秒/口播结构" in summaries["douyin"]
    assert all(item.source_ref.startswith("snapshot:") for item in pack.insights)
    assert before["brain_version_id"] == after["brain_version_id"]
    assert before["content_hash"] == after["content_hash"]


def test_professional_creative_pack_has_three_distinct_directions_and_passes_preflight(
    tmp_path,
):
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        build_professional_creative_pack,
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        material = _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前主图做一个10秒竖屏抖音剧情短视频，包装不能变化",
            provider="mock-video",
        )
        pack = build_professional_creative_pack(task)
        candidates = [
            load_professional_artifact("honeydew", artifact_id)
            for artifact_id in task.professional_artifacts["creative_candidates"]
        ]
        decision = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["creative_decision"],
        )
        story = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["story_package"],
        )
        bible = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["production_bible"],
        )
        qa = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["qa_report"],
        )
        skill_executions = [
            load_professional_artifact("honeydew", artifact_id)
            for artifact_id in task.professional_artifacts["skill_executions"]
        ]
        from product_creative.runtime.creative_tasks import _offline_action_args

        exact_args = _offline_action_args(task, "compose_exact_main_video")

    assert [item.direction for item in candidates] == [
        "stable",
        "variation",
        "exploration",
    ]
    assert len({item.one_liner for item in candidates}) == 3
    assert len({item.hook for item in candidates}) == 3
    candidate_and_story_copy = " ".join(
        [
            *[item.model_dump_json() for item in candidates],
            story.model_dump_json(),
        ]
    )
    assert "更安心" not in candidate_and_story_copy
    assert "不尴尬" not in candidate_and_story_copy
    assert decision.selected_candidate_id in {item.artifact_id for item in candidates}
    assert len(decision.scores) == 3
    assert len(decision.rejected_candidates) == 2
    assert story.hook_visual
    assert story.conflict
    assert story.turn
    assert story.ending
    assert "从一个细节开始" not in story.model_dump_json()
    assert bible.packaging_strategy == "exact-main-composite"
    assert bible.asset_roles[material["material_id"]] == "immutable_product_plate"
    assert len(bible.shots) >= 4
    assert all(shot.narrative_function for shot in bible.shots)
    assert qa.gate_result == "PASS", qa.blockers
    assert [item.skill_name for item in skill_executions] == [
        "task-director",
        "research-director",
        "creative-strategy",
        "creative-review",
        "script-writer",
        "storyboard-director",
        "compliance-guard",
    ]
    assert [item.execution_mode for item in skill_executions] == [
        "deterministic",
        "deterministic",
        "fixture",
        "fixture",
        "fixture",
        "fixture",
        "fixture",
    ]
    assert exact_args["story_package_id"] == task.professional_artifacts["story_package"]
    assert (
        exact_args["production_bible_id"]
        == task.professional_artifacts["production_bible"]
    )
    assert pack["provider_ready"] is True
    assert task.professional_artifact_status == "complete"
    assert task.selected_idea["candidate_id"] == decision.selected_candidate_id


def test_creative_candidates_resume_from_saved_artifacts_without_reinvoking_llm(
    tmp_path,
):
    from product_creative.runtime.business_skills import (
        configure_business_skill_executor,
    )
    from product_creative.runtime.creative_direction import (
        ensure_creative_candidates,
    )
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前主图做一个10秒竖屏剧情视频，包装不能变化",
            provider="mock-video",
        )
        expected_ids = list(task.professional_artifacts["creative_candidates"])
        research = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["research_insight_pack"],
        )
        task.professional_artifacts.pop("creative_candidates")

        def no_strategy_retry(spec, input_payload, expected_output_schema):
            if spec.name == "creative-strategy":
                raise AssertionError("saved candidates must be reused")
            return _m12_offline_skill_executor(
                spec,
                input_payload,
                expected_output_schema,
            )

        configure_business_skill_executor(no_strategy_retry)
        try:
            resumed = ensure_creative_candidates(task, research)
        finally:
            configure_business_skill_executor(_m12_offline_skill_executor)

    assert [item.artifact_id for item in resumed] == expected_ids
    assert task.professional_artifacts["creative_candidates"] == expected_ids


def test_professional_stage_checkpoint_survives_later_skill_failure(tmp_path):
    from product_creative.runtime.business_skills import (
        configure_business_skill_executor,
    )
    from product_creative.runtime.creative_direction import (
        build_professional_creative_pack,
    )
    from product_creative.runtime.creative_tasks import (
        load_creative_task,
        start_creative_task,
    )
    from product_creative.runtime.professional_artifacts import (
        persist_professional_task_checkpoint,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前主图做一个10秒竖屏剧情视频，包装不能变化",
            provider="mock-video",
        )
        candidate_ids = list(task.professional_artifacts["creative_candidates"])
        for key in (
            "creative_candidates",
            "creative_decision",
            "story_package",
            "production_bible",
            "qa_report",
        ):
            task.professional_artifacts.pop(key, None)
        task.professional_artifacts["skill_executions"] = [
            artifact_id
            for artifact_id in task.professional_artifacts["skill_executions"]
            if "-creative_strategy-" not in artifact_id
            and "-creative_review-" not in artifact_id
            and "-script_writer-" not in artifact_id
            and "-storyboard-" not in artifact_id
            and "-compliance-" not in artifact_id
        ]
        persist_professional_task_checkpoint(task)

        def fail_after_candidates(spec, input_payload, expected_output_schema):
            if spec.name == "creative-review":
                raise ValueError("fixture decision validation failure")
            return _m12_offline_skill_executor(
                spec,
                input_payload,
                expected_output_schema,
            )

        configure_business_skill_executor(fail_after_candidates)
        try:
            with pytest.raises(ValueError, match="fixture decision validation failure"):
                build_professional_creative_pack(task)
        finally:
            configure_business_skill_executor(_m12_offline_skill_executor)
        persisted = load_creative_task("honeydew", task.task_id)

    assert persisted.professional_artifacts["creative_candidates"] == candidate_ids
    assert "creative_decision" not in persisted.professional_artifacts


def test_deterministic_claim_failure_overrides_a_semantic_compliance_pass(tmp_path):
    from product_creative.runtime.business_skills import configure_business_skill_executor
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import load_professional_artifact
    from product_creative.workspace import workspace_scope

    def executor(spec, input_payload, expected_output_schema):
        payload = _m12_offline_skill_executor(
            spec,
            input_payload,
            expected_output_schema,
        )
        if spec.name == "creative-strategy":
            payload["candidates"][0]["one_liner"] += " 并承诺治疗便秘。"
        return payload

    configure_business_skill_executor(executor)
    try:
        with workspace_scope(tmp_path):
            _create_mature_product(tmp_path)
            task = start_creative_task(
                "honeydew",
                "用当前主图做一个10秒竖屏剧情视频，包装不能变化",
                provider="mock-video",
            )
            qa = load_professional_artifact(
                "honeydew",
                task.professional_artifacts["qa_report"],
            )
    finally:
        configure_business_skill_executor(_m12_offline_skill_executor)

    claim_check = next(item for item in qa.checks if item.name == "claim_boundary_safe")
    semantic_check = next(
        item for item in qa.checks if item.name == "semantic_compliance_review"
    )
    assert claim_check.status == "FAIL"
    assert semantic_check.status == "PASS"
    assert qa.gate_result == "NEEDS_REVISION"


def test_semantic_compliance_guard_can_require_revision_when_hard_rules_pass(tmp_path):
    from product_creative.runtime.business_skills import configure_business_skill_executor
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import load_professional_artifact
    from product_creative.workspace import workspace_scope

    def executor(spec, input_payload, expected_output_schema):
        if spec.name == "compliance-guard":
            return {
                "checks": [
                    {
                        "name": "semantic_compliance_review",
                        "status": "FAIL",
                        "detail": "剧情语境暗示特定人群绝对安全，需要改写。",
                    }
                ],
                "warnings": [],
                "blockers": ["移除特定人群绝对安全的暗示。"],
            }
        return _m12_offline_skill_executor(
            spec,
            input_payload,
            expected_output_schema,
        )

    configure_business_skill_executor(executor)
    try:
        with workspace_scope(tmp_path):
            _create_mature_product(tmp_path)
            task = start_creative_task(
                "honeydew",
                "用当前主图做一个10秒竖屏剧情视频，包装不能变化",
                provider="mock-video",
            )
            qa = load_professional_artifact(
                "honeydew",
                task.professional_artifacts["qa_report"],
            )
    finally:
        configure_business_skill_executor(_m12_offline_skill_executor)

    assert qa.gate_result == "NEEDS_REVISION"
    assert "移除特定人群绝对安全的暗示。" in qa.blockers


def test_high_historical_similarity_without_a_novelty_strategy_requires_revision(
    tmp_path,
):
    from product_creative.runtime.business_skills import configure_business_skill_executor
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import load_professional_artifact
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        start_creative_task(
            "honeydew",
            "用当前主图做一个10秒竖屏剧情视频，包装不能变化",
            provider="mock-video",
        )

        def repeated_executor(spec, input_payload, expected_output_schema):
            payload = _m12_offline_skill_executor(
                spec,
                input_payload,
                expected_output_schema,
            )
            if spec.name == "creative-strategy":
                for candidate in payload["candidates"]:
                    candidate["novelty_strategy"] = ""
            return payload

        configure_business_skill_executor(repeated_executor)
        try:
            repeated = start_creative_task(
                "honeydew",
                "再做一个10秒竖屏剧情视频，包装不能变化",
                provider="mock-video",
            )
            candidates = [
                load_professional_artifact("honeydew", artifact_id)
                for artifact_id in repeated.professional_artifacts[
                    "creative_candidates"
                ]
            ]
            qa = load_professional_artifact(
                "honeydew",
                repeated.professional_artifacts["qa_report"],
            )
        finally:
            configure_business_skill_executor(_m12_offline_skill_executor)

    assert max(item.historical_similarity for item in candidates) >= 0.95
    novelty_check = next(item for item in qa.checks if item.name == "historical_novelty")
    assert novelty_check.status == "FAIL"
    assert qa.gate_result == "NEEDS_REVISION"


def test_preflight_blocks_when_grounding_is_not_ready_and_does_not_fabricate_later_artifacts(
    tmp_path,
):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        build_professional_creative_pack,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        task = start_creative_task(
            "honeydew",
            "帮我做一个10秒产品视频，包装不能变化",
            provider="mock-video",
        )
        pack = build_professional_creative_pack(task)

    assert pack["provider_ready"] is False
    assert pack["blocked_at"] == "product_grounding_pack"
    assert "creative_candidates" not in task.professional_artifacts
    assert "story_package" not in task.professional_artifacts
    assert "production_bible" not in task.professional_artifacts
    assert task.professional_artifact_status == "in_progress"


def test_adaptive_decision_uses_research_refs_and_preview_mode_requires_user_review(
    tmp_path,
):
    from product_creative.common import write_json
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        build_professional_creative_pack,
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "先给我看三个今天能发的抖音剧情方案，包装不能变化",
            provider="mock-video",
        )
        snapshot_path = (
            tmp_path
            / ".hermes"
            / "product_creative"
            / "products"
            / "honeydew"
            / "artifacts"
            / "external_source_snapshots"
            / "source-douyin-preview.json"
        )
        write_json(
            snapshot_path,
            {
                "snapshot_id": "source-douyin-preview",
                "provider": "douyin",
                "channel": "douyin",
                "created_at": task.created_at,
                "status": "completed",
                "not_product_fact": True,
                "items": [
                    {
                        "title": "倒计时反差开场",
                        "transcript": "她已经迟到，却突然在门口停住。",
                        "first5_analysis": {"summary": "倒计时后静音，制造突然停下的悬念。"},
                    }
                ],
            },
        )
        pack = build_professional_creative_pack(task)
        candidates = [
            load_professional_artifact("honeydew", artifact_id)
            for artifact_id in task.professional_artifacts["creative_candidates"]
        ]
        decision = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["creative_decision"],
        )

    assert pack["provider_ready"] is False
    assert pack["blocked_at"] == "creative_preview"
    assert decision.preview_required is True
    assert all(
        "snapshot:source-douyin-preview" in " ".join(candidate.source_refs)
        for candidate in candidates
    )
    assert "story_package" not in task.professional_artifacts


def test_preview_first_user_can_select_candidate_and_continue_same_task_without_provider(
    tmp_path,
    monkeypatch,
):
    from product_creative.runtime import creative_tasks
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    class FailIfCalled:
        calls = 0

        def dispatch(self, _envelope):
            self.calls += 1
            raise AssertionError("candidate selection must not dispatch a provider")

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="先给我看三个10秒竖屏抖音剧情视频方向，包装不能变化",
            provider="mock-video",
            autonomy_mode="adaptive",
        )
        assert started["task_status"] == "NEEDS_INPUT"
        assert "story_package" not in started["professional_artifacts"]

        fake_bus = FailIfCalled()
        monkeypatch.setattr(creative_tasks, "command_bus", lambda: fake_bus)
        selected = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="选择B方向，产品在第4秒左右出现",
        )
        decision = load_professional_artifact(
            "honeydew",
            selected["professional_artifacts"]["creative_decision"],
        )
        bible = load_professional_artifact(
            "honeydew",
            selected["professional_artifacts"]["production_bible"],
        )
        qa = load_professional_artifact(
            "honeydew",
            selected["professional_artifacts"]["qa_report"],
        )

    first_product_index = next(
        index
        for index, shot in enumerate(bible.shots)
        if shot.input_materials
    )
    assert fake_bus.calls == 0
    assert selected["task_id"] == started["task_id"]
    assert selected["task_status"] == "NEEDS_INPUT"
    assert selected["authorization_request"] == {}
    assert "ready for user production approval" in selected["blocked_reason"]
    assert decision.artifact_id.endswith("-r1")
    assert decision.selected_candidate_id.endswith("-variation")
    assert "story_package" in selected["professional_artifacts"]
    assert qa.gate_result == "PASS"
    assert sum(
        shot.duration_seconds
        for shot in bible.shots[:first_product_index]
    ) == 4.0


def test_m13_natural_language_preview_authorization_produces_real_local_video(
    tmp_path,
    monkeypatch,
):
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.runtime.creative_tasks import load_creative_task
    from product_creative.runtime.media_compositor import probe_media
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
        save_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    ffmpeg = _local_media_tool("ffmpeg")
    ffprobe = _local_media_tool("ffprobe")
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("local ffmpeg/ffprobe are required for M13 MP4 E2E")
    monkeypatch.setenv("PRODUCT_CREATIVE_FFMPEG_PATH", str(ffmpeg))
    monkeypatch.setenv("PRODUCT_CREATIVE_FFPROBE_PATH", str(ffprobe))
    monkeypatch.delenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", raising=False)

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        before = product_brains().current("honeydew")["content_hash"]
        started = product_agent_turn(
            product_id="honeydew",
            message="先给我看三个10秒竖屏剧情视频方向，包装和文字不能改变",
            provider="mock-video",
        )
        selected = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="选择B方向，产品在第4秒左右出现",
        )
        bible = load_professional_artifact(
            "honeydew",
            selected["professional_artifacts"]["production_bible"],
        )
        bible_payload = bible.model_dump(
            mode="json",
            exclude={"content_hash"},
        )
        bible_payload["specification"] = {
            **bible_payload["specification"],
            "canvas": [270, 480],
            "fps": 12,
        }
        save_professional_artifact(type(bible).model_validate(bible_payload))
        approved_direction = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认生产，就按这个生成",
        )
        authorization_request = approved_direction["authorization_request"]
        assert authorization_request["request_id"]
        assert approved_direction["task_status"] == "BLOCKED_AUTHORIZATION"
        assert approved_direction["professional_artifacts"]["media_execution_plan"]

        completed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认当前任务的本地 fixture 生成",
            authorization_id=authorization_request["request_id"],
            confirmed=True,
        )
        task = load_creative_task("honeydew", started["task_id"])
        after = product_brains().current("honeydew")["content_hash"]

        media_result = next(
            item
            for item in reversed(task.result_descriptors)
            if item.get("type") == "media_result"
        )
        video_path = (
            Path(task.artifact_path).parents[2]
            / media_result["path"]
        )
        media_probe = probe_media(video_path)

    assert selected["task_status"] == "NEEDS_INPUT"
    assert completed["task_status"] == "READY"
    assert completed["current_stage"] == "QUALITY_REVIEW"
    assert video_path.is_file()
    video_stream = next(
        stream
        for stream in media_probe["streams"]
        if stream["codec_type"] == "video"
    )
    audio_stream = next(
        stream
        for stream in media_probe["streams"]
        if stream["codec_type"] == "audio"
    )
    assert (video_stream["width"], video_stream["height"]) == (270, 480)
    assert video_stream["codec_name"] == "h264"
    assert audio_stream["codec_name"] == "aac"
    assert float(media_probe["format"]["duration"]) >= 9.5
    assert len(task.professional_artifacts["media_shot_results"]) >= 5
    assert task.professional_artifacts["media_composite_manifest"]
    assert before == after


def test_m13_natural_language_continue_retries_only_the_failed_shot(
    tmp_path,
    monkeypatch,
):
    import product_creative.provider_shots as provider_shots
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.runtime.creative_tasks import load_creative_task
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
        save_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    ffmpeg = _local_media_tool("ffmpeg")
    ffprobe = _local_media_tool("ffprobe")
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("local ffmpeg/ffprobe are required for M13 recovery E2E")
    monkeypatch.setenv("PRODUCT_CREATIVE_FFMPEG_PATH", str(ffmpeg))
    monkeypatch.setenv("PRODUCT_CREATIVE_FFPROBE_PATH", str(ffprobe))
    monkeypatch.delenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", raising=False)

    real_fixture = provider_shots._fixture_image
    calls: dict[str, int] = {}
    failed_once = False

    def fail_third_shot_once(product_root, payload):
        nonlocal failed_once
        shot_id = payload["source_shot_id"]
        calls[shot_id] = calls.get(shot_id, 0) + 1
        if shot_id == "shot-03" and not failed_once:
            failed_once = True
            raise RuntimeError("injected shot-03 fixture failure")
        return real_fixture(product_root, payload)

    monkeypatch.setattr(
        provider_shots,
        "_fixture_image",
        fail_third_shot_once,
    )

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="先给我看三个10秒竖屏剧情视频方向，包装和文字不能改变",
            provider="mock-video",
        )
        selected = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="选择B方向，产品在第4秒左右出现",
        )
        bible = load_professional_artifact(
            "honeydew",
            selected["professional_artifacts"]["production_bible"],
        )
        bible_payload = bible.model_dump(
            mode="json",
            exclude={"content_hash"},
        )
        bible_payload["specification"] = {
            **bible_payload["specification"],
            "canvas": [270, 480],
            "fps": 12,
        }
        save_professional_artifact(type(bible).model_validate(bible_payload))
        approved_direction = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认生产，就按这个生成",
        )
        failed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认当前任务的本地 fixture 生成",
            authorization_id=approved_direction["authorization_request"]["request_id"],
            confirmed=True,
        )
        calls_after_failure = dict(calls)

        completed = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="继续这个视频",
        )
        task = load_creative_task("honeydew", started["task_id"])

    assert failed["task_status"] == "FAILED_RETRYABLE"
    assert calls_after_failure == {
        "shot-01": 1,
        "shot-02": 1,
        "shot-03": 1,
    }
    assert completed["task_status"] == "READY"
    assert completed["current_stage"] == "QUALITY_REVIEW"
    assert calls["shot-01"] == 1
    assert calls["shot-02"] == 1
    assert calls["shot-03"] == 2
    assert calls["shot-04"] == 1
    assert calls["shot-05"] == 1
    assert task.professional_artifacts["media_composite_manifest"]


def test_m14_natural_language_continue_repairs_only_failed_black_shot(
    tmp_path,
    monkeypatch,
):
    from PIL import Image

    import product_creative.provider_shots as provider_shots
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.runtime.creative_tasks import load_creative_task
    from product_creative.runtime.media_qa import configure_media_qa_adapters
    from product_creative.runtime.media_review import record_media_qa_decision
    from product_creative.ports.runtime_repositories import (
        product_brains,
        recovery,
    )
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
        save_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    ffmpeg = _local_media_tool("ffmpeg")
    ffprobe = _local_media_tool("ffprobe")
    if not ffmpeg.is_file() or not ffprobe.is_file():
        pytest.skip("local ffmpeg/ffprobe are required for M14 repair E2E")
    monkeypatch.setenv("PRODUCT_CREATIVE_FFMPEG_PATH", str(ffmpeg))
    monkeypatch.setenv("PRODUCT_CREATIVE_FFPROBE_PATH", str(ffprobe))
    monkeypatch.delenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", raising=False)

    real_fixture = provider_shots._fixture_image
    calls: dict[str, int] = {}

    def black_third_shot_once(product_root, payload):
        shot_id = payload["source_shot_id"]
        calls[shot_id] = calls.get(shot_id, 0) + 1
        if shot_id != "shot-03":
            return real_fixture(product_root, payload)
        target = payload.get("target") or {}
        canvas = target.get("canvas") or [1080, 1920]
        output_dir = product_root / "artifacts" / "media_shot_sources"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{payload['payload_id']}.png"
        if calls[shot_id] > 1:
            output.unlink(missing_ok=True)
            return real_fixture(product_root, payload)
        Image.new(
            "RGB",
            (int(canvas[0]), int(canvas[1])),
            (0, 0, 0),
        ).save(output)
        return {
            "source_media": str(output.relative_to(product_root)),
            "content_hash": hashlib.sha256(output.read_bytes()).hexdigest(),
            "duration_seconds": 0,
        }

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

    monkeypatch.setattr(
        provider_shots,
        "_fixture_image",
        black_third_shot_once,
    )
    configure_media_qa_adapters(
        ocr_adapter=fixture_ocr,
        visual_adapter=fixture_visual,
    )
    try:
        with workspace_scope(tmp_path):
            _create_mature_product(tmp_path)
            started = product_agent_turn(
                product_id="honeydew",
                message="先给我看三个10秒竖屏剧情视频方向，包装和文字不能改变",
                provider="mock-video",
            )
            selected = product_agent_turn(
                product_id="honeydew",
                task_id=started["task_id"],
                message="选择B方向，产品在第4秒左右出现",
            )
            bible = load_professional_artifact(
                "honeydew",
                selected["professional_artifacts"]["production_bible"],
            )
            bible_payload = bible.model_dump(
                mode="json",
                exclude={"content_hash"},
            )
            bible_payload["specification"] = {
                **bible_payload["specification"],
                "canvas": [270, 480],
                "fps": 12,
            }
            save_professional_artifact(
                type(bible).model_validate(bible_payload)
            )
            approved = product_agent_turn(
                product_id="honeydew",
                task_id=started["task_id"],
                message="确认生产，就按这个生成",
            )
            first = product_agent_turn(
                product_id="honeydew",
                task_id=started["task_id"],
                message="确认当前任务的本地 fixture 生成",
                authorization_id=approved["authorization_request"]["request_id"],
                confirmed=True,
            )
            calls_after_first = dict(calls)
            repaired = product_agent_turn(
                product_id="honeydew",
                task_id=started["task_id"],
                message="继续修复这个视频",
            )
            task = load_creative_task("honeydew", started["task_id"])
            brain_before_reject = product_brains().current(
                "honeydew"
            )["content_hash"]
            qa_report_id = task.professional_artifacts["media_qa_report"]
            confirmation_id = recovery().request_confirmation(
                "honeydew",
                "product_media_qa_decide",
                qa_report_id,
                "medium",
                "trace-m14-user-reject",
            )
            record_media_qa_decision(
                "honeydew",
                qa_report_id=qa_report_id,
                decision="reject",
                reason="节奏仍然不够自然，这一版不要交付。",
                actor="fixture-user",
                confirmation_id=confirmation_id,
                trace_id="trace-m14-user-reject",
            )
            rejected_task = load_creative_task(
                "honeydew",
                started["task_id"],
            )
            brain_after_reject = product_brains().current(
                "honeydew"
            )["content_hash"]
    finally:
        configure_media_qa_adapters(
            ocr_adapter=None,
            visual_adapter=None,
        )

    assert first["current_stage"] == "QUALITY_REVIEW"
    assert first["professional_artifacts"]["media_repair_decision"]
    assert calls_after_first["shot-03"] == 1
    assert repaired["task_status"] == "AWAITING_FEEDBACK"
    assert calls["shot-01"] == 1
    assert calls["shot-02"] == 1
    assert calls["shot-03"] == 2
    assert calls["shot-04"] == 1
    assert calls["shot-05"] == 1
    assert len(task.professional_artifacts["media_qa_reports"]) == 2
    assert len(task.professional_artifacts["media_repair_decisions"]) == 1
    assert rejected_task.status == "FAILED_FINAL"
    assert any(
        item.get("type") == "media_qa_learning_evidence"
        and item.get("product_brain_writeback") is False
        for item in rejected_task.result_descriptors
    )
    assert brain_before_reject == brain_after_reject


def test_goal_planner_declares_professional_artifact_gates_for_video_tasks():
    from product_creative.application.planner import GoalPlanner
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message(
        "帮我做一个今天能发的抖音产品剧情视频，10秒竖屏，包装不能变化"
    )

    assert GoalPlanner().creative_task_gates(request) == [
        "creative_task_brief",
        "product_grounding_pack",
        "research_insight_pack",
        "creative_candidates",
        "creative_decision",
        "story_package",
        "production_bible",
        "preflight_qa",
    ]


@pytest.mark.parametrize(
    "message",
    [
        "包装外观和文字不得变化",
        "产品包装文字必须保持不变",
        "主图原样保留，不允许改动",
    ],
)
def test_natural_language_packaging_preservation_phrases_require_exact_route(message):
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message(
        f"用当前主图做一条10秒产品视频，{message}"
    )

    assert request.preserve_exact_packaging is True
    assert request.deliverables == ["video"]


@pytest.mark.parametrize(
    "message",
    [
        "请为这个产品生成一段文字内容",
        "请给我一些文字",
        "输出文字",
    ],
)
def test_explicit_text_request_is_still_classified_as_text_delivery(message):
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message(message)

    assert request.deliverables == ["text"]


def test_packaging_constraint_and_separate_text_request_keep_both_deliverables():
    from product_creative.contracts.models import CreativeTaskRequest

    request = CreativeTaskRequest.from_message(
        "做一条产品视频，包装文字保持不变，另外给我一段文字"
    )

    assert request.deliverables == ["text", "video"]
    assert request.preserve_exact_packaging is True


def test_packaging_wording_from_user_routes_full_pack_to_exact_main_composite(tmp_path):
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        material = _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前确认主图做一条10秒9:16抖音轻喜剧产品短视频，"
            "包装外观和文字不得变化",
            provider="mock-video",
        )
        bible = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["production_bible"],
        )
        qa = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["qa_report"],
        )

    assert task.request.preserve_exact_packaging is True
    assert bible.packaging_strategy == "exact-main-composite"
    assert bible.asset_roles[material["material_id"]] == "immutable_product_plate"
    assert qa.gate_result == "PASS"


def test_preflight_blocks_route_mismatch_even_if_request_flag_is_lost(tmp_path):
    from product_creative.contracts.creative_artifacts import ProductionBibleArtifact
    from product_creative.runtime.creative_direction import ensure_preflight_qa
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        material = _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前主图做一条10秒产品视频，包装外观和文字不得变化",
            provider="mock-video",
        )
        candidates = [
            load_professional_artifact("honeydew", artifact_id)
            for artifact_id in task.professional_artifacts["creative_candidates"]
        ]
        decision = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["creative_decision"],
        )
        story = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["story_package"],
        )
        original_bible = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["production_bible"],
        )
        unsafe_payload = original_bible.model_dump(mode="json")
        unsafe_payload["artifact_id"] = f"{original_bible.artifact_id}-unsafe"
        unsafe_payload["packaging_strategy"] = "reference-guided-generation"
        unsafe_payload["asset_roles"][material["material_id"]] = "product_reference"
        unsafe_payload["content_hash"] = ""
        unsafe_bible = ProductionBibleArtifact.model_validate(unsafe_payload)
        task.request.preserve_exact_packaging = False

        qa = ensure_preflight_qa(
            task,
            candidates,
            decision,
            story,
            unsafe_bible,
        )

    assert qa.gate_result == "BLOCKED"
    assert any(
        check.name == "packaging_route_safe" and check.status == "FAIL"
        for check in qa.checks
    )


def test_preflight_marks_revisable_story_failure_as_needs_revision(tmp_path):
    from product_creative.contracts.creative_artifacts import StoryPackageArtifact
    from product_creative.runtime.creative_direction import ensure_preflight_qa
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
        save_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "用当前主图做一条10秒产品视频，包装不能变化",
            provider="mock-video",
        )
        candidates = [
            load_professional_artifact("honeydew", artifact_id)
            for artifact_id in task.professional_artifacts["creative_candidates"]
        ]
        decision = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["creative_decision"],
        )
        original_story = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["story_package"],
        )
        bible = load_professional_artifact(
            "honeydew",
            task.professional_artifacts["production_bible"],
        )
        generic_payload = original_story.model_dump(mode="json")
        generic_payload["artifact_id"] = f"{original_story.artifact_id}-generic"
        generic_payload["hook_visual"] = "从一个细节开始"
        generic_payload["content_hash"] = ""
        generic_story = StoryPackageArtifact.model_validate(generic_payload)
        save_professional_artifact(generic_story)

        qa = ensure_preflight_qa(
            task,
            candidates,
            decision,
            generic_story,
            bible,
        )

    assert qa.status == "NEEDS_REVISION"
    assert qa.gate_result == "NEEDS_REVISION"
    assert any(
        check.name == "story_specific" and check.status == "FAIL"
        for check in qa.checks
    )


def test_mock_provider_dispatch_is_blocked_when_professional_qa_is_missing(
    tmp_path,
    monkeypatch,
):
    from product_creative.brain.discovery import assess_product_readiness
    from product_creative.common import now_iso
    from product_creative.contracts.models import (
        CreativeTaskPlan,
        CreativeTaskPlanStep,
        CreativeTaskRecord,
        CreativeTaskRequest,
    )
    from product_creative.runtime import creative_tasks
    from product_creative.workspace import workspace_scope

    class FailIfCalled:
        calls = 0

        def dispatch(self, _envelope):
            self.calls += 1
            raise AssertionError("provider command bus dispatch must remain at zero")

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        request = CreativeTaskRequest.from_message("帮我生成一个产品视频")
        readiness = assess_product_readiness(
            "honeydew",
            request,
            task_id="task-provider-gate",
        )
        now = now_iso()
        task = CreativeTaskRecord(
            task_id="task-provider-gate",
            product_id="honeydew",
            created_at=now,
            updated_at=now,
            status="READY",
            current_stage="GENERATING",
            request=request,
            readiness=readiness,
            plan=CreativeTaskPlan(
                task_id="task-provider-gate",
                stages=[
                    "UNDERSTANDING",
                    "GENERATING",
                    "DELIVERING",
                    "AWAITING_FEEDBACK",
                ],
                artifact_gates=[
                    "creative_task_brief",
                    "product_grounding_pack",
                    "research_insight_pack",
                    "creative_candidates",
                    "creative_decision",
                    "story_package",
                    "production_bible",
                    "preflight_qa",
                ],
                actions=[
                    CreativeTaskPlanStep(
                        stage="GENERATING",
                        action="submit_video_generation_task",
                        guard="task_authorization",
                    )
                ],
            ),
            authorization_id="authorization-should-not-be-read",
            provider="mock-video",
            professional_artifact_status="in_progress",
            professional_artifacts={},
        )
        fake_bus = FailIfCalled()
        monkeypatch.setattr(creative_tasks, "command_bus", lambda: fake_bus)

        updated = creative_tasks.execute_authorized_mock_generation(task)

    assert fake_bus.calls == 0
    assert updated.status == "BLOCKED_PRODUCT"
    assert "Preflight QA" in updated.blocked_reason


def test_video_provider_request_is_compiled_from_production_bible_not_raw_message():
    from product_creative.provider_payloads import (
        compile_video_request_from_production_bible,
    )

    legacy_request = {
        "prompt": "帮我随便做个视频",
        "base_prompt": "帮我随便做个视频",
        "aspect_ratio": "1:1",
        "duration_seconds": 6,
        "storyboard": [],
        "reference_assets": [{"asset_id": "main-1", "role": "current_main_image"}],
        "provider_request_draft": {
            "body": {
                "content": [{"type": "text", "text": "帮我随便做个视频"}],
                "ratio": "1:1",
                "duration": 6,
            }
        },
    }
    bible = {
        "artifact_id": "bible-task-1",
        "content_hash": "b" * 64,
        "specification": {
            "aspect_ratio": "9:16",
            "duration_seconds": 10,
            "style": "现实轻喜剧",
            "audio": "前半急促，转折后轻快",
        },
        "shots": [
            {
                "shot_id": "shot-01",
                "duration_seconds": 2,
                "composition": "手机时间与门把手特写",
                "action": "时间跳到08:59，手停在门把上",
                "characters": ["小周"],
                "scene": "玄关",
                "input_materials": [],
                "caption": "",
                "narrative_function": "视觉钩子",
            },
            {
                "shot_id": "shot-02",
                "duration_seconds": 3,
                "composition": "包内俯拍",
                "action": "固定产品主图出现，节奏转轻快",
                "characters": [],
                "scene": "随身包",
                "input_materials": ["main-1"],
                "caption": "准备好，再出发",
                "narrative_function": "产品转折",
            },
        ],
        "packaging_strategy": "exact-main-composite",
        "continuity_rules": ["产品主图像素不变", "字幕由后期确定性渲染"],
    }

    request = compile_video_request_from_production_bible(legacy_request, bible)

    assert request["compiled_from"] == "production_bible"
    assert request["source_production_bible_id"] == "bible-task-1"
    assert request["source_production_bible_hash"] == "b" * 64
    assert request["aspect_ratio"] == "9:16"
    assert request["duration_seconds"] == 10
    assert request["storyboard"][0]["description"] == "时间跳到08:59，手停在门把上"
    assert "手机时间与门把手特写" in request["prompt"]
    assert "准备好，再出发" in request["prompt"]
    assert "帮我随便做个视频" not in request["prompt"]
    assert (
        request["provider_request_draft"]["body"]["content"][0]["text"]
        == request["prompt"]
    )


def test_exact_main_story_layer_uses_story_and_bible_instead_of_generic_fallback():
    from product_creative.capabilities.video.exact_video_service import (
        story_claims_from_professional_artifacts,
    )

    story = {
        "premise": "赶时间的主角在出门前遇到临时状况，产品成为恢复从容的转折。",
        "hook_visual": "手机时间跳到08:59，握住门把的手突然停住。",
        "conflict": "会议已经开始，但主角不愿慌乱出门。",
        "product_intervention": "固定产品主图在翻包动作后出现。",
        "turn": "提示音从急促切为轻快节拍。",
        "ending": "主角关门出发，产品主图与克制字幕收尾。",
        "dialogue": ["今天也要准备好，再从容出发。"],
    }
    bible = {
        "shots": [
            {
                "shot_id": "shot-01",
                "duration_seconds": 2,
                "action": "时间跳到08:59，动作突然停住",
                "caption": "",
            },
            {
                "shot_id": "shot-02",
                "duration_seconds": 3,
                "action": "翻包后固定产品主图出现",
                "caption": "准备好，再出发",
            },
        ]
    }

    claims = story_claims_from_professional_artifacts(
        {"generation_safe": {"product_name": "周十五"}},
        story,
        bible,
    )

    assert claims["hook"] == story["hook_visual"]
    assert claims["need"] == story["conflict"]
    assert claims["intro"] == story["product_intervention"]
    assert claims["taste"] == story["turn"]
    assert claims["final_line"] == story["ending"]
    assert claims["badges"] == ["准备好，再出发"]
    assert "从一个细节开始" not in " ".join(
        str(value) for value in claims.values()
    )


def test_video_task_reaches_authorization_only_after_professional_pack_and_compiled_payload(
    tmp_path,
):
    from product_creative.ports.runtime_repositories import artifacts
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "帮我做一个10秒竖屏抖音剧情视频",
            provider="mock-video",
        )
        payload_result = next(
            item["output"]
            for item in task.result_descriptors
            if item.get("action") == "build_video_provider_payload"
        )
        payload = artifacts().get("honeydew", payload_result["payload_id"])

    assert task.status == "BLOCKED_AUTHORIZATION"
    assert task.professional_artifact_status == "complete"
    assert task.plan.artifact_gates[-1] == "preflight_qa"
    assert task.selected_idea["candidate_id"]
    assert payload["compiled_from"] == "production_bible"
    assert (
        payload["source_production_bible_id"]
        == task.professional_artifacts["production_bible"]
    )
    assert payload["request"]["storyboard"]
    assert payload["request"]["prompt"].startswith(
        "严格按以下 Production Bible 制作视频"
    )
    assert task.request.raw_message not in payload["request"]["prompt"]


def test_feedback_revision_preserves_original_pack_and_creates_new_decision_revision(
    tmp_path,
):
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        started = product_agent_turn(
            product_id="honeydew",
            message="帮我做一个10秒竖屏抖音剧情视频，产品在第6秒左右出现",
            provider="mock-video",
        )
        generated = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="确认本任务允许一次 mock 视频生成",
            confirmed=True,
            authorization_id=started["authorization_request"]["request_id"],
        )
        first_decision_id = generated["professional_artifacts"]["creative_decision"]
        first_decision = load_professional_artifact(
            "honeydew",
            first_decision_id,
        )
        revised = product_agent_turn(
            product_id="honeydew",
            task_id=started["task_id"],
            message="把剧情改成包内物件争抢最后一个位置的轻喜剧，产品在第4秒左右出现",
        )
        second_decision_id = revised["professional_artifacts"]["creative_decision"]
        preserved_first = load_professional_artifact(
            "honeydew",
            first_decision_id,
        )
        second_decision = load_professional_artifact(
            "honeydew",
            second_decision_id,
        )
        second_story = load_professional_artifact(
            "honeydew",
            revised["professional_artifacts"]["story_package"],
        )
        second_bible = load_professional_artifact(
            "honeydew",
            revised["professional_artifacts"]["production_bible"],
        )

    assert revised["task_id"] == started["task_id"]
    assert revised["interpreted_goal"] == started["interpreted_goal"]
    assert second_decision_id != first_decision_id
    assert "-r1" in second_decision_id
    assert preserved_first.content_hash == first_decision.content_hash
    assert second_decision.content_hash != first_decision.content_hash
    assert second_decision.selected_candidate_id.endswith("-variation")
    assert "最后一个位置" in " ".join(
        [
            second_story.premise,
            second_story.hook_visual,
            second_story.conflict,
            second_story.turn,
            second_story.ending,
        ]
    )
    assert any(
        item.get("type") == "task_revision"
        and item.get("original_goal_preserved") is True
        for item in revised["result_descriptors"]
    )
    product_shot_index = next(
        index
        for index, shot in enumerate(second_bible.shots)
        if shot.input_materials
    )
    product_reveal_seconds = sum(
        shot.duration_seconds
        for shot in second_bible.shots[:product_shot_index]
    )
    assert product_reveal_seconds == 4.0
    assert second_bible.specification["product_reveal_seconds"] == 4.0


def test_requested_product_reveal_time_becomes_the_actual_shot_boundary(tmp_path):
    from product_creative.runtime.agent import product_agent_turn
    from product_creative.runtime.professional_artifacts import (
        load_professional_artifact,
    )
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        result = product_agent_turn(
            product_id="honeydew",
            message="帮我做一个10秒竖屏抖音剧情视频，产品在第3秒左右出现",
            provider="mock-video",
        )
        bible = load_professional_artifact(
            "honeydew",
            result["professional_artifacts"]["production_bible"],
        )

    product_shot_index = next(
        index
        for index, shot in enumerate(bible.shots)
        if shot.input_materials
    )
    actual_reveal_seconds = sum(
        shot.duration_seconds
        for shot in bible.shots[:product_shot_index]
    )
    assert actual_reveal_seconds == 3.0
    assert bible.specification["requested_product_reveal_seconds"] == 3.0
    assert bible.specification["product_reveal_seconds"] == 3.0


def test_desktop_query_projection_exposes_professional_summary_and_full_artifacts(
    tmp_path,
):
    from product_creative.application.console_queries import (
        ProductCreativeConsoleQueries,
    )
    from product_creative.runtime.creative_tasks import start_creative_task
    from product_creative.workspace import workspace_scope

    with workspace_scope(tmp_path):
        _create_mature_product(tmp_path)
        task = start_creative_task(
            "honeydew",
            "帮我做一个10秒竖屏抖音剧情视频",
            provider="mock-video",
        )
        queries = ProductCreativeConsoleQueries()
        listed = queries.creative_tasks("honeydew")
        detail = queries.creative_task("honeydew", task.task_id)

    assert listed[0]["professional_summary"]["status"] == "complete"
    assert listed[0]["professional_summary"]["qa"]["gate_result"] == "PASS"
    assert (
        listed[0]["professional_summary"]["decision"]["selected_candidate_id"]
        == task.selected_idea["candidate_id"]
    )
    assert listed[0]["professional_summary"]["skills"]["latest_skill"] == "compliance-guard"
    assert len(listed[0]["professional_summary"]["skills"]["completed"]) == 7
    artifacts = detail["professional_artifact_details"]
    assert len(artifacts["creative_candidates"]) == 3
    assert artifacts["story_package"]["hook_visual"]
    assert len(artifacts["production_bible"]["shots"]) == 5
    assert artifacts["qa_report"]["gate_result"] == "PASS"


def test_real_hermes_agent_loop_builds_the_full_professional_pack_before_generation(
    tmp_path,
):
    from product_creative.capabilities.product.commands import command_descriptors
    from product_creative.runtime.creative_tasks import load_creative_task
    from product_creative.workspace import workspace_scope
    from run_agent import AIAgent
    from tools.registry import registry

    user_message = "用当前主图做一个10秒竖屏抖音剧情视频"
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
        id="call-product-workflow-m11",
        type="function",
        function=SimpleNamespace(
            name="product_workflow_run",
            arguments=json.dumps(
                {
                    "product_id": "honeydew",
                    "message": user_message,
                    "autonomy_mode": "adaptive",
                    "provider": "mock-video",
                },
                ensure_ascii=False,
            ),
        ),
    )
    responses = [
        response(tool_calls=[tool_call], finish_reason="tool_calls"),
        response("专业创意包已完成，真实生成仍在等待任务级授权。"),
    ]
    api_calls = []
    logging_patch = patch.dict(
        sys.modules,
        {
            "concurrent_log_handler": SimpleNamespace(
                ConcurrentRotatingFileHandler=RotatingFileHandler
            )
        },
    )
    logging_patch.start()

    try:
        with workspace_scope(tmp_path):
            _create_mature_product(tmp_path)
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
    assert len(api_calls) == 2
    assert tool_payload["task_status"] == "BLOCKED_AUTHORIZATION"
    assert tool_payload["professional_artifact_status"] == "complete"
    assert task.request.raw_message == user_message
    assert task.plan.artifact_gates[-1] == "preflight_qa"
    assert set(task.professional_artifacts) >= {
        "creative_task_brief",
        "product_grounding_pack",
        "research_insight_pack",
        "creative_candidates",
        "creative_decision",
        "story_package",
        "production_bible",
        "qa_report",
        "skill_executions",
    }
    assert len(task.professional_artifacts["skill_executions"]) == 7
