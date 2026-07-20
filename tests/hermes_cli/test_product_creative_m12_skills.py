from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENT = ROOT / ".hermes" / "plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))


EXPECTED_SKILLS = {
    "task-director",
    "research-director",
    "creative-strategy",
    "creative-review",
    "script-writer",
    "storyboard-director",
    "compliance-guard",
    "learning-analyst",
}

REQUIRED_SECTIONS = {
    "When to Use",
    "Inputs",
    "Procedure",
    "Output Contract",
    "Tool Boundary",
    "Failure Conditions",
    "Quality Rubric",
    "Positive Examples",
    "Negative Examples",
    "Verification",
}


def test_business_skill_catalog_loads_the_eight_m12_skills():
    from product_creative.runtime.business_skills import load_business_skill_catalog

    catalog = load_business_skill_catalog()

    assert set(catalog) == EXPECTED_SKILLS
    for name, spec in catalog.items():
        assert spec.name == name
        assert spec.version == "1.0.0"
        assert spec.skill_path.name == "SKILL.md"
        assert spec.contract_path.name == "contract.json"
        assert spec.input_schemas
        assert spec.output_schemas
        assert spec.tool_allowlist
        assert spec.failure_codes
        assert REQUIRED_SECTIONS.issubset(spec.sections)


def test_business_skill_catalog_rejects_an_unknown_stage(tmp_path):
    from product_creative.runtime.business_skills import BusinessSkillContractError
    from product_creative.runtime.business_skills import load_business_skill_catalog

    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: bad-skill\n"
        "description: Use when exercising an invalid catalog fixture.\n"
        "---\n\n"
        + "\n\n".join(f"## {section}\nFixture." for section in sorted(REQUIRED_SECTIONS)),
        encoding="utf-8",
    )
    (skill_dir / "contract.json").write_text(
        json.dumps(
            {
                "name": "bad-skill",
                "version": "1.0.0",
                "stage": "unknown_stage",
                "input_schemas": ["product_creative.creative_task_brief.v1"],
                "output_schemas": ["product_creative.creative_task_brief.v1"],
                "tool_allowlist": ["artifact_read"],
                "failure_codes": ["invalid"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BusinessSkillContractError, match="unknown stage"):
        load_business_skill_catalog(tmp_path)


def test_business_skill_catalog_rejects_missing_required_sections(tmp_path):
    from product_creative.runtime.business_skills import BusinessSkillContractError
    from product_creative.runtime.business_skills import load_business_skill_catalog

    skill_dir = tmp_path / "incomplete-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: incomplete-skill\n"
        "description: Use when exercising an incomplete catalog fixture.\n"
        "---\n\n"
        "# Incomplete\n\n## When to Use\nFixture.\n",
        encoding="utf-8",
    )
    (skill_dir / "contract.json").write_text(
        json.dumps(
            {
                "name": "incomplete-skill",
                "version": "1.0.0",
                "stage": "task_director",
                "input_schemas": ["product_creative.creative_task.v1"],
                "output_schemas": ["product_creative.creative_task_brief.v1"],
                "tool_allowlist": ["task_state_read"],
                "failure_codes": ["invalid"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BusinessSkillContractError, match="missing required sections"):
        load_business_skill_catalog(tmp_path)


def test_register_business_skills_exposes_qualified_plugin_skills():
    from product_creative.runtime.business_skills import register_business_skills

    registered = {}

    class Context:
        def register_skill(self, name, path, description=""):
            registered[name] = {
                "path": Path(path),
                "description": description,
            }

    register_business_skills(Context())

    assert set(registered) == EXPECTED_SKILLS
    assert all(item["path"].exists() for item in registered.values())
    assert all(item["description"].startswith("Use when") for item in registered.values())


def test_plugin_registers_operator_and_all_business_skills(monkeypatch):
    import product_creative

    registered = {}

    class Context:
        llm = SimpleNamespace()

        def register_skill(self, name, path, description=""):
            registered[name] = Path(path)

        def register_cli_command(self, **_kwargs):
            return None

    monkeypatch.setattr(product_creative, "register_tools", lambda _ctx: None)
    monkeypatch.setattr(product_creative, "configure_generator_llm", lambda _llm: None)
    monkeypatch.setattr(product_creative, "configure_inspiration_llm", lambda _llm: None)
    monkeypatch.setattr(product_creative, "configure_self_iteration_llm", lambda _llm: None)
    monkeypatch.setattr(product_creative, "configure_decision_llm", lambda _llm: None)

    product_creative.register(Context())

    assert set(registered) == EXPECTED_SKILLS | {"product-creative-operator"}


def _skill_execution_payload() -> dict:
    return {
        "artifact_id": "skill-exec-task-1-creative-strategy-r0",
        "task_id": "task-1",
        "product_id": "honeydew",
        "created_at": "2026-07-16T00:00:00+00:00",
        "source_refs": ["grounding-task-1", "research-task-1"],
        "status": "PASS",
        "skill_name": "creative-strategy",
        "skill_version": "1.0.0",
        "stage": "creative_strategy",
        "execution_mode": "fixture",
        "input_artifacts": [
            {
                "artifact_id": "grounding-task-1",
                "content_hash": "a" * 64,
            },
            {
                "artifact_id": "research-task-1",
                "content_hash": "b" * 64,
            },
        ],
        "output_artifacts": [
            {
                "artifact_id": "candidate-task-1-stable",
                "content_hash": "c" * 64,
            }
        ],
        "allowed_tools": ["artifact_read", "history_search", "material_read"],
        "actual_actions": ["artifact_read", "history_search"],
        "model_metadata": {
            "provider": "fixture",
            "model": "m12-offline-fixture",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
        "started_at": "2026-07-16T00:00:00+00:00",
        "finished_at": "2026-07-16T00:00:01+00:00",
        "execution_status": "COMPLETED",
        "failure_code": "",
        "failure_detail": "",
    }


def test_skill_execution_artifact_is_immutable_and_tamper_evident():
    from product_creative.contracts.creative_artifacts import (
        BusinessSkillExecutionArtifact,
    )

    execution = BusinessSkillExecutionArtifact.model_validate(
        _skill_execution_payload()
    )
    dumped = execution.model_dump(mode="json")

    assert execution.schema_name == "product_creative.skill_execution.v1"
    assert len(execution.content_hash) == 64
    assert execution.actual_actions == ["artifact_read", "history_search"]

    dumped["skill_version"] = "9.9.9"
    with pytest.raises(ValueError, match="content_hash"):
        BusinessSkillExecutionArtifact.model_validate(dumped)


def test_skill_execution_rejects_actions_outside_the_allowlist():
    from product_creative.contracts.creative_artifacts import (
        BusinessSkillExecutionArtifact,
    )

    payload = _skill_execution_payload()
    payload["actual_actions"] = ["artifact_read", "provider_submit"]

    with pytest.raises(ValueError, match="outside the Skill allowlist"):
        BusinessSkillExecutionArtifact.model_validate(payload)


@pytest.mark.parametrize(
    "secret_field",
    ["api_key", "token", "cookie", "authorization"],
)
def test_skill_execution_rejects_sensitive_model_metadata(secret_field):
    from product_creative.contracts.creative_artifacts import (
        BusinessSkillExecutionArtifact,
    )

    payload = _skill_execution_payload()
    payload["model_metadata"][secret_field] = "must-not-persist"

    with pytest.raises(ValueError, match="sensitive"):
        BusinessSkillExecutionArtifact.model_validate(payload)


def test_skill_execution_failure_cannot_claim_output_artifacts():
    from product_creative.contracts.creative_artifacts import (
        BusinessSkillExecutionArtifact,
    )

    payload = _skill_execution_payload()
    payload["status"] = "BLOCKED"
    payload["execution_status"] = "FAILED"
    payload["failure_code"] = "invalid_skill_output"
    payload["failure_detail"] = "Structured output failed schema validation."

    with pytest.raises(ValueError, match="failed execution cannot claim outputs"):
        BusinessSkillExecutionArtifact.model_validate(payload)


@pytest.mark.parametrize(
    ("source_type", "item", "expected_kind", "required_features"),
    [
        (
            "web",
            {
                "title": "暑期通勤内容升温",
                "text": "近期公开内容更关注临时出行准备。",
                "published_at": "2026-07-16",
                "url": "https://example.test/web-1",
            },
            "dated_context",
            {"dated_context", "event_or_trend"},
        ),
        (
            "xiaohongshu",
            {
                "title": "出门前包里会放什么",
                "text": "用户常说“包里提前备着，出门更从容”。",
                "stats": {"liked": 120, "collected": 40, "comments": 18},
                "url": "https://example.test/xhs-1",
            },
            "consumer_scene",
            {
                "title_structure",
                "consumer_language",
                "emotion",
                "life_scene",
                "comment_concern",
            },
        ),
        (
            "douyin",
            {
                "title": "最后一秒突然停住",
                "transcript": "已经迟到了，她却突然退回门口。",
                "copy_analysis": {
                    "opening_hook": "已经迟到了，她却突然退回门口",
                    "replicable_formula": "时间压力 + 动作中断 + 物品反转",
                },
                "first5_analysis": {
                    "analysis": {
                        "visual_hook": "手机倒计时后手停在门把上",
                        "spoken_hook": "已经迟到了",
                        "pacing": "前两秒快，第三秒突然静音",
                        "conflict": "必须出门但突然停住",
                        "turn": "包内物品完成反转",
                        "audio": "倒计时提示音后静音",
                    }
                },
                "url": "https://example.test/douyin-1",
            },
            "short_video_hook",
            {
                "visual_hook_0_5s",
                "spoken_hook",
                "pacing",
                "conflict",
                "turn",
                "audio_or_cta",
            },
        ),
        (
            "historical",
            {
                "title": "旧版静态产品展示",
                "text": "主图居中，通用字幕依次出现，用户评价剧情空洞。",
                "result_status": "rejected",
            },
            "historical_pattern",
            {"repetition_pattern", "outcome_signal", "reusable_asset"},
        ),
    ],
)
def test_research_director_builds_source_specific_insight(
    source_type,
    item,
    expected_kind,
    required_features,
):
    from product_creative.runtime.professional_artifacts import (
        research_insight_from_item,
    )

    insight = research_insight_from_item(
        task_id="task-1",
        snapshot_id=f"source-{source_type}-1",
        item_index=1,
        source_type=source_type,
        item=item,
    )

    assert insight["source_type"] == source_type
    assert insight["insight_kind"] == expected_kind
    assert insight["observation"]
    assert insight["why_it_matters"]
    assert insight["adaptation_rule"]
    assert insight["creative_use"]
    assert insight["avoid_copying"]
    assert required_features.issubset(insight["source_features"])
    assert insight["source_ref"] == f"snapshot:source-{source_type}-1#item:1"


def _similarity_candidate(**overrides):
    payload = {
        "artifact_id": "candidate-old",
        "hook": "手机倒计时后，手停在门把上，提示音突然静音。",
        "conflict": "主角必须马上出门，却因为临时状况突然停住。",
        "progression": ["倒计时催促", "门口停住", "翻包寻找", "产品出现", "恢复从容"],
        "product_role": "产品作为随身准备的真实道具完成剧情转折。",
        "ending": "主角关门出发，产品固定画面克制收尾。",
        "production_route": "exact-main-composite",
    }
    payload.update(overrides)
    return payload


def test_historical_similarity_is_high_for_the_same_story_structure():
    from product_creative.runtime.creative_direction import (
        historical_similarity_against,
    )

    current = _similarity_candidate(artifact_id="candidate-current")
    old = _similarity_candidate()

    result = historical_similarity_against(current, [old])

    assert result["score"] >= 0.95
    assert result["similar_artifact_ids"] == ["candidate-old"]


def test_historical_similarity_detects_adjective_only_variation():
    from product_creative.runtime.creative_direction import (
        historical_similarity_against,
    )

    current = _similarity_candidate(
        artifact_id="candidate-current",
        hook="手机快速倒计时后，手忽然停在门把上，提示音瞬间静音。",
        conflict="主角必须立刻出门，却因为突发的小状况停住。",
        ending="主角轻松关门出发，产品固定画面温柔收尾。",
    )

    result = historical_similarity_against(current, [_similarity_candidate()])

    assert result["score"] >= 0.75


def test_historical_similarity_drops_for_a_different_mechanism():
    from product_creative.runtime.creative_direction import (
        historical_similarity_against,
    )

    current = _similarity_candidate(
        artifact_id="candidate-current",
        hook="包内俯拍，钥匙和耳机争抢最后一个位置。",
        conflict="包里只剩一个位置，拟人化物件争论谁应该被带走。",
        progression=["物件争位", "轮流陈述", "主角犹豫", "产品入场", "全员让位"],
        product_role="产品用可爱包装和便携体量赢得包内位置。",
        ending="拉链合上，所有物件安静，主角拎包出门。",
    )

    result = historical_similarity_against(current, [_similarity_candidate()])

    assert result["score"] <= 0.6


def test_business_skill_runtime_uses_structured_host_llm():
    from product_creative.runtime.business_skills import (
        configure_business_skill_executor,
        configure_business_skill_llm,
        execute_business_skill,
    )

    calls = []

    class Result:
        parsed = {"candidates": [{"direction": "stable"}]}
        provider = "deepseek"
        model = "deepseek-chat"
        agent_id = "host-agent"
        usage = SimpleNamespace(input_tokens=123, output_tokens=45)

    class Llm:
        def complete_structured(self, **kwargs):
            calls.append(kwargs)
            return Result()

    configure_business_skill_executor(None)
    configure_business_skill_llm(Llm())
    try:
        result = execute_business_skill(
            "creative-strategy",
            input_payload={"task_id": "task-1", "grounding": {"status": "READY"}},
            expected_output_schema={
                "type": "object",
                "properties": {"candidates": {"type": "array"}},
                "required": ["candidates"],
            },
        )
    finally:
        configure_business_skill_llm(None)

    assert result.payload == Result.parsed
    assert result.execution_mode == "llm_structured"
    assert result.model_metadata["provider"] == "deepseek"
    assert "Creative Strategy" in calls[0]["instructions"]
    assert "Tool allowlist" in calls[0]["instructions"]
    assert calls[0]["json_mode"] is True


def test_business_skill_runtime_supports_an_offline_fixture_executor():
    from product_creative.runtime.business_skills import (
        configure_business_skill_executor,
        execute_business_skill,
    )

    captured = {}

    def fixture(spec, input_payload, expected_output_schema):
        captured["name"] = spec.name
        captured["input"] = input_payload
        captured["schema"] = expected_output_schema
        return {"decision": {"selected_candidate_id": "candidate-b"}}

    configure_business_skill_executor(fixture)
    try:
        result = execute_business_skill(
            "creative-review",
            input_payload={"candidate_ids": ["a", "b", "c"]},
            expected_output_schema={"type": "object"},
        )
    finally:
        configure_business_skill_executor(None)

    assert result.execution_mode == "fixture"
    assert captured["name"] == "creative-review"
    assert result.payload["decision"]["selected_candidate_id"] == "candidate-b"


def test_creative_strategy_schema_fully_describes_each_candidate():
    from product_creative.runtime.creative_direction import (
        _creative_candidate_output_schema,
    )

    schema = _creative_candidate_output_schema()
    candidates = schema["properties"]["candidates"]
    item = candidates["items"]

    assert candidates["minItems"] == 3
    assert candidates["maxItems"] == 3
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {
        "direction",
        "one_liner",
        "stop_reason",
        "product_role",
        "target_emotion",
        "channel_fit",
        "hook",
        "conflict",
        "progression",
        "ending",
        "required_materials",
        "production_route",
        "risks",
        "estimated_cost",
        "feasibility",
        "historical_difference",
        "novelty_strategy",
    }
    assert item["properties"]["direction"]["enum"] == [
        "stable",
        "variation",
        "exploration",
    ]
    assert item["properties"]["progression"] == {
        "type": "array",
        "minItems": 2,
        "items": {"type": "string", "minLength": 1},
    }
    assert item["properties"]["feasibility"] == {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
    }


def test_creative_decision_schema_requires_three_scores_and_two_rejections():
    from product_creative.runtime.creative_direction import (
        _creative_decision_output_schema,
    )

    candidate_ids = ["candidate-a", "candidate-b", "candidate-c"]
    schema = _creative_decision_output_schema(candidate_ids)
    scores = schema["properties"]["scores"]
    rejections = schema["properties"]["rejected_candidates"]

    assert scores["type"] == "array"
    assert scores["minItems"] == 3
    assert scores["maxItems"] == 3
    assert scores["items"]["properties"]["candidate_id"]["enum"] == candidate_ids
    assert set(scores["items"]["required"]) == {
        "candidate_id",
        "product_fit",
        "channel_fit",
        "freshness",
        "feasibility",
        "packaging_safety",
        "compliance_safety",
        "total",
    }
    assert rejections["type"] == "array"
    assert rejections["minItems"] == 2
    assert rejections["maxItems"] == 2
    assert schema["properties"]["selected_candidate_id"]["enum"] == candidate_ids


def test_story_storyboard_and_compliance_schemas_define_nested_types():
    from product_creative.runtime.creative_direction import (
        _compliance_output_schema,
        _story_package_output_schema,
        _storyboard_output_schema,
    )

    story = _story_package_output_schema()
    storyboard = _storyboard_output_schema()
    compliance = _compliance_output_schema()

    assert story["properties"]["characters"]["items"]["required"] == [
        "name",
        "motivation",
    ]
    assert story["properties"]["narrative_functions"]["minItems"] == 4
    assert storyboard["properties"]["shots"]["minItems"] == 5
    assert storyboard["properties"]["shots"]["maxItems"] == 5
    assert storyboard["properties"]["shots"]["items"]["required"] == [
        "composition",
        "action",
        "characters",
        "scene",
        "caption",
        "narrative_function",
    ]
    assert compliance["properties"]["checks"]["items"]["properties"]["status"][
        "enum"
    ] == ["PASS", "WARN", "FAIL"]
    assert compliance["properties"]["warnings"]["items"]["type"] == "string"
    assert compliance["properties"]["blockers"]["items"]["type"] == "string"


def test_business_skill_runtime_blocks_when_no_executor_is_available():
    from product_creative.runtime.business_skills import (
        BusinessSkillExecutionUnavailable,
        configure_business_skill_executor,
        configure_business_skill_llm,
        execute_business_skill,
    )

    configure_business_skill_executor(None)
    configure_business_skill_llm(None)

    with pytest.raises(BusinessSkillExecutionUnavailable, match="not configured"):
        execute_business_skill(
            "script-writer",
            input_payload={"candidate": {}},
            expected_output_schema={"type": "object"},
        )


def test_business_skill_runtime_rejects_non_object_output():
    from product_creative.runtime.business_skills import (
        BusinessSkillOutputError,
        configure_business_skill_executor,
        execute_business_skill,
    )

    configure_business_skill_executor(lambda *_args: ["not", "an", "object"])
    try:
        with pytest.raises(BusinessSkillOutputError, match="JSON object"):
            execute_business_skill(
                "storyboard-director",
                input_payload={"story": {}},
                expected_output_schema={"type": "object"},
            )
    finally:
        configure_business_skill_executor(None)


def test_completed_business_skill_execution_is_saved_with_input_and_output_hashes(
    monkeypatch,
):
    from product_creative.runtime.business_skills import BusinessSkillRunResult
    from product_creative.runtime import professional_artifacts

    saved = []
    monkeypatch.setattr(
        professional_artifacts,
        "save_professional_artifact",
        lambda artifact: saved.append(artifact) or artifact.artifact_id,
    )
    task = SimpleNamespace(
        task_id="task-1",
        product_id="honeydew",
        revision_messages=[],
        professional_artifacts={},
    )
    input_artifact = SimpleNamespace(
        artifact_id="grounding-task-1",
        content_hash="a" * 64,
    )
    output_artifact = SimpleNamespace(
        artifact_id="candidate-task-1-stable",
        content_hash="b" * 64,
    )

    execution = professional_artifacts.record_business_skill_execution(
        task,
        skill_name="creative-strategy",
        run_result=BusinessSkillRunResult(
            payload={"candidates": []},
            execution_mode="llm_structured",
            model_metadata={
                "provider": "deepseek",
                "model": "deepseek-chat",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
        ),
        input_artifacts=[input_artifact],
        output_artifacts=[output_artifact],
        actual_actions=["artifact_read"],
    )

    assert saved == [execution]
    assert execution.skill_name == "creative-strategy"
    assert execution.skill_version == "1.0.0"
    assert execution.input_artifacts[0].content_hash == "a" * 64
    assert execution.output_artifacts[0].content_hash == "b" * 64
    assert execution.allowed_tools == ["artifact_read", "history_search", "material_read"]
    assert task.professional_artifacts["skill_executions"] == [execution.artifact_id]


def test_learning_evaluation_prompt_uses_the_versioned_learning_analyst_skill():
    from product_creative.capabilities.learning.result_evaluation_service import (
        _evaluation_instructions,
    )

    instructions = _evaluation_instructions()

    assert "learning-analyst v1.0.0" in instructions
    assert "# Learning Analyst" in instructions
    assert "Canonical Product Brain" in instructions


def test_failed_business_skill_execution_never_claims_outputs(monkeypatch):
    from product_creative.runtime import professional_artifacts

    saved = []
    monkeypatch.setattr(
        professional_artifacts,
        "save_professional_artifact",
        lambda artifact: saved.append(artifact) or artifact.artifact_id,
    )
    task = SimpleNamespace(
        task_id="task-1",
        product_id="honeydew",
        revision_messages=[],
        professional_artifacts={},
    )
    input_artifact = SimpleNamespace(
        artifact_id="grounding-task-1",
        content_hash="a" * 64,
    )

    execution = professional_artifacts.record_failed_business_skill_execution(
        task,
        skill_name="creative-strategy",
        input_artifacts=[input_artifact],
        actual_actions=["artifact_read"],
        error=RuntimeError("fixture model unavailable"),
    )

    assert saved == [execution]
    assert execution.execution_status == "FAILED"
    assert execution.output_artifacts == []
    assert execution.failure_code == "runtime_execution_failed"
    assert "fixture model unavailable" in execution.failure_detail
