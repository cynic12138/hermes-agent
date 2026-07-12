"""Strict and atomic filesystem storage adapters."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

from ..infrastructure.sqlite.domain_repositories import (
    SqliteArtifactRepository,
    SqliteMaterialRepository,
    SqliteProductBrainRepository,
)
from ..ports.errors import StoreCorruptionError, StoreError


_WRITE_LOCK = threading.RLock()


def read_json_strict(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StoreCorruptionError(f"cannot read structured JSON '{path}': {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise StoreCorruptionError(f"structured JSON '{path}' must contain an object")
    return payload


def write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the temporary basename short so long product/action identifiers stay
    # below the legacy Windows MAX_PATH boundary.
    temporary = path.parent / f".tmp-{uuid.uuid4().hex[:8]}"
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with _WRITE_LOCK:
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise StoreError(f"cannot atomically write structured JSON '{path}': {exc}") from exc


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with _WRITE_LOCK:
        try:
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise StoreError(f"cannot append structured event '{path}': {exc}") from exc


def _safe_segment(value: str, label: str) -> str:
    value = str(value or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ."
    if not value or value in {".", ".."} or any(char not in allowed for char in value):
        raise ValueError(f"{label} contains unsupported characters")
    return value


class FileSystemJsonDocumentRepository:
    """Collection-scoped JSON documents under one fixed storage root."""

    def __init__(self, root: Path):
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _collection(self, collection: str) -> Path:
        path = (self._root / _safe_segment(collection, "collection")).resolve()
        if self._root not in path.parents:
            raise ValueError("collection resolves outside repository root")
        return path

    def _path(self, collection: str, document_id: str) -> Path:
        folder = self._collection(collection)
        path = (folder / f"{_safe_segment(document_id, 'document_id')}.json").resolve()
        if folder not in path.parents:
            raise ValueError("document_id resolves outside collection")
        return path

    def get(self, collection: str, document_id: str) -> Dict[str, Any] | None:
        path = self._path(collection, document_id)
        return read_json_strict(path) if path.exists() else None

    def save(self, collection: str, document_id: str, payload: Dict[str, Any]) -> str:
        path = self._path(collection, document_id)
        write_json_atomic(path, payload)
        return str(path)

    def list(self, collection: str) -> List[Dict[str, Any]]:
        folder = self._collection(collection)
        if not folder.exists():
            return []
        return [read_json_strict(path) for path in sorted(folder.glob("*.json"))]

    def append(self, stream: str, payload: Dict[str, Any]) -> str:
        path = (self._root / f"{_safe_segment(stream, 'stream')}.jsonl").resolve()
        if self._root not in path.parents:
            raise ValueError("stream resolves outside repository root")
        append_jsonl(path, payload)
        return str(path)


class FileSystemStructuredRepository(FileSystemJsonDocumentRepository):
    def __init__(self, product_root: Path):
        super().__init__(product_root.resolve() / "structured")


class FileSystemArtifactRepository(FileSystemJsonDocumentRepository):
    def __init__(self, product_root: Path):
        self._product_root = product_root.resolve()
        self._records = SqliteArtifactRepository()
        super().__init__(self._product_root / "artifacts")

    def get(self, collection: str, document_id: str) -> Dict[str, Any] | None:
        payload = self._records.get(self._product_root.name, document_id)
        return payload or super().get(collection, document_id)

    def save(self, collection: str, document_id: str, payload: Dict[str, Any]) -> str:
        path = super().save(collection, document_id, payload)
        relative_path = str(Path(path).resolve().relative_to(self._product_root))
        self._records.save(self._product_root.name, document_id, collection, relative_path, payload)
        return path

    def list(self, collection: str) -> List[Dict[str, Any]]:
        records = self._records.list(self._product_root.name, collection)
        return records or super().list(collection)


class FileSystemProductBrainRepository:
    def __init__(self, product_root: Path):
        self._product_root = product_root.resolve()
        self._state_path = self._product_root / "structured" / "product_state.json"
        self._wiki_root = self._product_root / "wiki"
        self._versions = SqliteProductBrainRepository()

    def load_state(self) -> Dict[str, Any]:
        current = self._versions.current(self._product_root.name)
        return current["state"] if current else read_json_strict(self._state_path)

    def save_state(self, state: Dict[str, Any]) -> str:
        self._versions.commit_state(
            self._product_root.name,
            state,
            change_kind="structured_state_update",
        )
        write_json_atomic(self._state_path, state)
        return str(self._state_path)

    def page_path(self, relative_path: str) -> str:
        path = (self._wiki_root / relative_path).resolve()
        if self._wiki_root.resolve() not in path.parents:
            raise ValueError("Product Brain page resolves outside wiki root")
        return str(path)


class FileSystemMaterialRepository:
    def __init__(self, product_root: Path):
        root = product_root.resolve()
        self._product_root = root
        self._artifacts = FileSystemArtifactRepository(root)
        self._library_path = root / "structured" / "material_library.json"
        self._product_id = root.name
        self._records = SqliteMaterialRepository()

    def get_asset(self, material_id: str) -> Dict[str, Any] | None:
        return self._records.get(self._product_id, material_id) or self._artifacts.get("material_assets", material_id)

    def save_asset(self, material_id: str, payload: Dict[str, Any]) -> str:
        path = self._artifacts.save("material_assets", material_id, payload)
        relative_path = str(Path(path).resolve().relative_to(self._product_root))
        self._records.save(self._product_id, material_id, relative_path, payload)
        return path

    def list_assets(self) -> List[Dict[str, Any]]:
        return self._records.list(self._product_id) or self._artifacts.list("material_assets")

    def load_library(self) -> Dict[str, Any]:
        return read_json_strict(self._library_path) if self._library_path.exists() else {}

    def save_library(self, payload: Dict[str, Any]) -> str:
        write_json_atomic(self._library_path, payload)
        return str(self._library_path)
