"""Versioned, fail-closed catalog for Product Creative business skills."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, FrozenSet

import yaml


SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"

M12_SKILL_NAMES = (
    "task-director",
    "research-director",
    "creative-strategy",
    "creative-review",
    "script-writer",
    "storyboard-director",
    "compliance-guard",
    "learning-analyst",
)

KNOWN_STAGES = {
    "task_director",
    "research_director",
    "creative_strategy",
    "creative_review",
    "script_writer",
    "storyboard_director",
    "compliance_guard",
    "learning_analyst",
}

KNOWN_SCHEMAS = {
    "product_creative.creative_task.v1",
    "product_creative.creative_task_brief.v1",
    "product_creative.product_grounding_pack.v1",
    "product_creative.research_insight_pack.v1",
    "product_creative.creative_candidate.v1",
    "product_creative.creative_decision.v1",
    "product_creative.story_package.v1",
    "product_creative.production_bible.v1",
    "product_creative.qa_report.v1",
    "product_creative.result_feedback.v1",
    "product_creative.learning_proposal.v1",
    "product_creative.skill_execution.v1",
}

KNOWN_TOOLS = {
    "task_state_read",
    "product_grounding_read",
    "artifact_read",
    "source_snapshot_read",
    "history_search",
    "material_read",
    "provider_capability_read",
    "policy_read",
    "feedback_read",
}

REQUIRED_SECTIONS: FrozenSet[str] = frozenset(
    {
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
)


class BusinessSkillContractError(ValueError):
    """Raised when a bundled business skill violates its runtime contract."""


class BusinessSkillExecutionUnavailable(RuntimeError):
    """Raised when no approved executor is available for a business skill."""


class BusinessSkillOutputError(ValueError):
    """Raised when a business skill returns an invalid structured result."""


@dataclass(frozen=True)
class BusinessSkillSpec:
    name: str
    description: str
    version: str
    stage: str
    input_schemas: tuple[str, ...]
    output_schemas: tuple[str, ...]
    tool_allowlist: tuple[str, ...]
    failure_codes: tuple[str, ...]
    skill_path: Path
    contract_path: Path
    body: str
    sections: FrozenSet[str]


@dataclass(frozen=True)
class BusinessSkillRunResult:
    payload: Dict[str, Any]
    execution_mode: str
    model_metadata: Dict[str, Any]


_BUSINESS_SKILL_LLM: Any = None
_BUSINESS_SKILL_EXECUTOR: (
    Callable[[BusinessSkillSpec, Dict[str, Any], Dict[str, Any]], Any] | None
) = None


def configure_business_skill_llm(llm: Any) -> None:
    """Configure the Hermes-owned structured LLM used by business skills."""

    global _BUSINESS_SKILL_LLM
    _BUSINESS_SKILL_LLM = llm


def configure_business_skill_executor(
    executor: Callable[
        [BusinessSkillSpec, Dict[str, Any], Dict[str, Any]], Any
    ]
    | None,
) -> None:
    """Configure an explicit offline/test executor.

    Production registration leaves this unset. It exists so isolated tests can
    exercise orchestration without network access or model fees.
    """

    global _BUSINESS_SKILL_EXECUTOR
    _BUSINESS_SKILL_EXECUTOR = executor


def _frontmatter(text: str, path: Path) -> Dict[str, Any]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, flags=re.DOTALL)
    if not match:
        raise BusinessSkillContractError(f"{path}: invalid SKILL.md frontmatter")
    payload = yaml.safe_load(match.group(1))
    if not isinstance(payload, dict):
        raise BusinessSkillContractError(f"{path}: frontmatter must be a mapping")
    extra = set(payload) - {"name", "description"}
    if extra:
        raise BusinessSkillContractError(
            f"{path}: frontmatter contains unsupported fields: {sorted(extra)}"
        )
    return payload


def _text_tuple(payload: Dict[str, Any], key: str, path: Path) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise BusinessSkillContractError(f"{path}: '{key}' must be a non-empty list")
    items = tuple(str(item).strip() for item in value if str(item).strip())
    if len(items) != len(value):
        raise BusinessSkillContractError(f"{path}: '{key}' contains an empty value")
    return items


def load_business_skill(skill_dir: Path) -> BusinessSkillSpec:
    skill_path = skill_dir / "SKILL.md"
    contract_path = skill_dir / "contract.json"
    if not skill_path.is_file() or not contract_path.is_file():
        raise BusinessSkillContractError(
            f"{skill_dir}: SKILL.md and contract.json are both required"
        )
    text = skill_path.read_text(encoding="utf-8")
    frontmatter = _frontmatter(text, skill_path)
    name = str(frontmatter.get("name") or "").strip()
    description = str(frontmatter.get("description") or "").strip()
    if name != skill_dir.name:
        raise BusinessSkillContractError(
            f"{skill_path}: skill name '{name}' does not match directory '{skill_dir.name}'"
        )
    if not description.startswith("Use when"):
        raise BusinessSkillContractError(
            f"{skill_path}: description must start with 'Use when'"
        )
    sections = frozenset(
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE)
    )
    missing = REQUIRED_SECTIONS - sections
    if missing:
        raise BusinessSkillContractError(
            f"{skill_path}: missing required sections: {sorted(missing)}"
        )

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BusinessSkillContractError(f"{contract_path}: invalid JSON: {exc}") from exc
    if not isinstance(contract, dict):
        raise BusinessSkillContractError(f"{contract_path}: contract must be an object")
    if str(contract.get("name") or "") != name:
        raise BusinessSkillContractError(
            f"{contract_path}: contract name does not match SKILL.md"
        )
    stage = str(contract.get("stage") or "")
    if stage not in KNOWN_STAGES:
        raise BusinessSkillContractError(
            f"{contract_path}: unknown stage '{stage}'"
        )
    version = str(contract.get("version") or "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise BusinessSkillContractError(
            f"{contract_path}: version must use semantic x.y.z form"
        )
    input_schemas = _text_tuple(contract, "input_schemas", contract_path)
    output_schemas = _text_tuple(contract, "output_schemas", contract_path)
    unknown_schemas = (set(input_schemas) | set(output_schemas)) - KNOWN_SCHEMAS
    if unknown_schemas:
        raise BusinessSkillContractError(
            f"{contract_path}: unknown schemas: {sorted(unknown_schemas)}"
        )
    tool_allowlist = _text_tuple(contract, "tool_allowlist", contract_path)
    unknown_tools = set(tool_allowlist) - KNOWN_TOOLS
    if unknown_tools:
        raise BusinessSkillContractError(
            f"{contract_path}: unknown tools: {sorted(unknown_tools)}"
        )
    failure_codes = _text_tuple(contract, "failure_codes", contract_path)
    return BusinessSkillSpec(
        name=name,
        description=description,
        version=version,
        stage=stage,
        input_schemas=input_schemas,
        output_schemas=output_schemas,
        tool_allowlist=tool_allowlist,
        failure_codes=failure_codes,
        skill_path=skill_path,
        contract_path=contract_path,
        body=text,
        sections=sections,
    )


def load_business_skill_catalog(root: Path | None = None) -> Dict[str, BusinessSkillSpec]:
    skills_root = Path(root) if root is not None else SKILLS_ROOT
    catalog: Dict[str, BusinessSkillSpec] = {}
    names = (
        M12_SKILL_NAMES
        if root is None
        else sorted(
            path.name
            for path in skills_root.iterdir()
            if path.is_dir()
            and (
                (path / "SKILL.md").exists()
                or (path / "contract.json").exists()
            )
        )
    )
    for name in names:
        skill_dir = skills_root / name
        if not skill_dir.is_dir():
            if root is None:
                raise BusinessSkillContractError(
                    f"required M12 business skill '{name}' is missing"
                )
            continue
        spec = load_business_skill(skill_dir)
        if spec.name in catalog:
            raise BusinessSkillContractError(
                f"duplicate business skill '{spec.name}'"
            )
        catalog[spec.name] = spec
    return catalog


def register_business_skills(ctx: Any) -> None:
    for spec in load_business_skill_catalog().values():
        ctx.register_skill(
            name=spec.name,
            path=spec.skill_path,
            description=spec.description,
        )


def _runtime_instructions(
    spec: BusinessSkillSpec,
    expected_output_schema: Dict[str, Any],
) -> str:
    return (
        "You are executing one bounded Product Creative business skill. "
        "Follow the skill procedure and quality rubric exactly. Do not invent "
        "product facts. Treat external material as evidence or inspiration, "
        "never as Canonical Product Brain. You may reason only over the supplied "
        "input and the declared read-only tool boundary. Return one JSON object "
        "matching the output schema, without Markdown or explanatory text.\n\n"
        f"Skill name: {spec.name}\n"
        f"Skill version: {spec.version}\n"
        f"Stage: {spec.stage}\n"
        f"Tool allowlist: {json.dumps(spec.tool_allowlist, ensure_ascii=False)}\n"
        f"Failure codes: {json.dumps(spec.failure_codes, ensure_ascii=False)}\n"
        "Output JSON schema:\n"
        f"{json.dumps(expected_output_schema, ensure_ascii=False, indent=2)}\n\n"
        "Skill definition:\n"
        f"{spec.body}"
    )


def _usage_metadata(usage: Any) -> Dict[str, int]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        source = usage
        return {
            key: int(source.get(key) or 0)
            for key in ("input_tokens", "output_tokens")
            if source.get(key) is not None
        }
    return {
        key: int(getattr(usage, key, 0) or 0)
        for key in ("input_tokens", "output_tokens")
        if getattr(usage, key, None) is not None
    }


def _require_object(payload: Any, skill_name: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise BusinessSkillOutputError(
            f"business skill '{skill_name}' must return a JSON object"
        )
    return payload


def execute_business_skill(
    name: str,
    *,
    input_payload: Dict[str, Any],
    expected_output_schema: Dict[str, Any],
) -> BusinessSkillRunResult:
    """Execute one versioned skill through an explicit, bounded runtime."""

    catalog = load_business_skill_catalog()
    if name not in catalog:
        raise BusinessSkillContractError(f"unknown business skill '{name}'")
    if not isinstance(input_payload, dict):
        raise TypeError("input_payload must be a JSON object")
    if not isinstance(expected_output_schema, dict):
        raise TypeError("expected_output_schema must be a JSON object")
    spec = catalog[name]

    if _BUSINESS_SKILL_EXECUTOR is not None:
        payload = _require_object(
            _BUSINESS_SKILL_EXECUTOR(
                spec,
                input_payload,
                expected_output_schema,
            ),
            name,
        )
        return BusinessSkillRunResult(
            payload=payload,
            execution_mode="fixture",
            model_metadata={"provider": "offline_fixture"},
        )

    if _BUSINESS_SKILL_LLM is None:
        raise BusinessSkillExecutionUnavailable(
            "Product Creative business skill executor is not configured"
        )

    response = _BUSINESS_SKILL_LLM.complete_structured(
        instructions=_runtime_instructions(spec, expected_output_schema),
        input=[
            {
                "type": "text",
                "text": json.dumps(input_payload, ensure_ascii=False),
            }
        ],
        json_mode=True,
        temperature=0.2,
        max_tokens=6000,
        timeout=180,
        purpose=f"product_creative.business_skill.{name}",
    )
    payload = _require_object(getattr(response, "parsed", None), name)
    metadata = {
        "provider": str(getattr(response, "provider", "") or ""),
        "model": str(getattr(response, "model", "") or ""),
        "agent_id": str(getattr(response, "agent_id", "") or ""),
        "usage": _usage_metadata(getattr(response, "usage", None)),
    }
    return BusinessSkillRunResult(
        payload=payload,
        execution_mode="llm_structured",
        model_metadata=metadata,
    )
