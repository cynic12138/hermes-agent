"""Build the dependency-free Desktop plugin bundle."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "desktop_ui" / "index.js"
TARGET = ROOT / "dashboard" / "dist" / "desktop.js"
WEB_TARGET = ROOT / "dashboard" / "dist" / "backend-only.js"


def _plugin_desktop_contract() -> dict[str, object]:
    text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    block_match = re.search(r"(?ms)^desktop:\s*\n(?P<body>(?:^[ \t]+.*\n?)+)", text)
    if not block_match:
        raise SystemExit("plugin.yaml has no desktop contract")
    values: dict[str, object] = {}
    for key, raw in re.findall(r"(?m)^\s{2}([a-z_]+):\s*(.+?)\s*$", block_match.group("body")):
        value = raw.strip('"\'')
        values[key] = int(value) if key == "api_version" and value.isdigit() else value
    return values


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    if "__HERMES_DESKTOP_PLUGINS__.registerPage" not in source:
        raise SystemExit("Desktop bundle does not register a page")
    dashboard = json.loads((ROOT / "dashboard" / "manifest.json").read_text(encoding="utf-8"))
    plugin_desktop = _plugin_desktop_contract()
    dashboard_desktop = dashboard.get("desktop") or {}
    expected = {**dashboard_desktop, "entry": f"dashboard/{dashboard_desktop.get('entry', '')}"}
    for key in ("api_version", "path", "entry", "position", "label", "icon"):
        if plugin_desktop.get(key) != expected.get(key):
            raise SystemExit(f"Desktop contract mismatch for {key}")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(source, encoding="utf-8", newline="\n")
    WEB_TARGET.write_text("// Product Creative uses the native Desktop Plugin SDK.\n", encoding="utf-8", newline="\n")
    print(json.dumps({"path": str(TARGET), "sha256": hashlib.sha256(source.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
