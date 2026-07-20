from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENT = ROOT / ".hermes" / "plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))


def test_doubao_provider_key_prefers_doubao_and_keeps_legacy_fallbacks(monkeypatch):
    from product_creative import provider_config

    provider = {
        "auth_env": "DOUBAO_API_KEY",
        "auth_env_fallbacks": ["PRODUCT_CREATIVE_ARK_API_KEY", "ARK_API_KEY"],
    }
    values = {
        "DOUBAO_API_KEY": "doubao-primary",
        "PRODUCT_CREATIVE_ARK_API_KEY": "product-legacy",
        "ARK_API_KEY": "ark-legacy",
    }
    monkeypatch.setattr(provider_config, "_env_value", lambda name: values.get(name, ""))

    assert provider_config.provider_api_key(provider) == "doubao-primary"

    values["DOUBAO_API_KEY"] = ""
    assert provider_config.provider_api_key(provider) == "product-legacy"


def test_windows_env_resolution_reads_machine_scope_when_process_and_user_are_empty(monkeypatch):
    from product_creative import provider_registry

    class Key:
        def __init__(self, root):
            self.root = root

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def open_key(root, _path):
        return Key(root)

    def query_value(key, name):
        if key.root == "user":
            raise FileNotFoundError(name)
        return "machine-doubao-key", 1

    fake_winreg = SimpleNamespace(
        HKEY_CURRENT_USER="user",
        HKEY_LOCAL_MACHINE="machine",
        OpenKey=open_key,
        QueryValueEx=query_value,
    )
    monkeypatch.delenv("DOUBAO_API_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    assert provider_registry.env_value("DOUBAO_API_KEY") == "machine-doubao-key"


def test_normalize_generic_web_item_preserves_title_and_source_url():
    from product_creative.capabilities.inspiration import collection_service

    items = collection_service._normalize_import_items(
        "generic-web",
        {
            "title": "Readable source",
            "url": "https://example.com/article",
            "text": "useful source text",
        },
        1,
    )

    assert items == [
        {
            "source_item_id": "manual-1",
            "title": "Readable source",
            "text": "useful source text",
            "url": "https://example.com/article",
            "stats": {},
            "not_product_fact": True,
        }
    ]


def test_douyin_live_collects_transcript_copy_hook_and_first5_visual_analysis(monkeypatch):
    from product_creative.capabilities.inspiration import collection_service

    calls: list[str] = []
    timeouts: dict[str, int] = {}

    def fake_get(url: str, timeout: int = 30):
        calls.append(url)
        return {
            "status": "ok",
            "siliconflow_key_configured": True,
            "doubao_key_configured": True,
        }

    def fake_post(url: str, body: dict, timeout: int = 60):
        calls.append(url)
        timeouts[url.rsplit("/", 1)[-1]] = timeout
        if url.endswith("/api/search"):
            return {
                "items": [
                    {
                        "aweme_id": "video-1",
                        "title": "爆款参考",
                        "share_url": "https://www.douyin.com/video/1",
                        "stats": {"digg_count": 100},
                    }
                ],
                "count": 1,
            }
        if url.endswith("/api/video/transcribe-online"):
            return {
                "text": "前三秒先点名痛点",
                "copy_analysis": {
                    "source": "deepseek",
                    "opening_hook": "前三秒先点名痛点",
                },
            }
        if url.endswith("/api/video/analyze-first5"):
            return {
                "model": "doubao-seed-2-1-pro-260628",
                "input_mode": "native_video",
                "analyzed_seconds": 5,
                "analysis": {
                    "summary": "首秒近景反差，第二秒展示动作",
                    "hook_strength": 88,
                },
            }
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(collection_service, "_get_json", fake_get)
    monkeypatch.setattr(collection_service, "_post_json", fake_post)

    result = collection_service._douyin_live(
        "http://127.0.0.1:8000",
        "周十五蜂蜜露",
        1,
        transcribe_limit=1,
        analyze_first5_limit=1,
    )

    item = result["items"][0]
    assert item["copy_analysis"]["source"] == "deepseek"
    assert item["first5_analysis"]["analysis"]["hook_strength"] == 88
    assert result["transcribed_count"] == 1
    assert result["first5_analyzed_count"] == 1
    assert any(url.endswith("/api/video/transcribe-online") for url in calls)
    assert any(url.endswith("/api/video/analyze-first5") for url in calls)
    assert timeouts["analyze-first5"] > 600


def test_douyin_analysis_limits_cap_attempts_even_when_every_remote_call_fails(monkeypatch):
    from product_creative.capabilities.inspiration import collection_service

    attempts = {"transcribe": 0, "first5": 0}
    items = [
        {
            "aweme_id": f"video-{index}",
            "title": f"参考 {index}",
            "share_url": f"https://www.douyin.com/video/{index}",
        }
        for index in range(6)
    ]

    monkeypatch.setattr(collection_service, "_get_json", lambda *_args, **_kwargs: {"status": "ok"})

    def fake_post(url: str, _body: dict, timeout: int = 60):
        if url.endswith("/api/search"):
            return {"items": items, "count": len(items)}
        if url.endswith("/api/video/transcribe-online"):
            attempts["transcribe"] += 1
            raise RuntimeError("transcription unavailable")
        if url.endswith("/api/video/analyze-first5"):
            attempts["first5"] += 1
            raise RuntimeError("first5 unavailable")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(collection_service, "_post_json", fake_post)

    result = collection_service._douyin_live(
        "http://127.0.0.1:8000",
        "周十五蜂蜜露",
        6,
        transcribe_limit=5,
        analyze_first5_limit=5,
    )

    assert attempts == {"transcribe": 5, "first5": 5}
    assert len(result["transcript_errors"]) == 5
    assert len(result["first5_analysis_errors"]) == 5


def test_douyin_direct_url_analysis_does_not_depend_on_search_results(monkeypatch):
    from product_creative.capabilities.inspiration import collection_service

    calls: list[str] = []

    monkeypatch.setattr(
        collection_service,
        "_get_json",
        lambda *_args, **_kwargs: {"status": "ok"},
    )

    def fake_post(url: str, body: dict, timeout: int = 60):
        calls.append(url)
        if url.endswith("/api/search"):
            raise AssertionError("direct URL analysis must not depend on search")
        if url.endswith("/api/video/analyze-first5"):
            assert body["url"] == "https://www.douyin.com/video/7215131522305740084"
            return {
                "model": "doubao-seed-2-1-pro-260628",
                "input_mode": "native_video",
                "analyzed_seconds": 5,
                "analysis": {"hook_strength": 91},
            }
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(collection_service, "_post_json", fake_post)

    result = collection_service._douyin_live(
        "http://127.0.0.1:8000",
        "用户指定视频",
        1,
        transcribe_limit=0,
        analyze_first5_limit=1,
        source_url="https://www.douyin.com/video/7215131522305740084",
    )

    assert result["search"]["source"] == "direct_url"
    assert result["items"][0]["source_item_id"] == "7215131522305740084"
    assert result["items"][0]["first5_analysis"]["analysis"]["hook_strength"] == 91
    assert result["first5_analyzed_count"] == 1
    assert not any(url.endswith("/api/search") for url in calls)


def test_external_source_schema_allows_five_real_analysis_results():
    from product_creative.capabilities.inspiration.schemas import (
        PRODUCT_EXTERNAL_SOURCE_COLLECT_SCHEMA,
    )

    properties = PRODUCT_EXTERNAL_SOURCE_COLLECT_SCHEMA["parameters"]["properties"]
    assert properties["transcribe_limit"]["maximum"] == 5
    assert properties["analyze_first5_limit"] == {
        "type": "integer",
        "minimum": 0,
        "maximum": 5,
        "default": 1,
    }


def test_external_source_tool_preserves_explicit_zero_analysis_limits(monkeypatch):
    import json
    from product_creative.capabilities.inspiration import commands

    captured: dict[str, tuple] = {}

    def fake_collect(*args):
        captured["args"] = args
        return {"success": True}

    monkeypatch.setattr(commands, "collect_external_source_snapshot", fake_collect)

    result = json.loads(
        commands._handle_product_external_source_collect(
            {
                "product_id": "honeydew",
                "provider": "douyin-sidecar",
                "query": "指定视频",
                "mode": "live",
                "transcribe_limit": 0,
                "analyze_first5_limit": 0,
            }
        )
    )

    assert result["success"] is True
    assert captured["args"][11] == 0
    assert captured["args"][13] == 0


def test_registry_persists_the_user_selected_doubao_models_and_key_priority():
    from product_creative.provider_registry import load_registry

    providers = {item["name"]: item for item in load_registry()["providers"]}
    for name in ("volcengine-ark-image", "volcengine-ark-vlm", "volcengine-ark-video"):
        assert providers[name]["auth_env"] == "DOUBAO_API_KEY"
        assert providers[name]["auth_env_fallbacks"] == [
            "PRODUCT_CREATIVE_ARK_API_KEY",
            "ARK_API_KEY",
        ]
    assert providers["volcengine-ark-vlm"]["model"] == "doubao-seed-2-1-pro-260628"
    assert providers["volcengine-ark-vlm"]["request_defaults"]["thinking"] == {
        "type": "disabled"
    }
    assert providers["volcengine-ark-video"]["model"] == "doubao-seedance-2-0-260128"


def test_material_vlm_analysis_uses_the_canonical_provider_registry():
    from product_creative.capabilities.material import visual_service

    provider = visual_service._load_provider("volcengine-ark-vlm")

    assert provider["adapter"] == "responses-vlm"
    assert provider["model"] == "doubao-seed-2-1-pro-260628"


def test_material_vlm_analysis_accepts_registered_remote_image_urls():
    from product_creative.capabilities.material import visual_service

    assert (
        visual_service._first_remote_image_url(
            {"remote_url": "https://example.invalid/product.png"}
        )
        == "https://example.invalid/product.png"
    )


def test_material_vlm_analysis_uses_the_provider_request_timeout(monkeypatch):
    from product_creative.capabilities.material import visual_service

    captured = {}
    monkeypatch.setattr(visual_service, "provider_endpoint", lambda _provider: "https://example.invalid/responses")
    monkeypatch.setattr(visual_service, "provider_model", lambda _provider: "test-vlm")
    monkeypatch.setattr(visual_service, "provider_api_key", lambda _provider: "test-key")
    monkeypatch.setattr(
        visual_service,
        "_image_input_url",
        lambda _stored, _material: ("data:image/png;base64,AA==", "data_url"),
    )

    def fake_post(_endpoint, body, _api_key, timeout_seconds):
        captured["timeout_seconds"] = timeout_seconds
        captured["body"] = body
        return {"output_text": "{}"}

    monkeypatch.setattr(visual_service, "_post_json", fake_post)

    visual_service._run_vlm_analysis(
        "volcengine-ark-vlm",
        {
            "request_timeout_seconds": 600,
            "request_defaults": {"thinking": {"type": "disabled"}},
        },
        Path("unused.png"),
        {},
        "测试产品",
    )

    assert captured["timeout_seconds"] == 600
    assert captured["body"]["thinking"] == {"type": "disabled"}


def test_live_video_result_marks_external_call_and_redacts_signed_urls(tmp_path):
    from product_creative.capabilities.product.workspace_service import create_product
    from product_creative.provider_video_tasks import _write_generated_video_result
    from product_creative.workspace import workspace_scope

    signed_url = (
        "https://provider.example/video.mp4?"
        "X-Credential=temporary-credential&X-Signature=temporary-signature"
    )
    with workspace_scope(tmp_path):
        create_product("honeydew", "周十五蜂蜜露")
        result = _write_generated_video_result(
            tmp_path / "products" / "honeydew",
            {
                "job_id": "job-1",
                "video_task_id": "video-task-1",
                "remote_task_id": "remote-task-1",
                "provider": "volcengine-ark-video",
            },
            {"name": "volcengine-ark-video", "status": "live"},
            signed_url,
            {"content": {"video_url": signed_url}},
            download=False,
        )["result"]

    assert result["external_call_performed"] is True
    assert result["remote_url"] == "https://provider.example/video.mp4"
    assert result["outputs"][0]["remote_url"] == "https://provider.example/video.mp4"
    assert result["provider_response"]["content"]["video_url"] == "https://provider.example/video.mp4"
    assert "temporary-credential" not in str(result)
    assert "temporary-signature" not in str(result)
