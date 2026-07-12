"""Review and evaluation capability actions."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .task_overview_service import create_task_overview_package
from ..learning.result_evaluation_service import create_result_evaluation
from .result_review_service import create_result_review_package
from ..execution_helpers import text
from ..models import ActionRuntimeDefinition


def _review_result(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_result_review_package(text(args.get("product_id")), text(args.get("result_id")))


def _evaluate_result(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_result_evaluation(
        text(args.get("product_id")), text(args.get("result_id")), text(args.get("feedback_id")),
        text(args.get("provider")), text(args.get("model")),
    )


def _task_overview(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_task_overview_package(
        text(args.get("product_id")), text(args.get("result_id")),
        text(args.get("workflow_run_id")), text(args.get("title")),
    )


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("review_generated_result", _review_result, auto_advance=True),
        ActionRuntimeDefinition("evaluate_generated_result", _evaluate_result, auto_advance=True),
        ActionRuntimeDefinition("create_task_overview_package", _task_overview),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
