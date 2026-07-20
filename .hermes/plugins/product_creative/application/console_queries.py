"""Application query boundary for the M9 review console."""

from __future__ import annotations

from typing import Any, Dict, List

from ..ports.runtime_repositories import artifacts, console_reader


def _artifact_details(product_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    pointers = (
        task.get("professional_artifacts")
        if isinstance(task.get("professional_artifacts"), dict)
        else {}
    )
    for key, value in pointers.items():
        if isinstance(value, list):
            details[key] = [
                payload
                for artifact_id in value
                if (payload := artifacts().get(product_id, str(artifact_id)))
            ]
        elif value:
            payload = artifacts().get(product_id, str(value))
            if payload:
                details[key] = payload
    return details


def _professional_summary(
    task: Dict[str, Any],
    details: Dict[str, Any],
) -> Dict[str, Any]:
    grounding = details.get("product_grounding_pack") or {}
    decision = details.get("creative_decision") or {}
    qa = details.get("qa_report") or {}
    dependency = details.get("media_dependency_report") or {}
    media_plan = details.get("media_execution_plan") or {}
    shot_results = details.get("media_shot_results") or []
    manifest = details.get("media_composite_manifest") or {}
    media_qa = details.get("media_qa_report") or {}
    repair = details.get("media_repair_decision") or {}
    human_override = details.get("media_human_override") or {}
    failed_shots = [
        item
        for item in shot_results
        if item.get("execution_status")
        in {"FAILED_RETRYABLE", "FAILED_FINAL"}
    ]
    completed_shots = {
        str(item.get("shot_id") or "")
        for item in shot_results
        if item.get("execution_status") == "COMPLETED"
    }
    executions = details.get("skill_executions") or []
    latest_execution = executions[-1] if executions else {}
    return {
        "status": task.get("professional_artifact_status", "legacy_incomplete"),
        "grounding": {
            "readiness_status": grounding.get("readiness_status", ""),
            "blockers": grounding.get("blockers", []),
            "sku": grounding.get("sku", {}),
            "packaging": grounding.get("packaging", {}),
        },
        "decision": {
            "selected_candidate_id": decision.get("selected_candidate_id", ""),
            "selection_reason": decision.get("selection_reason", ""),
            "preview_required": decision.get("preview_required", False),
        },
        "qa": {
            "gate_result": qa.get("gate_result", ""),
            "blockers": qa.get("blockers", []),
            "warnings": qa.get("warnings", []),
        },
        "skills": {
            "latest_stage": latest_execution.get("stage", ""),
            "latest_skill": latest_execution.get("skill_name", ""),
            "latest_version": latest_execution.get("skill_version", ""),
            "completed": [
                {
                    "name": item.get("skill_name", ""),
                    "version": item.get("skill_version", ""),
                    "stage": item.get("stage", ""),
                    "status": item.get("execution_status", ""),
                }
                for item in executions
            ],
        },
        "media": {
            "dependency_status": dependency.get("overall_status", ""),
            "dependency_blockers": dependency.get("blockers", []),
            "dependency_warnings": dependency.get("warnings", []),
            "plan_id": media_plan.get("artifact_id", ""),
            "shots_completed": len(completed_shots),
            "shots_total": len(media_plan.get("shots") or []),
            "current_failure": (
                failed_shots[-1].get("error_detail", "")
                if failed_shots
                else ""
            ),
            "product_plate_id": (
                details.get("product_plate") or {}
            ).get("artifact_id", ""),
            "composite_manifest_id": manifest.get("artifact_id", ""),
            "output_relative_path": manifest.get("output_relative_path", ""),
            "qa_report_id": media_qa.get("artifact_id", ""),
            "qa_result": media_qa.get("overall_result", ""),
            "qa_failed_shot_ids": media_qa.get("failed_shot_ids", []),
            "qa_hard_blockers": media_qa.get("hard_blockers", []),
            "qa_warnings": media_qa.get("warnings", []),
            "repair_decision_id": repair.get("artifact_id", ""),
            "repair_decision": repair.get("decision", ""),
            "repair_round": repair.get("repair_round", 0),
            "human_override_id": human_override.get("artifact_id", ""),
            "human_decision": human_override.get("decision", ""),
        },
    }


class ProductCreativeConsoleQueries:
    def products(self) -> List[Dict[str, Any]]:
        return console_reader().products()

    def snapshot(self, product_id: str) -> Dict[str, Any]:
        return console_reader().snapshot(product_id)

    def workflows(self, product_id: str) -> List[Dict[str, Any]]:
        return console_reader().workflows(product_id)

    def creative_tasks(self, product_id: str) -> List[Dict[str, Any]]:
        tasks = console_reader().creative_tasks(product_id)
        for task in tasks:
            details = _artifact_details(product_id, task)
            task["professional_summary"] = _professional_summary(task, details)
        return tasks

    def creative_task(self, product_id: str, task_id: str) -> Dict[str, Any]:
        task = console_reader().creative_task(product_id, task_id)
        if not task:
            return {}
        details = _artifact_details(product_id, task)
        task["professional_summary"] = _professional_summary(task, details)
        task["professional_artifact_details"] = details
        return task

    def workflow(self, workflow_id: str) -> Dict[str, Any]:
        return console_reader().workflow(workflow_id)

    def review_queue(self, product_id: str) -> Dict[str, Any]:
        return console_reader().review_queue(product_id)

    def assets(self, product_id: str) -> Dict[str, Any]:
        return console_reader().assets(product_id)

    def learning(self, product_id: str) -> Dict[str, Any]:
        return console_reader().learning(product_id)

    def media(self, record_id: str) -> Dict[str, Any]:
        return console_reader().media(record_id)
