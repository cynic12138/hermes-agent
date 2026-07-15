"""Offline install and API probe for an exported Product Creative plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import site
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"command failed: {command[0]} ({result.returncode})")


def _probe_pythonpath(search_paths: list[str] | None = None) -> str:
    candidates: list[str] = [str(REPO_ROOT)]
    system_sites = getattr(site, "getsitepackages", lambda: [])()
    user_site = site.getusersitepackages()
    for value in [*(sys.path if search_paths is None else search_paths), *system_sites, user_site]:
        path = str(value or "").strip()
        if path and Path(path).is_dir() and path not in candidates:
            candidates.append(path)
    return os.pathsep.join(candidates)


def _probe(workspace: Path) -> None:
    from hermes_cli import web_server
    from starlette.testclient import TestClient

    client = TestClient(web_server.app)
    client.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN
    workspace_headers = {"X-Hermes-Workspace-Root": str(workspace)}

    listed = client.get("/api/desktop/plugins")
    assert listed.status_code == 200
    manifests = [item for item in listed.json()["plugins"] if item["name"] == "product_creative"]
    assert len(manifests) == 1
    manifest = manifests[0]
    assert manifest["source"] == "user"
    assert manifest["version"] == "9.1.0-alpha.1"
    assert manifest["path"] == "/product-creative"

    bundle_response = client.get("/api/desktop/plugins/product_creative/bundle")
    assert bundle_response.status_code == 200
    bundle = bundle_response.json()
    assert bundle["entry"] == manifest["entry"]
    assert bundle["version"] == manifest["version"]
    assert hashlib.sha256(bundle["source"].encode("utf-8")).hexdigest() == bundle["sha256"]

    health = client.get("/api/plugins/product_creative/v1/health", headers=workspace_headers)
    assert health.status_code == 200
    assert health.json()["version"] == "9.1.0-alpha.1"

    sys.path.insert(0, str(Path(os.environ["HERMES_HOME"]) / "plugins"))
    from product_creative.infrastructure.sqlite.database import runtime_database
    from product_creative.workspace import workspace_scope

    product_id = "distribution-e2e"
    proposal_id = "proposal-e2e"
    with workspace_scope(workspace):
        database = runtime_database()
        product = workspace / ".hermes" / "product_creative" / "products" / product_id
        product.mkdir(parents=True, exist_ok=True)
        now = "2026-07-14T00:00:00+00:00"
        with database.transaction() as connection:
            connection.execute(
                "INSERT INTO products(product_id,workspace_path,created_at,updated_at) VALUES(?,?,?,?)",
                (product_id, str(product), now, now),
            )
            connection.execute(
                "INSERT INTO product_brain_versions(brain_version_id,product_id,version,state_json,content_hash,status,created_at,change_kind,trace_id) VALUES(?,?,1,'{}','e2e','current',?,'initial','')",
                ("brain-e2e", product_id, now),
            )
            connection.execute(
                "INSERT INTO writeback_proposals(proposal_id,product_id,status,risk_level,payload_json,created_at,updated_at) VALUES(?,?,'proposed','medium',?,?,?)",
                (proposal_id, product_id, json.dumps({"proposal_id": proposal_id, "product_id": product_id, "status": "proposed", "updates": []}), now, now),
            )

    review = client.get(
        f"/api/plugins/product_creative/v1/products/{product_id}/review-queue",
        headers=workspace_headers,
    )
    assert review.status_code == 200
    assert [item["proposal_id"] for item in review.json()["proposals"]] == [proposal_id]

    decision_url = f"/api/plugins/product_creative/v1/proposals/{proposal_id}/decision"
    first = client.post(
        decision_url,
        headers=workspace_headers,
        json={"product_id": product_id, "decision": "reject", "expected_version": 1},
    )
    assert first.status_code == 428
    confirmation_id = first.json()["output"]["confirmation_id"]
    with workspace_scope(workspace):
        with runtime_database().read_session() as connection:
            assert connection.execute("SELECT status FROM writeback_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()["status"] == "proposed"
            assert connection.execute("SELECT COUNT(*) value FROM recovery_events").fetchone()["value"] == 0

    confirmed = client.post(
        decision_url,
        headers=workspace_headers,
        json={
            "product_id": product_id,
            "decision": "reject",
            "expected_version": 1,
            "confirmed": True,
            "confirmation_id": confirmation_id,
            "reason": "offline distribution verification",
            "actor": "release-gate",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["success"] is True
    with workspace_scope(workspace):
        with runtime_database().read_session() as connection:
            assert connection.execute("SELECT status FROM writeback_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()["status"] == "rejected"
            assert connection.execute("SELECT COUNT(*) value FROM recovery_events").fetchone()["value"] == 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution", type=Path, nargs="?")
    parser.add_argument("--probe", type=Path)
    args = parser.parse_args()
    if args.probe:
        _probe(args.probe.resolve(strict=True))
        print("installed distribution probe passed")
        return 0
    if args.distribution is None:
        parser.error("distribution is required")

    distribution = args.distribution.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="product-creative-install-") as temporary:
        root = Path(temporary)
        repository = root / "repository"
        shutil.copytree(distribution, repository)
        _run(["git", "init", "--initial-branch=main"], repository)
        _run(["git", "add", "--all"], repository)
        _run(["git", "-c", "user.name=release-gate", "-c", "user.email=release-gate@example.invalid", "commit", "-m", "distribution e2e"], repository)

        home = root / "hermes-home"
        workspace = root / "workspace"
        home.mkdir()
        workspace.mkdir()
        os.environ["HERMES_HOME"] = str(home)
        from hermes_cli.plugins_cmd import _get_disabled_set, _get_enabled_set, _install_plugin_core, _save_disabled_set, _save_enabled_set

        target, manifest, name = _install_plugin_core(repository.as_uri(), force=False)
        assert target.is_dir() and manifest["version"] == "9.1.0-alpha.1" and name == "product_creative"
        enabled, disabled = _get_enabled_set(), _get_disabled_set()
        enabled.add(name)
        disabled.discard(name)
        _save_enabled_set(enabled)
        _save_disabled_set(disabled)

        allowed = {"COMSPEC", "PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR"}
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        env["HERMES_HOME"] = str(home)
        env["PYTHONPATH"] = _probe_pythonpath()
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--probe", str(workspace)],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode:
            diagnostic = "\n".join(part[-4000:] for part in (result.stdout, result.stderr) if part)
            raise RuntimeError(f"installed distribution probe failed ({result.returncode})\n{diagnostic}")
    print("offline distribution install passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
