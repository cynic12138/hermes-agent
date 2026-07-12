"""Public material capability API."""

from .asset_service import bind_material_remote_url, list_material_assets, rebuild_material_manifest, register_material_asset
from .visual_service import analyze_image_asset, align_visual_analysis
from .card_service import check_m2_material_compatibility, rebuild_material_cards, rebuild_material_library_map
from .pack_service import prepare_task_material_pack, record_material_feedback, record_material_usage
from .resolver_service import provider_capability_matrix, resolve_material_execution_input

__all__ = [name for name in globals() if not name.startswith("_")]
