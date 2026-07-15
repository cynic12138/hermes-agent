"""Application query boundary for the M9 review console."""

from __future__ import annotations

from typing import Any, Dict, List

from ..ports.runtime_repositories import console_reader


class ProductCreativeConsoleQueries:
    def products(self) -> List[Dict[str, Any]]:
        return console_reader().products()

    def snapshot(self, product_id: str) -> Dict[str, Any]:
        return console_reader().snapshot(product_id)

    def workflows(self, product_id: str) -> List[Dict[str, Any]]:
        return console_reader().workflows(product_id)

    def creative_tasks(self, product_id: str) -> List[Dict[str, Any]]:
        return console_reader().creative_tasks(product_id)

    def creative_task(self, product_id: str, task_id: str) -> Dict[str, Any]:
        return console_reader().creative_task(product_id, task_id)

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
