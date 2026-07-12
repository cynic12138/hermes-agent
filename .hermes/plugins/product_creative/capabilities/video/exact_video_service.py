"""Exact-main-image video composition service."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state
from ...ports.runtime_repositories import artifacts, materials

from ..review.task_overview_service import create_task_overview_package

EXACT_MAIN_VIDEO_SCHEMA_VERSION = "product_creative.exact_main_image_video.v8.4"

EXACT_MAIN_VIDEO_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "anime_story": {
        "title": "动漫故事推广",
        "hook": "今天也太热了...",
        "need": "想喝点清爽的",
        "intro_prefix": "试试",
        "taste": "一口酸甜，清爽醒味",
        "badge_line": "三个不添加，喝得更安心",
        "final_line": "清爽酸甜，随手一袋",
        "footer": "夏日清爽小剧场",
        "beats": [
            {"time": "0-25%", "beat": "summer thirst hook"},
            {"time": "25-50%", "beat": "anime mascot introduces the fixed product image"},
            {"time": "50-72%", "beat": "show product claims from image/Product Brain outside the main image"},
            {"time": "72-100%", "beat": "final product CTA while main image stays unchanged"},
        ],
    },
    "summer_refresh": {
        "title": "夏日清爽推广",
        "hook": "热到没胃口？",
        "need": "来点酸甜清爽的",
        "intro_prefix": "今天开袋",
        "taste": "冰爽感、果香感、酸甜感一起到位",
        "badge_line": "清爽解腻，轻松入口",
        "final_line": "冰一下更清爽",
        "footer": "夏日降温补给站",
        "beats": [
            {"time": "0-25%", "beat": "hot summer scene"},
            {"time": "25-50%", "beat": "fixed product image appears as the refresh answer"},
            {"time": "50-72%", "beat": "outside badges explain refresh/taste claims"},
            {"time": "72-100%", "beat": "summer CTA with unchanged product image"},
        ],
    },
    "problem_solution": {
        "title": "痛点解决推广",
        "hook": "想喝又怕添加？",
        "need": "先看包装上的关键信息",
        "intro_prefix": "把选择交给",
        "taste": "酸甜好喝，也要喝得安心",
        "badge_line": "把顾虑写清楚",
        "final_line": "怕添加，就认真看配料",
        "footer": "安心选择小剧场",
        "beats": [
            {"time": "0-25%", "beat": "user concern hook"},
            {"time": "25-50%", "beat": "fixed product image used as answer"},
            {"time": "50-72%", "beat": "claims are shown outside the fixed image"},
            {"time": "72-100%", "beat": "confidence CTA"},
        ],
    },
    "three_claims": {
        "title": "三卖点强化",
        "hook": "喝之前先看这三点",
        "need": "口味、配料、场景都要清楚",
        "intro_prefix": "这袋",
        "taste": "酸甜顺口，信息直接",
        "badge_line": "三点卖点，一眼看懂",
        "final_line": "记住这三个关键词",
        "footer": "三秒卖点记忆点",
        "beats": [
            {"time": "0-25%", "beat": "three-point hook"},
            {"time": "25-50%", "beat": "fixed product image is introduced"},
            {"time": "50-72%", "beat": "three claims orbit outside image"},
            {"time": "72-100%", "beat": "memory CTA"},
        ],
    },
    "festival_topic": {
        "title": "节日话题推广",
        "hook": "节日聚会喝点不一样的",
        "need": "清爽酸甜更容易被记住",
        "intro_prefix": "带上",
        "taste": "轻松分享，酸甜不腻",
        "badge_line": "聚会、饭后、下午茶都合适",
        "final_line": "把清爽带到聚会里",
        "footer": "节日分享小剧场",
        "beats": [
            {"time": "0-25%", "beat": "festival/social scene hook"},
            {"time": "25-50%", "beat": "fixed product image becomes the share item"},
            {"time": "50-72%", "beat": "scene-fit claims appear outside image"},
            {"time": "72-100%", "beat": "festival CTA"},
        ],
    },
}

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))

def _resolve_material(base: Path, asset: str) -> Tuple[Dict[str, Any], Path]:
    if asset:
        candidate = Path(asset)
        if candidate.exists():
            resolved = candidate.resolve()
            root = base.resolve()
            if resolved != root and root not in resolved.parents:
                raise ValueError("material path must stay inside the product workspace")
            return {}, resolved
        name = asset if asset.endswith(".json") else f"{asset}.json"
        direct = base / "artifacts" / "material_assets" / name
        if direct.exists():
            payload = read_json(direct, {})
            return payload, _material_stored_path(base, payload)
    state = read_product_state(base)
    current_id = _text(((state.get("assets") or {}).get("current_main_image_id")))
    if current_id and current_id != asset:
        return _resolve_material(base, current_id)
    candidates = [
        payload for payload in materials().list(base.name)
        if payload.get("status") == "active" and payload.get("role") == "current_main_image"
    ]
    if not candidates:
        raise FileNotFoundError("no active current_main_image material is available")
    payload = sorted(candidates, key=lambda item: _text(item.get("created_at")))[-1]
    return payload, _material_stored_path(base, payload)

def _material_stored_path(base: Path, material: Dict[str, Any]) -> Path:
    stored = _text(material.get("stored_path"))
    if not stored:
        raise ValueError("material has no stored_path")
    path = base / stored
    if not path.exists():
        raise FileNotFoundError(f"material image does not exist: {stored}")
    return path

def _latest_analysis_for_material(base: Path, material_id: str) -> Dict[str, Any]:
    matches = [payload for payload in artifacts().list(base.name, "image_analysis") if payload.get("material_id") == material_id]
    return sorted(matches, key=lambda item: _text(item.get("created_at")))[-1] if matches else {}

def _story_claims(state: Dict[str, Any], analysis: Dict[str, Any], template: str) -> Dict[str, Any]:
    observations = analysis.get("visual_observations") if isinstance(analysis.get("visual_observations"), dict) else {}
    packaging = _text(observations.get("packaging"))
    visible_text = [str(item).strip() for item in _list(observations.get("visible_text")) if str(item).strip()]
    candidates: List[str] = []
    parsed = ((analysis.get("provider_output") or {}).get("parsed_json") or {})
    candidates.extend([str(item).strip() for item in _list(parsed.get("packaging_text_candidates")) if str(item).strip()])
    if packaging:
        candidates.extend([item.strip() for item in packaging.split(";") if item.strip()])
    for item in visible_text:
        for token in ["不加色素", "不加香精", "不加防腐剂", "酸甜好滋味", "金银花柚子汁", "怕添加，就喝金豆芽"]:
            if token in item:
                candidates.append(token)
    deduped: List[str] = []
    for item in candidates:
        if item and item not in deduped:
            deduped.append(item)
    safe = state.get("generation_safe") if isinstance(state.get("generation_safe"), dict) else {}
    product_name = safe.get("product_name") or state.get("name") or "当前产品"
    template_config = EXACT_MAIN_VIDEO_TEMPLATES.get(template, EXACT_MAIN_VIDEO_TEMPLATES["anime_story"])
    return {
        "product_name": product_name,
        "template_title": template_config["title"],
        "hook": template_config["hook"],
        "need": template_config["need"],
        "intro": f"{template_config['intro_prefix']}{product_name}",
        "taste": template_config["taste"],
        "badge_line": template_config["badge_line"],
        "final_line": template_config["final_line"],
        "footer": template_config["footer"],
        "beats": template_config["beats"],
        "badges": [item for item in deduped if item in {"不加色素", "不加香精", "不加防腐剂"}][:3] or ["酸甜好滋味", "清爽口感", "随手一袋"],
        "cta": "怕添加，就喝金豆芽" if "金豆芽" in str(product_name) or any("金豆芽" in item for item in deduped) else f"今天就试试{product_name}",
    }

def create_exact_main_image_video(
    product_id: str,
    asset: str = "",
    theme: str = "",
    template: str = "anime_story",
    duration: int = 10,
    fps: int = 24,
) -> Dict[str, Any]:
    """Compose a local video that keeps the main product image as a fixed layer."""

    if template not in EXACT_MAIN_VIDEO_TEMPLATES:
        raise ValueError(f"unsupported exact main image video template: {template}")
    if duration < 2 or duration > 15:
        raise ValueError("duration must be between 2 and 15 seconds")
    if fps < 6 or fps > 30:
        raise ValueError("fps must be between 6 and 30")

    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow is required for exact-main-image composer") from exc

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for exact-main-image composer")

    base = ensure_product(product_id)
    state = apply_generation_safe_state(read_product_state(base))
    material, source_path = _resolve_material(base, asset)
    analysis = _latest_analysis_for_material(base, _text(material.get("material_id")))
    story = _story_claims(state, analysis, template)

    result_id = f"video-result-{timestamp()}"
    run_dir = base / "artifacts" / "generated_videos" / f"exact-main-video-{timestamp()}"
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    canvas_w, canvas_h = 1080, 1920
    image = Image.open(source_path).convert("RGBA")
    max_box = 820
    scale = min(1.0, max_box / max(image.size))
    display_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
    display = image if display_size == image.size else image.resize(display_size, resampling)
    image_x = (canvas_w - display.width) // 2
    image_y = 92

    font_path = _font_path()

    def font(size: int):
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

    fonts = {
        "hero": font(74),
        "title": font(58),
        "sub": font(42),
        "badge": font(34),
        "small": font(28),
    }

    total_frames = int(duration * fps)
    for idx in range(total_frames):
        t = idx / fps
        frame = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        _draw_anime_background(draw, canvas_w, canvas_h, t)
        _draw_shadow_card(frame, image_x, image_y, display.width, display.height)
        frame.alpha_composite(display, (image_x, image_y))
        _draw_story_layer(draw, story, t, duration, canvas_w, canvas_h, image_x, image_y, display.width, display.height, fonts)
        frame.convert("RGB").save(frames_dir / f"frame_{idx:04d}.jpg", quality=94, subsampling=1)

    video_path = run_dir / f"video-output-{timestamp()}-exact-main-{template}.mp4"
    _run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame_%04d.jpg"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    )
    gif_path = run_dir / f"video-output-{timestamp()}-exact-main-{template}-preview.gif"
    palette = run_dir / "palette.png"
    try:
        _run([ffmpeg, "-y", "-i", str(video_path), "-vf", "fps=8,scale=360:-1:flags=lanczos,palettegen", str(palette)])
        _run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(palette),
                "-lavfi",
                "fps=8,scale=360:-1:flags=lanczos[x];[x][1:v]paletteuse",
                str(gif_path),
            ]
        )
    except RuntimeError:
        gif_path = Path("")

    result = {
        "schema_version": EXACT_MAIN_VIDEO_SCHEMA_VERSION,
        "result_id": result_id,
        "job_id": "",
        "video_task_id": "",
        "product_id": base.name,
        "created_at": now_iso(),
        "provider": "exact-main-image-composer",
        "brief_type": "video",
        "mode": "local_composition",
        "status": "completed",
        "external_call_performed": False,
        "source_material_id": material.get("material_id", ""),
        "source_material_path": _rel(base, source_path),
        "source_analysis_id": analysis.get("analysis_id", ""),
        "theme": _text(theme) or "固定真实主图的动漫剧情推广视频",
        "template": template,
        "template_title": story.get("template_title", ""),
        "duration_seconds": duration,
        "fps": fps,
        "canvas": [canvas_w, canvas_h],
        "main_image_policy": {
            "locked": True,
            "source_is_canonical_material": True,
            "placement": [image_x, image_y],
            "display_size": list(display_size),
            "source_size": [image.width, image.height],
            "whole_image_transform": "none" if display_size == image.size else "uniform_scale_only",
            "forbidden_modifications": [
                "redraw_product_body",
                "change_packaging_text",
                "change_packaging_layout",
                "stylize_product_body",
                "crop_product_image",
                "replace_product_shape",
            ],
            "allowed_animation_scope": "background, captions, anime character, mascot, bubbles, lines, and other elements outside the fixed product image",
        },
        "story_beats": story.get("beats", []),
        "outputs": [
            {
                "type": "video",
                "path": _rel(base, video_path),
                "mime_type": "video/mp4",
                "bytes": video_path.stat().st_size,
                "mock": False,
                "description": "Local deterministic video composition. The main product image is a fixed layer; external animation happens around it.",
            }
        ],
        "review": {
            "requires_human_review": True,
            "ready_for_feedback": True,
            "notes": "M8 exact-main-image composer result. Review should focus on whether the fixed product image remains visually unchanged and whether the surrounding anime story promotes the product.",
        },
        "summary": "Generated a fixed-main-image anime story video without calling an external video model.",
    }
    if gif_path:
        result["outputs"].append(
            {
                "type": "preview_gif",
                "path": _rel(base, gif_path),
                "mime_type": "image/gif",
                "bytes": gif_path.stat().st_size,
                "mock": False,
                "description": "Animated preview for user review.",
            }
        )
    json_path = base / "artifacts" / "generated_videos" / f"{result_id}.json"
    md_path = base / "artifacts" / "generated_videos" / f"{result_id}.md"
    write_json(json_path, result)
    md_path.write_text(_exact_video_markdown(result), encoding="utf-8")
    append_jsonl(
        base / "structured" / "generated_video_index.jsonl",
        {
            "result_id": result_id,
            "created_at": result["created_at"],
            "provider": result["provider"],
            "status": result["status"],
            "path": result["outputs"][0]["path"],
            "source_material_id": result["source_material_id"],
            "main_image_locked": True,
        },
    )
    update_index_and_log(base, "exact-main-video", result_id, [str(json_path.relative_to(base))])
    overview = create_task_overview_package(base.name, result_id, title="Exact main image anime story video")
    return {
        "success": True,
        "product_id": base.name,
        "result_id": result_id,
        "files": {
            "json": str(json_path),
            "markdown": str(md_path),
            "video": str(video_path),
            "preview_gif": str(gif_path) if gif_path else "",
        },
        "result": result,
        "task_overview_package_id": overview["task_overview_package_id"],
        "task_overview_files": overview["files"],
    }

def _font_path() -> str:
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for item in candidates:
        if Path(item).exists():
            return item
    return ""

def _run(args: List[str]) -> None:
    completed = subprocess.run(args, capture_output=True, text=True, timeout=300)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"command failed: {detail[:800]}")

def _draw_anime_background(draw: Any, w: int, h: int, t: float) -> None:
    for y in range(0, h, 6):
        k = y / h
        col = (int(180 * (1 - k) + 226 * k), int(234 * (1 - k) + 252 * k), 255)
        draw.rectangle((0, y, w, y + 6), fill=col)
    cx, cy = w // 2, 520
    for i in range(18):
        a = i * math.tau / 18 + 0.06 * math.sin(t)
        draw.line((cx, cy, cx + math.cos(a) * 900, cy + math.sin(a) * 900), fill=(46, 130, 180, 48), width=7)
    for i in range(8):
        y = 990 + i * 100 + 14 * math.sin(t * 2 + i)
        pts = [(x, y + 20 * math.sin(x / 95 + t * 2 + i)) for x in range(-60, w + 80, 42)]
        draw.line(pts, fill=(43, 134, 179, 92), width=6)
    for i in range(18):
        x = (89 * i + 37 * math.sin(t + i)) % w
        y = 1880 - ((t * 56 + i * 117) % 1850)
        _bubble(draw, x, y, 9 + (i % 5) * 6, 80 + (i % 4) * 28)

def _draw_shadow_card(frame: Any, x: int, y: int, width: int, height: int) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x - 24, y - 20, x + width + 24, y + height + 28), radius=38, fill=(24, 86, 110, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    frame.alpha_composite(shadow)
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((x - 26, y - 26, x + width + 26, y + height + 26), radius=38, fill=(255, 255, 255, 242), outline=(255, 255, 255), width=6)

def _draw_story_layer(
    draw: Any,
    story: Dict[str, Any],
    t: float,
    duration: int,
    w: int,
    h: int,
    image_x: int,
    image_y: int,
    image_w: int,
    image_h: int,
    fonts: Dict[str, Any],
) -> None:
    p = t / max(duration, 1)
    if p < 0.25:
        _character(draw, 170, 1245, 1.12, "hot")
        _mascot(draw, 910 + int(18 * math.sin(t * 3)), 1180 + int(12 * math.cos(t * 4)), 0.85)
        for i in range(10):
            _sparkle(draw, 120 + i * 88, 1028 + (i % 3) * 58, 10, (255, 154, 70, 175))
        _center(draw, w, 1018, story["hook"], fonts["title"])
        _center(draw, w, 1096, story["need"], fonts["sub"], fill=(47, 111, 145), sw=4)
    elif p < 0.50:
        phase = (p - 0.25) / 0.25
        _character(draw, 170, 1245, 1.08, "hot")
        mx = int(930 - 330 * phase + 12 * math.sin(t * 7))
        my = int(1190 - 65 * phase + 18 * math.sin(t * 4))
        _mascot(draw, mx, my, 0.95)
        draw.line((mx - 70, my - 40, image_x + image_w - 160, image_y + image_h - 60), fill=(40, 130, 182, 220), width=9)
        _center(draw, w, 1018, story["intro"], fonts["title"])
        _center(draw, w, 1096, story["product_name"], fonts["sub"], fill=(47, 111, 145), sw=4)
    elif p < 0.72:
        _character(draw, 170, 1245, 1.08, "happy")
        _mascot(draw, 900 + int(12 * math.sin(t * 5)), 1188 + int(12 * math.cos(t * 3)), 0.92)
        for r in range(4):
            off = int((t * 42 + r * 56) % 260)
            draw.rounded_rectangle(
                (image_x - 45 - off // 8, image_y - 45 - off // 8, image_x + image_w + 45 + off // 8, image_y + image_h + 45 + off // 8),
                radius=50 + off // 10,
                outline=(255, 255, 255, max(25, 150 - off // 2)),
                width=5,
            )
        badges = story["badges"][:3]
        positions = [(183, 1030), (540, 1082), (872, 1030)]
        colors = [(80, 190, 108), (255, 154, 70), (255, 122, 153)]
        for idx, badge_text in enumerate(badges):
            _badge(draw, positions[idx][0], positions[idx][1], badge_text, colors[idx], fonts["badge"])
        _center(draw, w, 1196, story.get("badge_line") or story["taste"], fonts["title"])
        _center(draw, w, 1278, story["taste"], fonts["sub"], fill=(47, 111, 145), sw=4)
    else:
        _character(draw, 168 + int(10 * math.sin(t * 3)), 1245, 1.05, "happy")
        _mascot(draw, 900 + int(15 * math.sin(t * 3)), 1195 + int(8 * math.cos(t * 4)), 0.95)
        for i in range(16):
            _sparkle(draw, (70 + i * 66 + int(20 * math.sin(t + i))) % w, 1020 + (i % 4) * 115, 13, (255, 244, 130, 225))
        _center(draw, w, 1016, story["cta"], fonts["hero"])
        _center(draw, w, 1110, story.get("final_line") or story["taste"], fonts["sub"], fill=(47, 111, 145), sw=4)
        draw.rounded_rectangle((145, h - 334, w - 145, h - 212), radius=48, fill=(255, 255, 255, 235), outline=(42, 130, 180, 220), width=5)
        _center(draw, w, h - 308, story.get("footer") or story.get("template_title", ""), fonts["sub"], sw=0)
        _center(draw, w, h - 252, story["taste"], fonts["small"], fill=(47, 111, 145), sw=0)

def _center(draw: Any, w: int, y: int, text: str, font: Any, fill: Tuple[int, int, int] = (22, 93, 130), stroke: Tuple[int, int, int] = (255, 255, 255), sw: int = 5) -> None:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=sw)
    draw.text(((w - (box[2] - box[0])) / 2, y), text, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke)

def _bubble(draw: Any, x: float, y: float, r: float, a: int = 145) -> None:
    draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 255, 255, a), width=4)
    draw.ellipse((x - r * 0.38, y - r * 0.45, x - r * 0.14, y - r * 0.22), fill=(255, 255, 255, min(245, a + 50)))

def _sparkle(draw: Any, x: float, y: float, s: int = 16, c: Tuple[int, int, int, int] = (255, 244, 130, 230)) -> None:
    draw.line((x - s, y, x + s, y), fill=c, width=4)
    draw.line((x, y - s, x, y + s), fill=c, width=4)

def _mascot(draw: Any, cx: int, cy: int, scale: float = 1.0) -> None:
    r = int(52 * scale)
    ink = (32, 47, 56)
    yellow = (255, 219, 66)
    green = (80, 190, 108)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=yellow, outline=ink, width=max(2, int(4 * scale)))
    draw.ellipse((cx + int(20 * scale), cy - int(62 * scale), cx + int(72 * scale), cy - int(24 * scale)), fill=green, outline=ink, width=max(2, int(3 * scale)))
    draw.arc((cx - int(30 * scale), cy - int(16 * scale), cx - int(8 * scale), cy + int(4 * scale)), 205, 335, fill=ink, width=max(2, int(4 * scale)))
    draw.ellipse((cx + int(22 * scale), cy - int(14 * scale), cx + int(32 * scale), cy - int(4 * scale)), fill=ink)
    draw.arc((cx - int(24 * scale), cy - int(2 * scale), cx + int(31 * scale), cy + int(34 * scale)), 10, 170, fill=ink, width=max(2, int(4 * scale)))
    draw.ellipse((cx - int(43 * scale), cy + int(7 * scale), cx - int(25 * scale), cy + int(25 * scale)), fill=(255, 147, 89))
    draw.ellipse((cx + int(34 * scale), cy + int(7 * scale), cx + int(52 * scale), cy + int(25 * scale)), fill=(255, 147, 89))

def _character(draw: Any, cx: int, cy: int, scale: float = 1.0, mood: str = "hot") -> None:
    ink = (32, 47, 56)
    skin = (255, 216, 184)
    hair = (61, 68, 86)
    shirt = (255, 125, 154) if mood == "hot" else (86, 191, 235)
    draw.rounded_rectangle((cx - int(54 * scale), cy + int(46 * scale), cx + int(54 * scale), cy + int(160 * scale)), radius=int(28 * scale), fill=shirt, outline=ink, width=max(2, int(4 * scale)))
    draw.ellipse((cx - int(65 * scale), cy - int(70 * scale), cx + int(65 * scale), cy + int(60 * scale)), fill=skin, outline=ink, width=max(2, int(4 * scale)))
    draw.pieslice((cx - int(69 * scale), cy - int(76 * scale), cx + int(69 * scale), cy + int(42 * scale)), 180, 360, fill=hair)
    draw.ellipse((cx - int(30 * scale), cy - int(12 * scale), cx - int(18 * scale), cy + int(1 * scale)), fill=ink)
    draw.ellipse((cx + int(18 * scale), cy - int(12 * scale), cx + int(30 * scale), cy + int(1 * scale)), fill=ink)
    if mood == "hot":
        draw.arc((cx - int(25 * scale), cy + int(12 * scale), cx + int(25 * scale), cy + int(42 * scale)), 200, 340, fill=ink, width=max(2, int(4 * scale)))
        draw.ellipse((cx + int(54 * scale), cy - int(26 * scale), cx + int(78 * scale), cy + int(15 * scale)), fill=(93, 184, 244), outline=ink, width=max(1, int(2 * scale)))
    else:
        draw.arc((cx - int(30 * scale), cy + int(2 * scale), cx + int(30 * scale), cy + int(39 * scale)), 10, 170, fill=ink, width=max(2, int(4 * scale)))

def _badge(draw: Any, cx: int, cy: int, text: str, color: Tuple[int, int, int], font: Any) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    tw = box[2] - box[0]
    th = box[3] - box[1]
    rect = (cx - tw // 2 - 28, cy - th // 2 - 16, cx + tw // 2 + 28, cy + th // 2 + 16)
    draw.rounded_rectangle(rect, radius=30, fill=(255, 255, 255, 238), outline=color, width=5)
    draw.text((cx - tw / 2, cy - th / 2 - 2), text, font=font, fill=(32, 47, 56))

def _exact_video_markdown(result: Dict[str, Any]) -> str:
    lines = [
        f"# {result['result_id']}",
        "",
        f"Provider: {result['provider']}",
        f"Status: {result['status']}",
        f"Source material: {result.get('source_material_id', '')}",
        f"External call performed: {result['external_call_performed']}",
        "",
        "## Outputs",
        "",
    ]
    for item in result.get("outputs") or []:
        lines.append(f"- {item.get('type')}: {item.get('path')} ({item.get('description')})")
    lines.extend(["", "## Main Image Policy", ""])
    for key, value in (result.get("main_image_policy") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Review", "", result.get("review", {}).get("notes", ""), ""])
    return "\n".join(lines)
