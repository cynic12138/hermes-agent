"""Runtime repository ports and composition accessors."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Protocol


class ProductBrainVersions(Protocol):
    def current(self, product_id: str) -> Dict[str, Any]: ...
    def ensure_initial(self, product_id: str, state: Dict[str, Any]) -> Dict[str, Any]: ...
    def commit_state(self, product_id: str, state: Dict[str, Any], *, change_kind: str, **kwargs: Any) -> Dict[str, Any]: ...
    def record_generation_snapshot(self, product_id: str, target: str, payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]: ...
    def apply_proposal(self, **kwargs: Any) -> Dict[str, Any]: ...


class ArtifactRecords(Protocol):
    def save(self, product_id: str, artifact_id: str, artifact_type: str, relative_path: str, payload: Dict[str, Any]) -> str: ...
    def get(self, product_id: str, artifact_id: str) -> Dict[str, Any]: ...
    def list(self, product_id: str, artifact_type: str = "") -> List[Dict[str, Any]]: ...
    def list_records(self, product_id: str, artifact_type: str = "") -> List[Dict[str, Any]]: ...


class ProposalRecords(Protocol):
    def save(self, proposal: Dict[str, Any]) -> str: ...
    def get(self, proposal_id: str, product_id: str = "") -> Dict[str, Any]: ...
    def list(self, product_id: str) -> List[Dict[str, Any]]: ...


class MaterialRecords(Protocol):
    def get(self, product_id: str, material_id: str) -> Dict[str, Any]: ...
    def list(self, product_id: str) -> List[Dict[str, Any]]: ...


class ArtifactDocuments(Protocol):
    def save(self, collection: str, document_id: str, payload: Dict[str, Any]) -> str: ...


class MaterialDocuments(Protocol):
    def list_assets(self) -> List[Dict[str, Any]]: ...
    def save_asset(self, material_id: str, payload: Dict[str, Any]) -> str: ...
    def save_library(self, payload: Dict[str, Any]) -> str: ...


class ProductBrainDocuments(Protocol):
    def load_state(self) -> Dict[str, Any]: ...
    def save_state(self, state: Dict[str, Any]) -> str: ...


class RepositoryFactory(Protocol):
    def product_brains(self) -> ProductBrainVersions: ...
    def artifacts(self) -> ArtifactRecords: ...
    def proposals(self) -> ProposalRecords: ...
    def materials(self) -> MaterialRecords: ...
    def artifact_documents(self, product_root: Path) -> ArtifactDocuments: ...
    def material_documents(self, product_root: Path) -> MaterialDocuments: ...
    def brain_documents(self, product_root: Path) -> ProductBrainDocuments: ...
    def rules(self) -> Any: ...
    def workflows(self) -> Any: ...
    def receipts(self, product_id: str) -> Any: ...
    def provider_dispatcher(self) -> Any: ...
    def observation_reader(self) -> Any: ...


_factory: RepositoryFactory | None = None


def configure_repositories(factory: RepositoryFactory) -> None:
    global _factory
    _factory = factory


def _configured() -> RepositoryFactory:
    if _factory is None:
        raise RuntimeError("Product Creative repositories have not been configured")
    return _factory


def product_brains() -> ProductBrainVersions:
    return _configured().product_brains()


def artifacts() -> ArtifactRecords:
    return _configured().artifacts()


def proposals() -> ProposalRecords:
    return _configured().proposals()


def materials() -> MaterialRecords:
    return _configured().materials()


def artifact_documents(product_root: Path) -> ArtifactDocuments:
    return _configured().artifact_documents(product_root)


def material_documents(product_root: Path) -> MaterialDocuments:
    return _configured().material_documents(product_root)


def brain_documents(product_root: Path) -> ProductBrainDocuments:
    return _configured().brain_documents(product_root)


def rules():
    return _configured().rules()


def workflows():
    return _configured().workflows()


def receipts(product_id: str):
    return _configured().receipts(product_id)


def provider_dispatcher():
    return _configured().provider_dispatcher()


def observation_reader():
    return _configured().observation_reader()
