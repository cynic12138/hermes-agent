from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".hermes" / "plugins" / "product_creative" / "scripts" / "validate_distribution.py"
SPEC = importlib.util.spec_from_file_location("product_creative_distribution_validator", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

INSTALL_SCRIPT = ROOT / ".hermes" / "plugins" / "product_creative" / "scripts" / "verify_distribution_install.py"
INSTALL_SPEC = importlib.util.spec_from_file_location("product_creative_distribution_install", INSTALL_SCRIPT)
assert INSTALL_SPEC and INSTALL_SPEC.loader
installer = importlib.util.module_from_spec(INSTALL_SPEC)
INSTALL_SPEC.loader.exec_module(installer)
EXPORT_SCRIPT = (
    ROOT
    / ".hermes"
    / "plugins"
    / "product_creative"
    / "scripts"
    / "export_distribution.ps1"
)
PYTHON_EXPORT_SCRIPT = EXPORT_SCRIPT.with_suffix(".py")


def _load_exporter():
    spec = importlib.util.spec_from_file_location(
        "product_creative_distribution_exporter", PYTHON_EXPORT_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _distribution(tmp_path: Path) -> Path:
    root = tmp_path / "distribution"
    bundle = root / "dashboard" / "dist" / "desktop.js"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("window.bundle = true\n", encoding="utf-8")
    (root / "plugin.yaml").write_text("name: product_creative\nversion: 9.1.0-alpha.1\n", encoding="utf-8")
    (root / "dashboard" / "manifest.json").write_text(
        json.dumps({"name": "product_creative", "version": "9.1.0-alpha.1"}), encoding="utf-8"
    )
    source = {
        "source_commit": "abc123",
        "plugin_version": "9.1.0-alpha.1",
        "desktop_sdk_version": 1,
        "desktop_bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "payload_sha256": validator.payload_hash(root),
    }
    (root / "SOURCE.json").write_text(json.dumps(source), encoding="utf-8")
    return root


def test_distribution_validator_accepts_consistent_safe_payload(tmp_path):
    root = _distribution(tmp_path)

    assert validator.validate(root, expected_version="9.1.0-alpha.1", expected_commit="abc123") == []


def test_distribution_validator_reports_paths_without_exposing_secrets(tmp_path):
    root = _distribution(tmp_path)
    secret = "sk-this-value-must-never-appear-in-the-report"
    (root / "products").mkdir()
    (root / "products" / "runtime.sqlite3").write_text("runtime", encoding="utf-8")
    (root / "config.py").write_text(f'api_key = "{secret}"\n', encoding="utf-8")

    errors = validator.validate(root)
    report = "\n".join(errors)

    assert "forbidden-path:products/runtime.sqlite3" in errors
    assert "literal-secret:config.py:1" in errors
    assert secret not in report


def test_offline_probe_pythonpath_keeps_repo_and_installed_dependencies(monkeypatch, tmp_path):
    extra_site = tmp_path / "extra-site"
    system_site = tmp_path / "system-site"
    user_site = tmp_path / "user-site"
    extra_site.mkdir()
    system_site.mkdir()
    user_site.mkdir()
    monkeypatch.setattr(installer.site, "getsitepackages", lambda: [str(system_site), str(system_site)])
    monkeypatch.setattr(installer.site, "getusersitepackages", lambda: str(user_site))

    values = installer._probe_pythonpath([str(extra_site), "", str(system_site)]).split(installer.os.pathsep)

    assert values == [str(installer.REPO_ROOT), str(extra_site), str(system_site), str(user_site)]


def test_cross_platform_exporter_includes_uncommitted_first_party_sources():
    exporter = _load_exporter()

    assert exporter.GIT_SOURCE_ARGS == (
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
        ".hermes/plugins/product_creative",
    )


def test_powershell_exporter_is_only_a_compatibility_wrapper():
    script = EXPORT_SCRIPT.read_text(encoding="utf-8")

    assert "export_distribution.py" in script
    assert "ls-files --cached --others --exclude-standard" not in script


def test_exporter_rejects_output_inside_or_above_repository(tmp_path):
    exporter = _load_exporter()

    with pytest.raises(ValueError, match="outside the source repository"):
        exporter.assert_safe_output_directory(ROOT / "unsafe-export", ROOT)
    with pytest.raises(ValueError, match="outside the source repository"):
        exporter.assert_safe_output_directory(ROOT.parent, ROOT)

    assert exporter.assert_safe_output_directory(tmp_path / "safe-export", ROOT) == (
        tmp_path / "safe-export"
    ).resolve()


def test_exporter_filters_runtime_generated_and_distribution_implementation_files():
    exporter = _load_exporter()

    assert exporter._include_source("plugin.py") is True
    assert exporter._include_source("desktop_ui/index.js") is True
    assert exporter._include_source("runtime_data/workspace.json") is False
    assert exporter._include_source("dashboard/dist/desktop.js") is False
    assert exporter._include_source("scripts/export_distribution.py") is False
    assert exporter._include_source("products/private.sqlite3") is False


def test_cross_platform_exporter_produces_a_validated_distribution(tmp_path):
    exporter = _load_exporter()

    root = exporter.export_distribution(
        tmp_path / "distribution",
        expected_version="9.1.0-alpha.1",
    )
    source = json.loads((root / "SOURCE.json").read_text(encoding="utf-8"))

    assert source["source_commit"]
    assert source["plugin_version"] == "9.1.0-alpha.1"
    assert source["desktop_sdk_version"] == 1
    assert validator.validate(
        root,
        expected_version="9.1.0-alpha.1",
        expected_commit=source["source_commit"],
    ) == []
