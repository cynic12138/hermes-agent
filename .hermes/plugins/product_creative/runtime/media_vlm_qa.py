"""Doubao VLM observations for rendered media quality assurance."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from ..capabilities.material import visual_service
from ..common import ensure_product, now_iso, slug, write_json
from ..provider_config import (
    provider_api_key,
    provider_endpoint,
    provider_model,
)
from ..provider_registry import provider_entry
from .media_compositor import probe_media
from .media_dependencies import resolve_media_tool


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_DEFAULT_PROMPT = (
    "你是视频成片质量检查员。请观察这组三帧接触图，只描述画面中实际可见的内容，"
    "不要补充产品功效、使用方法或其他不可见事实。请只输出 JSON，不要输出 Markdown。"
    "字段必须包括：observed_text（可见字幕原文，无法确认则空字符串）、"
    "subtitle_bbox（主要字幕的归一化 [x,y,width,height]，无法确认则空数组）、"
    "subtitle_visible_ratio（0 到 1）、confidence（0 到 1）、"
    "characters（稳定可识别的角色描述数组）、scene（简短场景描述）、"
    "product_visible（布尔值）、observed_action（实际观察到的动作）、"
    "action_completed（计划动作是否在镜头内完成的布尔值）、"
    "continuity_notes（数组）、risk_flags（数组）。"
    "遇到乱码、文字不完整、包装疑似变化、角色或场景不稳定时写入 risk_flags，"
    "并相应降低 confidence。"
)


def _workspace_media_path(product_id: str, media_path: Path) -> Path:
    product_root = ensure_product(product_id).resolve()
    resolved = Path(media_path).resolve()
    if product_root != resolved and product_root not in resolved.parents:
        raise ValueError("media VLM QA path must stay inside the product workspace")
    if not resolved.is_file():
        raise FileNotFoundError(f"media VLM QA input is missing: {resolved}")
    return resolved


def _duration_seconds(media_path: Path) -> float:
    probe = probe_media(media_path)
    value = (probe.get("format") or {}).get("duration")
    try:
        duration = float(value or 0)
    except (TypeError, ValueError):
        duration = 0
    return max(0.1, duration)


def _extract_video_frame(
    media_path: Path,
    output_path: Path,
    *,
    at_seconds: float,
) -> None:
    ffmpeg = resolve_media_tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for live media VLM QA")
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{max(0.0, at_seconds):.3f}",
            "-i",
            str(media_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=512:-2",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not output_path.is_file():
        detail = (result.stderr or result.stdout or "ffmpeg frame extraction failed")
        raise RuntimeError(detail.strip()[-2000:])


def _extract_contact_sheet(
    product_id: str,
    shot_id: str,
    media_path: Path,
) -> Path:
    """Extract three representative frames into one auditable JPEG."""

    media_path = _workspace_media_path(product_id, media_path)
    product_root = ensure_product(product_id)
    media_hash = hashlib.sha256(media_path.read_bytes()).hexdigest()
    output_dir = product_root / "artifacts" / "media_qa" / "contact-sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        output_dir
        / f"{slug(shot_id) or 'shot'}-{media_hash[:16]}.jpg"
    )
    if output_path.is_file():
        return output_path

    if media_path.suffix.lower() in _IMAGE_SUFFIXES:
        with Image.open(media_path) as image:
            frame = image.convert("RGB")
            frame.thumbnail((512, 512))
            frames = [frame.copy(), frame.copy(), frame.copy()]
    else:
        duration = _duration_seconds(media_path)
        frame_dir = output_dir / f".{output_path.stem}-frames"
        frame_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        for index, ratio in enumerate((0.15, 0.50, 0.85), 1):
            frame_path = frame_dir / f"{index}.jpg"
            _extract_video_frame(
                media_path,
                frame_path,
                at_seconds=max(0.0, duration * ratio),
            )
            with Image.open(frame_path) as image:
                frames.append(image.convert("RGB").copy())

    target_height = max(frame.height for frame in frames)
    normalized = []
    for frame in frames:
        if frame.height != target_height:
            width = max(1, round(frame.width * target_height / frame.height))
            frame = frame.resize((width, target_height))
        normalized.append(frame)
    sheet = Image.new(
        "RGB",
        (sum(frame.width for frame in normalized), target_height),
        (255, 255, 255),
    )
    offset = 0
    for frame in normalized:
        sheet.paste(frame, (offset, 0))
        offset += frame.width
    sheet.save(output_path, format="JPEG", quality=90)
    return output_path


def _request_doubao_observation(
    *,
    provider_name: str,
    contact_sheet: Path,
    prompt: str,
) -> dict[str, Any]:
    """Call the registered Responses VLM without exposing credentials."""

    provider = provider_entry(provider_name)
    endpoint = provider_endpoint(provider)
    model = provider_model(provider)
    api_key = provider_api_key(provider)
    if not endpoint:
        raise RuntimeError(
            f"VLM provider endpoint is not configured: {provider_name}"
        )
    if not model:
        raise RuntimeError(
            f"VLM provider model is not configured: {provider_name}"
        )
    if provider.get("auth_env") and not api_key:
        raise RuntimeError(
            f"VLM provider auth env is missing: {provider.get('auth_env')}"
        )
    image_data = base64.b64encode(contact_sheet.read_bytes()).decode("ascii")
    mime_type = (
        "image/png"
        if contact_sheet.suffix.lower() == ".png"
        else "image/jpeg"
    )
    body: dict[str, Any] = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": (
                            f"data:{mime_type};base64,{image_data}"
                        ),
                    },
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                ],
            }
        ],
    }
    defaults = provider.get("request_defaults") or {}
    if defaults.get("max_output_tokens"):
        body["max_output_tokens"] = int(defaults["max_output_tokens"])
    thinking = defaults.get("thinking")
    if (
        isinstance(thinking, dict)
        and thinking.get("type") in {"enabled", "disabled"}
    ):
        body["thinking"] = {"type": thinking["type"]}
    response = visual_service._post_json(
        endpoint,
        body,
        api_key,
        int(provider.get("request_timeout_seconds") or 120),
    )
    output_text = visual_service._extract_response_text(response)
    parsed = visual_service._parse_json_text(output_text)
    if not parsed:
        raise RuntimeError(
            "Doubao media QA returned no valid JSON observation"
        )
    return {
        **parsed,
        "provider": provider_name,
        "model": model,
        "usage": (
            response.get("usage", {})
            if isinstance(response, dict)
            else {}
        ),
    }


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


class DoubaoMediaQaAdapter:
    """One shared, bounded VLM observation cache for OCR and visual QA."""

    def __init__(
        self,
        *,
        provider_name: str = "volcengine-ark-vlm",
        max_calls: int = 5,
    ) -> None:
        self.provider_name = provider_name
        self.max_calls = min(5, max(0, int(max_calls)))
        self.call_count = 0
        self._cache: dict[str, dict[str, Any]] = {}

    def _observe(
        self,
        *,
        product_id: str,
        shot_id: str,
        media_path: Path,
    ) -> dict[str, Any]:
        media_path = _workspace_media_path(product_id, media_path)
        cache_key = str(media_path).casefold()
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        if self.call_count >= self.max_calls:
            raise RuntimeError(
                "Doubao media QA real call limit has been reached"
            )
        contact_sheet = _extract_contact_sheet(
            product_id,
            shot_id,
            media_path,
        )
        raw = _request_doubao_observation(
            provider_name=self.provider_name,
            contact_sheet=contact_sheet,
            prompt=_DEFAULT_PROMPT,
        )
        self.call_count += 1
        confidence = min(1.0, max(0.0, _float(raw.get("confidence"))))
        visible_ratio = min(
            1.0,
            max(0.0, _float(raw.get("subtitle_visible_ratio"))),
        )
        bbox = raw.get("subtitle_bbox")
        if not (
            isinstance(bbox, list)
            and len(bbox) == 4
            and all(isinstance(item, (int, float)) for item in bbox)
        ):
            bbox = []
        observation = {
            "observed_text": str(raw.get("observed_text") or ""),
            "subtitle_bbox": list(bbox),
            "subtitle_visible_ratio": visible_ratio,
            "confidence": confidence,
            "characters": _string_list(raw.get("characters")),
            "scene": str(raw.get("scene") or "").strip(),
            "product_visible": bool(raw.get("product_visible")),
            "observed_action": str(raw.get("observed_action") or "").strip(),
            "action_completed": raw.get("action_completed") is True,
            "continuity_notes": _string_list(
                raw.get("continuity_notes")
            ),
            "risk_flags": _string_list(raw.get("risk_flags")),
            "provider": str(raw.get("provider") or self.provider_name),
            "model": str(raw.get("model") or ""),
            "usage": (
                raw.get("usage")
                if isinstance(raw.get("usage"), dict)
                else {}
            ),
        }
        product_root = ensure_product(product_id)
        media_hash = hashlib.sha256(media_path.read_bytes()).hexdigest()
        evidence_path = (
            product_root
            / "artifacts"
            / "media_qa"
            / "vlm-observations"
            / (
                f"{slug(shot_id) or 'shot'}-"
                f"{media_hash[:16]}.json"
            )
        )
        write_json(
            evidence_path,
            {
                "schema_version": (
                    "product_creative.media_vlm_observation.v1"
                ),
                "product_id": product_id,
                "shot_id": shot_id,
                "created_at": now_iso(),
                "media_path": str(media_path.relative_to(product_root)),
                "contact_sheet": str(
                    contact_sheet.relative_to(product_root)
                ),
                **observation,
            },
        )
        observation["evidence_refs"] = [
            "media_qa:"
            + str(evidence_path.relative_to(product_root))
        ]
        self._cache[cache_key] = observation
        return observation

    def ocr(
        self,
        *,
        product_id: str,
        shot_id: str,
        media_path: Path,
        expected_text: str,
        start_seconds: float,
        end_seconds: float,
    ) -> dict[str, Any]:
        del expected_text
        observation = self._observe(
            product_id=product_id,
            shot_id=shot_id,
            media_path=media_path,
        )
        return {
            "observed_text": observation["observed_text"],
            "confidence": observation["confidence"],
            "bounding_box": observation["subtitle_bbox"],
            "visible_duration_seconds": (
                max(0.0, end_seconds - start_seconds)
                * observation["subtitle_visible_ratio"]
            ),
            "evidence_refs": list(observation["evidence_refs"]),
        }

    def visual(
        self,
        *,
        product_id: str,
        shot_id: str,
        media_path: Path,
        expected_characters: list[str],
        expected_scene: str,
        expected_product_visible: bool,
        expected_action: str = "",
    ) -> dict[str, Any]:
        del (
            expected_characters,
            expected_scene,
            expected_product_visible,
            expected_action,
        )
        observation = self._observe(
            product_id=product_id,
            shot_id=shot_id,
            media_path=media_path,
        )
        return {
            "confidence": observation["confidence"],
            "characters": list(observation["characters"]),
            "scene": observation["scene"],
            "product_visible": observation["product_visible"],
            "observed_action": observation["observed_action"],
            "action_completed": observation["action_completed"],
            "continuity_notes": list(
                observation["continuity_notes"]
            ),
            "risk_flags": list(observation["risk_flags"]),
            "evidence_refs": list(observation["evidence_refs"]),
        }


def create_doubao_media_qa_adapters(
    *,
    max_calls: int = 5,
) -> tuple[Any, Any]:
    adapter = DoubaoMediaQaAdapter(max_calls=max_calls)
    return adapter.ocr, adapter.visual
