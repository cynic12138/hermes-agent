"""Generated result learning evaluation service."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state
from ...brain.rules import create_rule_candidates_for_evaluation
from ..learning.feedback_repository import read_result_feedback_entries

from ..review.result_shared import _brief_context, _list, _rel, _resolve_result_path, _text

RESULT_EVALUATION_SCHEMA_VERSION = "product_creative.result_evaluation.v7.4"

_LLM: Any = None

def configure_llm(llm: Any) -> None:
    global _LLM
    _LLM = llm

def _read_feedback_entries(base: Path) -> List[Dict[str, Any]]:
    return read_result_feedback_entries(base)

def _resolve_feedback(base: Path, feedback: str, result_id: str) -> Dict[str, Any]:
    if feedback:
        candidate = Path(feedback)
        if candidate.exists():
            resolved = candidate.resolve()
            if base.resolve() == resolved or base.resolve() in resolved.parents:
                return read_json(resolved, {})
        path = base / "artifacts" / "result_feedback" / (feedback if feedback.endswith(".json") else f"{feedback}.json")
        if path.exists():
            return read_json(path, {})
    matches = [
        item for item in _read_feedback_entries(base)
        if item.get("source_result_id") == result_id
    ]
    return matches[-1] if matches else {}

def _parse_json_text(value: str) -> Dict[str, Any]:
    text = value.strip()
    if not text:
        return {}
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}

def _evaluation_instructions() -> str:
    from ...runtime.business_skills import load_business_skill_catalog

    skill = load_business_skill_catalog()["learning-analyst"]
    return f"""
你是 Product Creative 的结果评审智能体。你的任务不是夸赞生成结果，而是判断真实图片/视频结果是否应该影响 Product Brain。

输出 JSON，字段必须包含：
- summary: 一句话总结结果是否适合当前产品。
- strengths: 数组，最多 5 条。
- weaknesses: 数组，最多 5 条。
- proposed_updates: 数组，每项包含 path、value、update_type、target_page、target_section、risk_level。
- requires_human_review: 必须为 true。

规则：
- 只允许从真实 result、source prompt、Product State、用户反馈中总结规律。
- 不允许把外部灵感、URL、文件名当成产品事实。
- 图像规律写入 learning.image_generation_preferences。
- 视频规律写入 learning.video_script_preferences。
- 成功规律可写入 learning.successful_patterns。
- 失败规律写入 learning.failed_patterns。
- 不确定或可能改变定位的内容 risk_level 设为 medium 或 high。

以下是本次必须遵守的版本化业务 Skill（{skill.name} v{skill.version}）：

{skill.body}
"""

def _fallback_updates(result: Dict[str, Any], feedback: Dict[str, Any]) -> List[Dict[str, Any]]:
    result_id = _text(result.get("result_id"))
    brief_type = _text(result.get("brief_type")) or "generation"
    preference_path = "learning.video_script_preferences" if brief_type == "video" else "learning.image_generation_preferences"
    target_page = "content-patterns/video-patterns.md" if brief_type == "video" else "content-patterns/visual-patterns.md"
    updates: List[Dict[str, Any]] = []
    note = _text(feedback.get("note"))
    rating = feedback.get("rating")
    if note:
        updates.append(
            {
                "path": preference_path,
                "value": f"{brief_type} result {result_id} feedback: {note}",
                "update_type": "result_preference",
                "target_page": target_page,
                "target_section": "Confirmed Learning",
                "risk_level": "medium",
            }
        )
    for item in _list(feedback.get("like_reasons")):
        updates.append(
            {
                "path": "learning.successful_patterns",
                "value": f"{brief_type} result {result_id} liked: {item}",
                "update_type": "successful_pattern",
                "target_page": "content-patterns/proven-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    for item in _list(feedback.get("dislike_reasons")) + _list(feedback.get("issues")):
        updates.append(
            {
                "path": "learning.failed_patterns",
                "value": f"{brief_type} result {result_id} avoid: {item}",
                "update_type": "failed_pattern",
                "target_page": "content-patterns/failed-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    scores = feedback.get("quality_scores") if isinstance(feedback.get("quality_scores"), dict) else {}
    for key, value in scores.items():
        if value is not None and int(value) <= 2:
            updates.append(
                {
                    "path": "learning.failed_patterns",
                    "value": f"{brief_type} result {result_id} low {key}: {value}/5",
                    "update_type": "failed_pattern",
                    "target_page": "content-patterns/failed-patterns.md",
                    "target_section": "Confirmed Learning",
                    "risk_level": "low",
                }
            )
    if rating and int(rating) >= 4 and feedback.get("selected"):
        updates.append(
            {
                "path": "learning.successful_patterns",
                "value": f"Selected {brief_type} result {result_id} scored {rating}/5.",
                "update_type": "successful_pattern",
                "target_page": "content-patterns/proven-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    return updates

def _fallback_evaluation(result: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "summary": "基于结构化用户反馈生成的结果评估，等待人工确认后才可沉淀。",
        "strengths": _list(feedback.get("like_reasons"))[:5],
        "weaknesses": (_list(feedback.get("dislike_reasons")) + _list(feedback.get("issues")))[:5],
        "proposed_updates": _fallback_updates(result, feedback),
        "requires_human_review": True,
    }

def _llm_evaluate(base: Path, result: Dict[str, Any], feedback: Dict[str, Any], provider: str, model: str) -> Dict[str, Any]:
    if os.environ.get("PRODUCT_CREATIVE_ENABLE_LLM") != "1" or os.environ.get("PRODUCT_CREATIVE_DISABLE_LLM") == "1" or _LLM is None:
        return {}
    state = apply_generation_safe_state(read_product_state(base))
    brief_context = _brief_context(base, result)
    payload = {
        "product_state": state.get("generation_safe", {}),
        "result": {
            "result_id": result.get("result_id"),
            "brief_type": result.get("brief_type"),
            "status": result.get("status"),
            "provider": result.get("provider"),
            "summary": result.get("summary"),
            "outputs": result.get("outputs", []),
        },
        "source_prompt": brief_context.get("prompt", ""),
        "feedback": feedback,
    }
    input_text = json.dumps(payload, ensure_ascii=False)
    try:
        response = _LLM.complete_structured(
            instructions=_evaluation_instructions(),
            input=[{"type": "text", "text": input_text}],
            json_mode=True,
            temperature=0.1,
            max_tokens=2500,
            timeout=180,
            provider=_text(provider) or None,
            model=_text(model) or None,
            purpose="product_creative.result_evaluation",
        )
        parsed = response.parsed if isinstance(response.parsed, dict) else _parse_json_text(response.text)
        parsed["llm"] = {
            "call_mode": "structured_json_mode",
            "provider": getattr(response, "provider", ""),
            "model": getattr(response, "model", ""),
            "content_type": getattr(response, "content_type", ""),
        }
        return parsed
    except Exception:
        response = _LLM.complete(
            messages=[
                {"role": "system", "content": _evaluation_instructions()},
                {"role": "user", "content": input_text},
            ],
            temperature=0.1,
            max_tokens=2500,
            timeout=180,
            provider=_text(provider) or None,
            model=_text(model) or None,
            purpose="product_creative.result_evaluation.text_json_fallback",
        )
        parsed = _parse_json_text(response.text)
        parsed["llm"] = {
            "call_mode": "text_json_fallback",
            "provider": getattr(response, "provider", ""),
            "model": getattr(response, "model", ""),
            "content_type": "json_text_fallback",
        }
        return parsed

def _normal_updates(items: Any, result: Dict[str, Any]) -> List[Dict[str, Any]]:
    brief_type = _text(result.get("brief_type")) or "generation"
    default_path = "learning.video_script_preferences" if brief_type == "video" else "learning.image_generation_preferences"
    default_page = "content-patterns/video-patterns.md" if brief_type == "video" else "content-patterns/visual-patterns.md"
    allowed_paths = {
        "learning.image_generation_preferences",
        "learning.video_script_preferences",
        "learning.successful_patterns",
        "learning.failed_patterns",
        "learning.feedback_preferences",
    }
    updates: List[Dict[str, Any]] = []
    for item in _list(items):
        if not isinstance(item, dict):
            continue
        value = _text(item.get("value"))
        if not value:
            continue
        path = _text(item.get("path")) or default_path
        path = re.sub(r"\[\d+\]$", "", path)
        if path not in allowed_paths:
            path = default_path
        updates.append(
            {
                "path": path,
                "value": value[:500],
                "update_type": _text(item.get("update_type")) or "result_preference",
                "target_page": _text(item.get("target_page")) or default_page,
                "target_section": _text(item.get("target_section")) or "Confirmed Learning",
                "risk_level": _text(item.get("risk_level")) or "medium",
            }
        )
    return updates

def _evaluation_markdown(evaluation: Dict[str, Any]) -> str:
    lines = [
        f"# {evaluation['result_evaluation_id']}",
        "",
        f"Result: {evaluation['source_result_id']}",
        f"Feedback: {evaluation.get('source_feedback_id', '')}",
        f"Status: {evaluation['status']}",
        f"LLM mode: {(evaluation.get('llm') or {}).get('call_mode', 'rule_fallback')}",
        "",
        "## Summary",
        "",
        evaluation.get("summary", ""),
        "",
        "## Strengths",
        "",
    ]
    lines.extend([f"- {item}" for item in evaluation.get("strengths", [])] or ["- None"])
    lines.extend(["", "## Weaknesses", ""])
    lines.extend([f"- {item}" for item in evaluation.get("weaknesses", [])] or ["- None"])
    lines.extend(["", "## Proposed Updates", ""])
    lines.extend([f"- `{item.get('path')}`: {item.get('value')}" for item in evaluation.get("proposed_updates", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def create_result_evaluation(
    product_id: str,
    result: str,
    feedback: str = "",
    provider: str = "",
    model: str = "",
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    result_path = _resolve_result_path(base, result)
    result_payload = read_json(result_path, {})
    result_id = _text(result_payload.get("result_id")) or result_path.stem
    feedback_payload = _resolve_feedback(base, feedback, result_id)
    parsed = _llm_evaluate(base, result_payload, feedback_payload, provider, model)
    if not parsed:
        parsed = _fallback_evaluation(result_payload, feedback_payload)
        parsed["llm"] = {"call_mode": "rule_fallback", "provider": "", "model": ""}
    proposed_updates = _normal_updates(parsed.get("proposed_updates"), result_payload)
    if not proposed_updates:
        fallback = _fallback_evaluation(result_payload, feedback_payload)
        proposed_updates = _normal_updates(fallback.get("proposed_updates"), result_payload)
        parsed.setdefault("summary", fallback.get("summary", ""))
        parsed.setdefault("strengths", fallback.get("strengths", []))
        parsed.setdefault("weaknesses", fallback.get("weaknesses", []))
        parsed.setdefault("llm", {})["fallback_reason"] = "llm_returned_no_actionable_updates"
    evaluation_id = f"result-evaluation-{timestamp()}"
    evaluation = {
        "schema_version": RESULT_EVALUATION_SCHEMA_VERSION,
        "result_evaluation_id": evaluation_id,
        "evaluation_id": evaluation_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "review_required",
        "mutates_product_brain": False,
        "requires_human_review": True,
        "source_result_id": result_id,
        "source_result_path": _rel(base, result_path),
        "source_feedback_id": feedback_payload.get("feedback_id", ""),
        "source_feedback_path": feedback_payload.get("feedback_path", ""),
        "summary": _text(parsed.get("summary")),
        "strengths": [str(item) for item in _list(parsed.get("strengths")) if str(item).strip()][:5],
        "weaknesses": [str(item) for item in _list(parsed.get("weaknesses")) if str(item).strip()][:5],
        "proposed_updates": proposed_updates,
        "llm": parsed.get("llm") if isinstance(parsed.get("llm"), dict) else {"call_mode": "unknown"},
    }
    rule_candidates = create_rule_candidates_for_evaluation(base, evaluation)
    evaluation["rule_candidate_ids"] = [item.rule_id for item in rule_candidates]
    evaluation["rule_candidate_count"] = len(rule_candidates)
    out_dir = base / "artifacts" / "result_evaluations"
    json_path = out_dir / f"{evaluation_id}.json"
    md_path = out_dir / f"{evaluation_id}.md"
    write_json(json_path, evaluation)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_evaluation_markdown(evaluation), encoding="utf-8")
    append_jsonl(
        base / "structured" / "result_evaluation_index.jsonl",
        {
            "result_evaluation_id": evaluation_id,
            "created_at": evaluation["created_at"],
            "source_result_id": result_id,
            "source_feedback_id": evaluation["source_feedback_id"],
            "proposed_update_count": len(proposed_updates),
            "rule_candidate_count": len(rule_candidates),
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "result-evaluation", evaluation_id, [str(json_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "result_evaluation_id": evaluation_id,
        "proposed_update_count": len(proposed_updates),
        "rule_candidate_count": len(rule_candidates),
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "evaluation": evaluation,
    }
