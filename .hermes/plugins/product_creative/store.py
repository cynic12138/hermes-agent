"""Product workspace, Product Wiki, state, feedback, and proposal storage."""

from __future__ import annotations

from .capabilities.product.context_service import context_pack
from .brain.provenance import build_product_fingerprint
from .capabilities.learning.writeback_service import apply_proposal, evolve_product
from .capabilities.learning.feedback_repository import (
    read_channel_feedback_entries,
    read_feedback_entries,
    read_material_feedback_entries,
    read_result_evaluation_entries,
    read_result_feedback_entries,
    read_video_brief_feedback_entries,
    read_visual_alignment_entries,
    record_feedback,
)
from .brain.wiki import export_product_state_from_wiki, wiki_lint_product, wiki_upgrade_product
from .capabilities.product.ingestion_service import ingest_product
from .capabilities.product.workspace_service import create_product, resolve_product_workspace


