"""SQLite connection, migration, and Unit of Work boundary."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3
import threading
from pathlib import Path
from typing import Iterator

from ...common import now_iso
from ...workspace import workspace_root
from .migrations import MIGRATIONS


_INIT_LOCK = threading.RLock()


def runtime_database_path() -> Path:
    path = workspace_root() / ".hermes" / "product_creative" / "runtime.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()


class SqliteDatabase:
    def __init__(self, path: Path | None = None):
        self.path = (path or runtime_database_path()).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def initialize(self) -> None:
        with _INIT_LOCK:
            connection = self._connect()
            try:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
                )
                applied = {int(row["version"]) for row in connection.execute("SELECT version FROM schema_migrations")}
                for version, name, sql in MIGRATIONS:
                    if version in applied:
                        continue
                    try:
                        safe_name = name.replace("'", "''")
                        applied_at = now_iso().replace("'", "''")
                        connection.executescript(
                            "BEGIN IMMEDIATE;\n"
                            + sql
                            + f"\nINSERT INTO schema_migrations(version, name, applied_at) "
                            f"VALUES ({version}, '{safe_name}', '{applied_at}');\nCOMMIT;"
                        )
                    except Exception:
                        if connection.in_transaction:
                            connection.execute("ROLLBACK")
                        raise
            finally:
                connection.close()

    @contextmanager
    def read_session(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        try:
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()


_DATABASES: dict[str, SqliteDatabase] = {}


def runtime_database(path: Path | None = None) -> SqliteDatabase:
    resolved = str((path or runtime_database_path()).resolve())
    database = _DATABASES.get(resolved)
    if database is None:
        database = SqliteDatabase(Path(resolved))
        _DATABASES[resolved] = database
    return database
