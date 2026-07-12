"""Ordered, repeatable SQLite schema migrations."""

from __future__ import annotations


MIGRATIONS = (
    (
        1,
        "durable_runtime_v1",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            workspace_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS workflow_instances (
            workflow_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            definition TEXT NOT NULL,
            definition_version TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            status TEXT NOT NULL,
            current_step INTEGER NOT NULL DEFAULT 0,
            intent_json TEXT NOT NULL,
            pause_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            lease_owner TEXT,
            lease_expires_at REAL
        );
        CREATE INDEX IF NOT EXISTS idx_workflow_product_status
            ON workflow_instances(product_id, status, updated_at);

        CREATE TABLE IF NOT EXISTS workflow_steps (
            workflow_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            step_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            args_json TEXT NOT NULL,
            output_json TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT NOT NULL,
            pause_reason TEXT NOT NULL DEFAULT '',
            error_code TEXT NOT NULL DEFAULT '',
            error_message TEXT NOT NULL DEFAULT '',
            started_at TEXT,
            completed_at TEXT,
            PRIMARY KEY(workflow_id, position),
            UNIQUE(step_id),
            UNIQUE(idempotency_key),
            FOREIGN KEY(workflow_id) REFERENCES workflow_instances(workflow_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_workflow_steps_status
            ON workflow_steps(workflow_id, status, position);

        CREATE TABLE IF NOT EXISTS workflow_events (
            event_id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(workflow_id, sequence),
            FOREIGN KEY(workflow_id) REFERENCES workflow_instances(workflow_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_workflow_events_trace
            ON workflow_events(trace_id, sequence);

        CREATE TABLE IF NOT EXISTS command_receipts (
            receipt_key TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            idempotency_values_json TEXT NOT NULL,
            result_json TEXT NOT NULL DEFAULT '{}',
            error_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_receipts_product_action
            ON command_receipts(product_id, action, updated_at);

        CREATE TABLE IF NOT EXISTS outbox_events (
            outbox_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            workflow_id TEXT NOT NULL DEFAULT '',
            step_id TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempt INTEGER NOT NULL DEFAULT 0,
            available_at REAL NOT NULL,
            lease_owner TEXT,
            lease_expires_at REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(topic, idempotency_key)
        );
        CREATE INDEX IF NOT EXISTS idx_outbox_delivery
            ON outbox_events(status, available_at, lease_expires_at);

        CREATE TABLE IF NOT EXISTS provider_tasks (
            provider_task_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            workflow_id TEXT NOT NULL DEFAULT '',
            step_id TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL,
            kind TEXT NOT NULL,
            external_task_id TEXT NOT NULL DEFAULT '',
            idempotency_key TEXT NOT NULL,
            status TEXT NOT NULL,
            request_json TEXT NOT NULL,
            response_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(provider, idempotency_key)
        );

        CREATE TABLE IF NOT EXISTS rule_candidates (
            rule_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            conflict_key TEXT NOT NULL,
            scope TEXT NOT NULL,
            target_path TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            sample_size INTEGER NOT NULL,
            confidence REAL NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rules_product_conflict
            ON rule_candidates(product_id, conflict_key, status);

        CREATE TABLE IF NOT EXISTS rule_evidence (
            rule_id TEXT NOT NULL,
            evidence_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(rule_id, evidence_id),
            FOREIGN KEY(rule_id) REFERENCES rule_candidates(rule_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rule_conflicts (
            conflict_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            conflict_key TEXT NOT NULL,
            left_rule_id TEXT NOT NULL,
            right_rule_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS writeback_proposals (
            proposal_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            applied_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_proposals_product_status
            ON writeback_proposals(product_id, status, updated_at);

        CREATE TABLE IF NOT EXISTS proposal_updates (
            proposal_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            target_path TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY(proposal_id, position),
            FOREIGN KEY(proposal_id) REFERENCES writeback_proposals(proposal_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS product_brain_versions (
            brain_version_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            parent_version_id TEXT,
            proposal_id TEXT,
            state_json TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(product_id, version)
        );

        CREATE TABLE IF NOT EXISTS generation_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            brain_version_id TEXT NOT NULL,
            target TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS artifact_records (
            artifact_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            content_hash TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(product_id, relative_path)
        );

        CREATE TABLE IF NOT EXISTS material_records (
            material_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            content_hash TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS migration_backups (
            backup_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            backup_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        "durable_runtime_v2",
        """
        CREATE TABLE IF NOT EXISTS legacy_imports (
            import_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            status TEXT NOT NULL,
            imported_records INTEGER NOT NULL DEFAULT 0,
            error_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            UNIQUE(product_id, source_path, source_hash)
        );

        CREATE TABLE IF NOT EXISTS confirmations (
            confirmation_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            command TEXT NOT NULL,
            subject_id TEXT NOT NULL DEFAULT '',
            risk_level TEXT NOT NULL,
            status TEXT NOT NULL,
            trace_id TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            decided_at TEXT
        );

        ALTER TABLE outbox_events ADD COLUMN result_json TEXT NOT NULL DEFAULT '{}';
        ALTER TABLE outbox_events ADD COLUMN error_json TEXT NOT NULL DEFAULT '{}';
        ALTER TABLE provider_tasks ADD COLUMN attempt INTEGER NOT NULL DEFAULT 0;

        CREATE INDEX IF NOT EXISTS idx_legacy_import_product
            ON legacy_imports(product_id, status, created_at);
        CREATE INDEX IF NOT EXISTS idx_confirmations_subject
            ON confirmations(product_id, command, subject_id, status);
        CREATE INDEX IF NOT EXISTS idx_brain_product_status
            ON product_brain_versions(product_id, status, version);
        CREATE INDEX IF NOT EXISTS idx_artifacts_product_type
            ON artifact_records(product_id, artifact_type, created_at);
        CREATE INDEX IF NOT EXISTS idx_materials_product_status
            ON material_records(product_id, status, updated_at);
        """,
    ),
    (
        3,
        "product_brain_provenance_v3",
        """
        ALTER TABLE product_brain_versions ADD COLUMN change_kind TEXT NOT NULL DEFAULT 'legacy_import';
        ALTER TABLE product_brain_versions ADD COLUMN trace_id TEXT NOT NULL DEFAULT '';
        """,
    ),
    (
        4,
        "mock_provider_idempotency_v4",
        """
        CREATE TABLE IF NOT EXISTS mock_provider_effects (
            idempotency_key TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            kind TEXT NOT NULL,
            response_json TEXT NOT NULL,
            external_task_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """,
    ),
    (
        5,
        "product_scoped_artifact_ids_v5",
        """
        ALTER TABLE artifact_records RENAME TO artifact_records_v1;
        CREATE TABLE artifact_records (
            artifact_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            content_hash TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            PRIMARY KEY(product_id, artifact_id),
            UNIQUE(product_id, relative_path)
        );
        INSERT INTO artifact_records
            SELECT artifact_id, product_id, artifact_type, relative_path, content_hash, payload_json, created_at
            FROM artifact_records_v1;
        DROP TABLE artifact_records_v1;
        CREATE INDEX idx_artifacts_product_type
            ON artifact_records(product_id, artifact_type, created_at);

        ALTER TABLE material_records RENAME TO material_records_v1;
        CREATE TABLE material_records (
            material_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            content_hash TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(product_id, material_id)
        );
        INSERT INTO material_records
            SELECT material_id, product_id, relative_path, content_hash, status, payload_json, created_at, updated_at
            FROM material_records_v1;
        DROP TABLE material_records_v1;
        CREATE INDEX idx_materials_product_status
            ON material_records(product_id, status, updated_at);
        """,
    ),
    (
        6,
        "product_scoped_proposals_v6",
        """
        ALTER TABLE proposal_updates RENAME TO proposal_updates_v1;
        ALTER TABLE writeback_proposals RENAME TO writeback_proposals_v1;
        CREATE TABLE writeback_proposals (
            proposal_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            applied_at TEXT,
            PRIMARY KEY(product_id, proposal_id)
        );
        INSERT INTO writeback_proposals
            SELECT proposal_id, product_id, status, risk_level, payload_json, created_at, updated_at, applied_at
            FROM writeback_proposals_v1;
        CREATE TABLE proposal_updates (
            product_id TEXT NOT NULL,
            proposal_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            target_path TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY(product_id, proposal_id, position),
            FOREIGN KEY(product_id, proposal_id)
                REFERENCES writeback_proposals(product_id, proposal_id) ON DELETE CASCADE
        );
        INSERT INTO proposal_updates(product_id, proposal_id, position, target_path, payload_json)
            SELECT p.product_id, u.proposal_id, u.position, u.target_path, u.payload_json
            FROM proposal_updates_v1 u
            JOIN writeback_proposals_v1 p ON p.proposal_id=u.proposal_id;
        DROP TABLE proposal_updates_v1;
        DROP TABLE writeback_proposals_v1;
        CREATE INDEX idx_proposals_product_status
            ON writeback_proposals(product_id, status, updated_at);
        """,
    ),
    (
        7,
        "workflow_step_identity_v7",
        """
        ALTER TABLE workflow_steps RENAME TO workflow_steps_v1;
        CREATE TABLE workflow_steps (
            workflow_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            step_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            args_json TEXT NOT NULL,
            output_json TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT NOT NULL,
            pause_reason TEXT NOT NULL DEFAULT '',
            error_code TEXT NOT NULL DEFAULT '',
            error_message TEXT NOT NULL DEFAULT '',
            started_at TEXT,
            completed_at TEXT,
            PRIMARY KEY(workflow_id, position),
            FOREIGN KEY(workflow_id) REFERENCES workflow_instances(workflow_id) ON DELETE CASCADE
        );
        INSERT INTO workflow_steps
            SELECT workflow_id, position, step_id, action, status, args_json, output_json,
                   attempt, idempotency_key, pause_reason, error_code, error_message,
                   started_at, completed_at
            FROM workflow_steps_v1;
        DROP TABLE workflow_steps_v1;
        CREATE INDEX idx_workflow_steps_status
            ON workflow_steps(workflow_id, status, position);
        CREATE INDEX idx_workflow_steps_identity
            ON workflow_steps(step_id, workflow_id);
        """,
    ),
    (
        8,
        "single_product_lease_v8",
        """
        CREATE TABLE IF NOT EXISTS product_leases (
            product_id TEXT PRIMARY KEY,
            lease_owner TEXT NOT NULL,
            lease_expires_at REAL NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
    ),
)
