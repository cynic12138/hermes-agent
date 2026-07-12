"""Infrastructure composition root for Product Creative repositories."""

from __future__ import annotations

from ..ports.runtime_repositories import configure_repositories
from .sqlite.domain_repositories import (
    SqliteArtifactRepository,
    SqliteMaterialRepository,
    SqliteProductBrainRepository,
    SqliteProposalRepository,
    SqliteRuleRepository,
)
from .sqlite.repositories import SqliteActionReceiptRepository, SqliteWorkflowRepository
from ..stores.filesystem import (
    FileSystemArtifactRepository,
    FileSystemMaterialRepository,
    FileSystemProductBrainRepository,
)
from .provider_dispatcher import DurableProviderDispatcher
from .runtime_read_model import SqliteObservationReader
from .m9_repository import SqliteConsoleReader, SqliteRecoveryRepository


class SqliteRepositoryFactory:
    def product_brains(self) -> SqliteProductBrainRepository:
        return SqliteProductBrainRepository()

    def artifacts(self) -> SqliteArtifactRepository:
        return SqliteArtifactRepository()

    def proposals(self) -> SqliteProposalRepository:
        return SqliteProposalRepository()

    def materials(self) -> SqliteMaterialRepository:
        return SqliteMaterialRepository()

    def artifact_documents(self, product_root):
        return FileSystemArtifactRepository(product_root)

    def material_documents(self, product_root):
        return FileSystemMaterialRepository(product_root)

    def brain_documents(self, product_root):
        return FileSystemProductBrainRepository(product_root)

    def rules(self):
        return SqliteRuleRepository()

    def workflows(self):
        return SqliteWorkflowRepository()

    def receipts(self, product_id: str):
        return SqliteActionReceiptRepository(product_id)

    def provider_dispatcher(self):
        return DurableProviderDispatcher()

    def observation_reader(self):
        return SqliteObservationReader()

    def recovery(self):
        return SqliteRecoveryRepository()

    def console_reader(self):
        return SqliteConsoleReader()


def configure_default_repositories() -> None:
    configure_repositories(SqliteRepositoryFactory())
