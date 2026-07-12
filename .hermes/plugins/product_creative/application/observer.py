"""Build compact, version-pinned runtime observations from SQLite."""

from __future__ import annotations

from ..contracts.durable import Observation
from ..ports.runtime_repositories import observation_reader


class RuntimeObserver:
    def observe(self, product_id: str) -> Observation:
        return observation_reader().observe(product_id)
