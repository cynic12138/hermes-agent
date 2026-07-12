"""Shared helpers for the Product Creative plugin."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


TOOLSET = "product_creative"
PLUGIN_DATA_DIR = Path(".hermes") / "product_creative"
PRODUCTS_DIR = PLUGIN_DATA_DIR / "products"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def json_text(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9_.-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-._")
    if not value:
        raise ValueError("product id is required")
    return value[:80]


def products_root() -> Path:
    root = Path.cwd() / PRODUCTS_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def product_dir(product_id: str) -> Path:
    root = products_root().resolve()
    target = (root / slug(product_id)).resolve()
    if root != target and root not in target.parents:
        raise ValueError("product id resolves outside the product workspace")
    return target


def ensure_product(product_id: str) -> Path:
    path = product_dir(product_id)
    if not path.exists():
        raise FileNotFoundError(f"product '{product_id}' does not exist")
    return path


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not isinstance(data, dict):
        return
    resolved = path.resolve()
    parts = resolved.parts
    try:
        products_index = parts.index("products")
    except ValueError:
        return
    if products_index < 2 or parts[products_index - 2 : products_index] != (".hermes", "product_creative"):
        return
    if len(parts) <= products_index + 2:
        return
    product_id = parts[products_index + 1]
    section = parts[products_index + 2]
    if section == "artifacts" and len(parts) > products_index + 4 and resolved.suffix.lower() == ".json":
        from .ports.runtime_repositories import artifacts

        artifact_type = parts[products_index + 3]
        artifacts().save(
            product_id,
            resolved.stem,
            artifact_type,
            str(resolved.relative_to(Path(*parts[: products_index + 2]))),
            data,
        )
        if artifact_type in {
            "image_generation_runs",
            "generated_images",
            "generation_jobs",
            "video_tasks",
            "generated_videos",
        }:
            from .ports.runtime_repositories import product_brains

            product_brains().record_generation_snapshot(
                product_id,
                str(data.get("target") or data.get("brief_type") or artifact_type),
                {
                    "artifact_id": resolved.stem,
                    "artifact_type": artifact_type,
                    "status": data.get("status", ""),
                },
                snapshot_id=f"snapshot-{product_id}-{resolved.stem}",
            )
    elif section == "structured" and resolved.name == "product_state.json":
        from .ports.runtime_repositories import product_brains

        product_brains().commit_state(
            product_id,
            data,
            change_kind="structured_state_update",
        )


def append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False) + "\n")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)


def write_if_missing(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(text, encoding="utf-8")


def product_state_path(base: Path) -> Path:
    return base / "structured" / "product_state.json"


def read_product_state(base: Path) -> Dict[str, Any]:
    from .ports.runtime_repositories import product_brains

    repository = product_brains()
    current = repository.current(base.name)
    if current:
        return dict(current["state"])
    state = read_json(product_state_path(base), {})
    return repository.ensure_initial(base.name, state)["state"] if state else {}


def wiki_path(base: Path, *parts: str) -> Path:
    return base / "wiki" / Path(*parts)


def update_index_and_log(base: Path, action: str, subject: str, details: Iterable[str]) -> None:
    date = today()
    index = base / "wiki" / "index.md"
    if index.exists():
        text = index.read_text(encoding="utf-8")
        text = re.sub(r"Last updated: .*", f"Last updated: {date}", text)
        index.write_text(text, encoding="utf-8")
    body = "\n".join(f"- {item}" for item in details)
    append_text(base / "wiki" / "log.md", f"\n## [{date}] {action} | {subject}\n{body}\n")
