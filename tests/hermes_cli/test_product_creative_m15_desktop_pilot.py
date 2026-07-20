from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENT = ROOT / ".hermes" / "plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))


def _client() -> TestClient:
    from product_creative.dashboard.plugin_api import router

    app = FastAPI()
    app.include_router(router, prefix="/api/plugins/product_creative")
    return TestClient(app)


def _headers(workspace: Path) -> dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    return {"X-Hermes-Workspace-Root": str(workspace)}


def test_desktop_diagnostics_report_presence_without_secret_values(monkeypatch):
    from product_creative.runtime.desktop_diagnostics import (
        collect_desktop_diagnostics,
    )

    secret_values = {
        "DOUBAO_API_KEY": "doubao-secret-must-not-leak",
        "DEEPSEEK_API_KEY": "deepseek-secret-must-not-leak",
        "SILICONFLOW_API_KEY": "silicon-secret-must-not-leak",
    }
    for key, value in secret_values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", "1")

    report = collect_desktop_diagnostics(
        resolve_tool=lambda name: f"C:/tools/{name}.exe",
        probe_sidecar=lambda _name, _url: {
            "available": False,
            "detail": "Not running",
        },
    )

    checks = {item["id"]: item for item in report["checks"]}
    assert report["schema_name"] == "product_creative.desktop_diagnostics.v1"
    assert report["overall_status"] == "READY"
    assert checks["credential-doubao"]["status"] == "READY"
    assert checks["credential-doubao"]["metadata"]["capabilities"] == [
        "image",
        "image_analysis",
        "video",
    ]
    assert checks["credential-deepseek"]["status"] == "READY"
    assert checks["credential-siliconflow"]["status"] == "READY"
    assert checks["real-provider-opt-in"]["status"] == "READY"
    assert checks["media-ffmpeg"]["status"] == "READY"
    assert checks["media-ffprobe"]["status"] == "READY"
    assert checks["sidecar-xhs"]["status"] == "OPTIONAL_OFFLINE"
    assert checks["sidecar-douyin"]["status"] == "OPTIONAL_OFFLINE"
    assert checks["sidecar-xhs"]["required"] is False

    serialized = json.dumps(report, ensure_ascii=False)
    for secret in secret_values.values():
        assert secret not in serialized


def test_desktop_diagnostics_missing_optional_sources_do_not_block_core(monkeypatch):
    from product_creative.runtime.desktop_diagnostics import (
        collect_desktop_diagnostics,
    )

    monkeypatch.setenv("DOUBAO_API_KEY", "configured")
    monkeypatch.setenv("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER", "1")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)

    report = collect_desktop_diagnostics(
        resolve_tool=lambda name: f"C:/tools/{name}.exe",
        probe_sidecar=lambda _name, _url: {
            "available": False,
            "detail": "Not running",
        },
    )

    assert report["overall_status"] == "READY"
    assert all(
        item["required"] is False
        for item in report["checks"]
        if item["id"] in {
            "credential-deepseek",
            "credential-siliconflow",
            "sidecar-xhs",
            "sidecar-douyin",
        }
    )


def test_desktop_diagnostics_route_is_read_only_and_workspace_scoped(
    monkeypatch,
    tmp_path,
):
    from product_creative.dashboard import plugin_api

    monkeypatch.setattr(
        plugin_api,
        "collect_desktop_diagnostics",
        lambda: {
            "schema_name": "product_creative.desktop_diagnostics.v1",
            "schema_version": "1.0",
            "overall_status": "READY",
            "checks": [],
        },
    )
    workspace = tmp_path / "workspace"

    response = _client().get(
        "/api/plugins/product_creative/v1/diagnostics",
        headers=_headers(workspace),
    )

    assert response.status_code == 200
    assert response.json()["overall_status"] == "READY"
    assert not (workspace / ".hermes" / "product_creative").exists()


def test_desktop_onboarding_creates_product_and_keeps_description_out_of_canonical(
    tmp_path,
):
    from product_creative.ports.runtime_repositories import product_brains
    from product_creative.workspace import workspace_scope

    workspace = tmp_path / "workspace"
    response = _client().post(
        "/api/plugins/product_creative/v1/products",
        headers=_headers(workspace),
        json={
            "name": "周十五益生菌蜂蜜露",
            "product_id": "zhou-shiwu-honeydew",
            "description": "用户提供的产品描述，只能先作为待确认资料。",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["created"] is True
    assert payload["selected_product_id"] == "zhou-shiwu-honeydew"
    assert payload["ingest"]["canonical_brain_changed"] is False

    with workspace_scope(workspace):
        current = product_brains().current("zhou-shiwu-honeydew")
        assert current["version"] == 1
        assert current["state"]["basic"]["brief"] == ""

    product_root = (
        workspace
        / ".hermes"
        / "product_creative"
        / "products"
        / "zhou-shiwu-honeydew"
    )
    drafts = list((product_root / "artifacts" / "draft_understanding").glob("*.json"))
    assert len(drafts) == 1
    assert "用户提供的产品描述" in drafts[0].read_text(encoding="utf-8")


def test_desktop_onboarding_rejects_empty_name_and_existing_product(tmp_path):
    workspace = tmp_path / "workspace"
    headers = _headers(workspace)
    client = _client()

    empty = client.post(
        "/api/plugins/product_creative/v1/products",
        headers=headers,
        json={"name": "   "},
    )
    assert empty.status_code == 422

    first = client.post(
        "/api/plugins/product_creative/v1/products",
        headers=headers,
        json={"name": "同名产品", "product_id": "same-product"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/plugins/product_creative/v1/products",
        headers=headers,
        json={"name": "同名产品", "description": "不应写入现有产品"},
    )
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]

    product_root = (
        workspace
        / ".hermes"
        / "product_creative"
        / "products"
        / "same-product"
    )
    assert not list((product_root / "raw" / "product-inputs").glob("*.md"))


def test_desktop_onboarding_and_product_lists_are_workspace_isolated(tmp_path):
    client = _client()
    workspace_a = tmp_path / "workspace-a"
    workspace_b = tmp_path / "workspace-b"

    created = client.post(
        "/api/plugins/product_creative/v1/products",
        headers=_headers(workspace_a),
        json={"name": "Workspace A product", "product_id": "product-a"},
    )
    assert created.status_code == 201

    list_a = client.get(
        "/api/plugins/product_creative/v1/products",
        headers=_headers(workspace_a),
    )
    list_b = client.get(
        "/api/plugins/product_creative/v1/products",
        headers=_headers(workspace_b),
    )

    assert [item["product_id"] for item in list_a.json()["products"]] == [
        "product-a"
    ]
    assert list_b.json()["products"] == []
