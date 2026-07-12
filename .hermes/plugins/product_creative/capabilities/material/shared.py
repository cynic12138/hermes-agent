from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))
