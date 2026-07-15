from __future__ import annotations

import hashlib
import json

import pytest

from hermes_cli import web_server


def _plugin(tmp_path, *, source="user", desktop=None):
    dashboard = tmp_path / "plugin" / "dashboard"
    (dashboard / "dist").mkdir(parents=True)
    (dashboard / "dist" / "desktop.js").write_text("window.desktopPluginLoaded = true", encoding="utf-8")
    return {
        "name": "example",
        "version": "1.0.0",
        "source": source,
        "desktop": desktop or {
            "api_version": 1,
            "path": "/example",
            "entry": "dist/desktop.js",
            "position": "end",
            "label": "Example",
            "icon": "extensions",
        },
        "_dir": str(dashboard),
    }


@pytest.fixture
def client(monkeypatch, tmp_path):
    from starlette.testclient import TestClient

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    instance = TestClient(web_server.app)
    instance.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN
    return instance


def test_desktop_list_excludes_project_and_inactive_plugins(client, monkeypatch, tmp_path):
    active = _plugin(tmp_path)
    project = {**active, "name": "project", "source": "project"}
    disabled = {**active, "name": "disabled"}
    monkeypatch.setattr(web_server, "_get_dashboard_plugins", lambda: [active, project, disabled])
    monkeypatch.setattr(web_server, "_is_dashboard_plugin_active", lambda item: item["name"] != "disabled")

    response = client.get("/api/desktop/plugins")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["plugins"]] == ["example"]


def test_desktop_bundle_is_authenticated_and_hashed(client, monkeypatch, tmp_path):
    plugin = _plugin(tmp_path)
    monkeypatch.setattr(web_server, "_get_dashboard_plugins", lambda: [plugin])
    monkeypatch.setattr(web_server, "_is_dashboard_plugin_active", lambda _item: True)

    response = client.get("/api/desktop/plugins/example/bundle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == 1
    assert payload["entry"] == "dist/desktop.js"
    assert payload["name"] == "example"
    assert payload["version"] == "1.0.0"
    assert payload["sha256"] == hashlib.sha256(payload["source"].encode()).hexdigest()


def test_desktop_endpoints_require_authentication(monkeypatch):
    from starlette.testclient import TestClient

    instance = TestClient(web_server.app)
    assert instance.get("/api/desktop/plugins").status_code == 401
    assert instance.get("/api/desktop/plugins/example/bundle").status_code == 401


def test_desktop_bundle_rejects_project_plugin(client, monkeypatch, tmp_path):
    plugin = _plugin(tmp_path, source="project")
    monkeypatch.setattr(web_server, "_get_dashboard_plugins", lambda: [plugin])
    monkeypatch.setattr(web_server, "_is_dashboard_plugin_active", lambda _item: True)

    assert client.get("/api/desktop/plugins/example/bundle").status_code == 404


def test_desktop_bundle_rejects_oversize_source(client, monkeypatch, tmp_path):
    plugin = _plugin(tmp_path)
    (tmp_path / "plugin" / "dashboard" / "dist" / "desktop.js").write_text(
        "x" * (2 * 1024 * 1024 + 1), encoding="utf-8"
    )
    monkeypatch.setattr(web_server, "_get_dashboard_plugins", lambda: [plugin])
    monkeypatch.setattr(web_server, "_is_dashboard_plugin_active", lambda _item: True)

    assert client.get("/api/desktop/plugins/example/bundle").status_code == 413


def test_discovery_ignores_desktop_entry_traversal(monkeypatch, tmp_path):
    home = tmp_path / "home"
    dashboard = home / "plugins" / "unsafe" / "dashboard"
    dashboard.mkdir(parents=True)
    (dashboard / "manifest.json").write_text(json.dumps({
        "name": "unsafe",
        "desktop": {"api_version": 1, "path": "/unsafe", "entry": "../../outside.js"},
    }), encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    web_server._dashboard_plugins_cache = None

    plugin = next(item for item in web_server._discover_dashboard_plugins() if item["name"] == "unsafe")

    assert plugin["desktop"] is None


@pytest.mark.parametrize(
    "desktop",
    [
        {"api_version": 2, "path": "/unsafe", "entry": "dist/desktop.js"},
        {"api_version": 1, "path": "unsafe", "entry": "dist/desktop.js"},
        {"api_version": 1, "path": "/unsafe", "entry": "dist/desktop.txt"},
        {"api_version": 1, "path": "/unsafe", "entry": "dist/desktop.js", "position": "sideways"},
        {"api_version": 1, "path": "/unsafe", "entry": "dist/desktop.js", "label": ""},
        {"api_version": 1, "path": "/unsafe", "entry": "dist/desktop.js", "icon": "bad icon"},
    ],
)
def test_discovery_ignores_invalid_desktop_contract(monkeypatch, tmp_path, desktop):
    home = tmp_path / "home"
    dashboard = home / "plugins" / "unsafe" / "dashboard"
    dashboard.mkdir(parents=True)
    (dashboard / "manifest.json").write_text(
        json.dumps({"name": "unsafe", "desktop": desktop}), encoding="utf-8"
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    web_server._dashboard_plugins_cache = None

    plugin = next(item for item in web_server._discover_dashboard_plugins() if item["name"] == "unsafe")

    assert plugin["desktop"] is None
