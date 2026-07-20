"""Deterministic product-plate extraction for packaging-safe composition."""

from __future__ import annotations

from collections import Counter, deque
import hashlib
from pathlib import Path
from typing import Any

from ..common import ensure_product, now_iso, read_json, read_product_state
from ..contracts.creative_artifacts import ProductPlateArtifact
from ..ports.runtime_repositories import materials
from .professional_artifacts import save_professional_artifact


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _material_stored_path(product_root: Path, material: dict[str, Any]) -> Path:
    stored = str(material.get("stored_path") or "").strip()
    if not stored:
        raise ValueError("material has no stored_path")
    root = product_root.resolve()
    path = (root / stored).resolve()
    if root != path and root not in path.parents:
        raise ValueError("material path must stay inside the product workspace")
    if not path.is_file():
        raise FileNotFoundError(f"material image does not exist: {stored}")
    return path


def resolve_product_material(
    product_id: str,
    material_id: str = "",
) -> tuple[dict[str, Any], Path]:
    """Resolve an explicit material/path or the active current main image."""

    product_root = ensure_product(product_id)
    if material_id:
        candidate = Path(material_id)
        if candidate.exists():
            root = product_root.resolve()
            resolved = candidate.resolve()
            if root != resolved and root not in resolved.parents:
                raise ValueError("material path must stay inside the product workspace")
            return {}, resolved
        material = materials().get(product_root.name, material_id)
        if material:
            return material, _material_stored_path(product_root, material)
        name = material_id if material_id.endswith(".json") else f"{material_id}.json"
        legacy_path = product_root / "artifacts" / "material_assets" / name
        if legacy_path.is_file():
            material = read_json(legacy_path, {})
            return material, _material_stored_path(product_root, material)

    state = read_product_state(product_root)
    current_id = str(
        ((state.get("assets") or {}).get("current_main_image_id") or "")
    ).strip()
    if current_id and current_id != material_id:
        return resolve_product_material(product_root.name, current_id)
    candidates = [
        item
        for item in materials().list(product_root.name)
        if item.get("status", "active") == "active"
        and item.get("role") == "current_main_image"
    ]
    if not candidates:
        raise FileNotFoundError("no active current_main_image material is available")
    material = sorted(
        candidates,
        key=lambda item: str(item.get("created_at") or ""),
    )[-1]
    return material, _material_stored_path(product_root, material)


def _edge_coordinates(width: int, height: int) -> list[tuple[int, int]]:
    coordinates = [(x, 0) for x in range(width)]
    coordinates.extend((x, height - 1) for x in range(width))
    coordinates.extend((0, y) for y in range(1, height - 1))
    coordinates.extend((width - 1, y) for y in range(1, height - 1))
    return coordinates


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum((first - second) ** 2 for first, second in zip(left, right))


def _edge_connected_plate(image):
    from PIL import Image

    rgba = image.convert("RGBA")
    width, height = rgba.size
    if width < 3 or height < 3:
        return rgba, False
    rgb = rgba.convert("RGB")
    edges = _edge_coordinates(width, height)
    edge_colors = [rgb.getpixel(point) for point in edges]
    reference, count = Counter(edge_colors).most_common(1)[0]
    if count / len(edge_colors) < 0.65:
        return rgba, False

    threshold_squared = 35**2
    queue = deque(
        point
        for point in edges
        if _color_distance(rgb.getpixel(point), reference) <= threshold_squared
    )
    background: set[tuple[int, int]] = set(queue)
    while queue:
        x, y = queue.popleft()
        for next_x, next_y in (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ):
            point = (next_x, next_y)
            if (
                next_x < 0
                or next_y < 0
                or next_x >= width
                or next_y >= height
                or point in background
            ):
                continue
            if _color_distance(rgb.getpixel(point), reference) <= threshold_squared:
                background.add(point)
                queue.append(point)

    ratio = len(background) / (width * height)
    if ratio < 0.05 or ratio > 0.90:
        return rgba, False
    alpha = Image.new("L", rgba.size, 255)
    alpha_pixels = alpha.load()
    for x, y in background:
        alpha_pixels[x, y] = 0
    rgba.putalpha(alpha)
    return rgba, True


def ensure_product_plate(
    product_id: str,
    *,
    task_id: str,
    material_id: str,
) -> ProductPlateArtifact:
    """Create an immutable-pixel plate without generative redrawing."""

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required for product plate extraction") from exc

    product_root = ensure_product(product_id)
    material, source_path = resolve_product_material(product_root.name, material_id)
    source_hash = _sha256(source_path)
    with Image.open(source_path) as source:
        source.load()
        source_size = source.size
        alpha = source.getchannel("A") if "A" in source.getbands() else None
        has_transparency = bool(
            alpha is not None
            and alpha.getextrema()[0] < 255
        )
        warnings: list[str] = []
        if has_transparency:
            plate = source.convert("RGBA")
            mask_mode = "source_alpha"
        else:
            plate, extracted = _edge_connected_plate(source)
            if extracted:
                mask_mode = "edge_connected_background"
            else:
                plate = source.convert("RGBA")
                mask_mode = "full_rect"
                warnings.append(
                    "Background could not be isolated deterministically; "
                    "the complete source rectangle will remain immutable."
                )

    artifact_id = f"product-plate-{task_id}"
    relative_path = (
        Path("artifacts")
        / "product_plates"
        / f"{artifact_id}.png"
    )
    output = product_root / relative_path
    output.parent.mkdir(parents=True, exist_ok=True)
    plate.save(output, format="PNG")
    artifact = ProductPlateArtifact(
        artifact_id=artifact_id,
        task_id=task_id,
        product_id=product_root.name,
        created_at=now_iso(),
        source_refs=[
            f"material:{material.get('material_id') or material_id}",
        ],
        status="READY",
        source_material_id=str(material.get("material_id") or material_id),
        source_content_hash=source_hash,
        plate_relative_path=str(relative_path),
        plate_content_hash=_sha256(output),
        mask_mode=mask_mode,
        source_size=source_size,
        plate_size=plate.size,
        allowed_transforms=[
            "uniform_scale",
            "translate",
            "alpha_composite",
        ],
        forbidden_transforms=[
            "redraw",
            "non_uniform_scale",
            "change_packaging_text",
            "recolor",
        ],
        warnings=warnings,
    )
    save_professional_artifact(artifact)
    return artifact
