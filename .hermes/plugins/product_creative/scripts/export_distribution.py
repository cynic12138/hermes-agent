"""Export a reviewed Product Creative distribution from the current worktree."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType


PLUGIN_RELATIVE = Path(".hermes/plugins/product_creative")
GIT_SOURCE_ARGS = (
    "ls-files",
    "--cached",
    "--others",
    "--exclude-standard",
    "--",
    PLUGIN_RELATIVE.as_posix(),
)
EXCLUDED_DIRECTORIES = {"__pycache__", ".pytest_cache", "runtime_data"}
EXCLUDED_SUFFIXES = {".pyc", ".sqlite", ".sqlite3", ".db", ".wal", ".shm"}
EXCLUDED_FILES = {
    "scripts/build_desktop_bundle.py",
    "scripts/export_distribution.py",
    "scripts/export_distribution.ps1",
    "scripts/validate_distribution.py",
    "scripts/verify_distribution_install.py",
}


def _load_validator(script_dir: Path) -> ModuleType:
    path = script_dir / "validate_distribution.py"
    spec = importlib.util.spec_from_file_location("product_creative_distribution_validator", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load distribution validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _same_or_child(candidate: Path, parent: Path) -> bool:
    candidate_text = os.path.normcase(str(candidate.resolve(strict=False)))
    parent_text = os.path.normcase(str(parent.resolve(strict=False)))
    try:
        return os.path.commonpath((candidate_text, parent_text)) == parent_text
    except ValueError:
        return False


def assert_safe_output_directory(output: Path, repo_root: Path) -> Path:
    output = output.expanduser().resolve(strict=False)
    repo_root = repo_root.resolve(strict=True)
    anchor = Path(output.anchor).resolve(strict=False)
    if output == anchor:
        raise ValueError("Refusing to export to a volume root")
    if _same_or_child(output, repo_root) or _same_or_child(repo_root, output):
        raise ValueError("Output directory must be outside the source repository and not its ancestor")
    return output


def _include_source(relative: str) -> bool:
    path = Path(relative)
    lowered_parts = {part.lower() for part in path.parts}
    normalized = path.as_posix()
    if lowered_parts & EXCLUDED_DIRECTORIES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if normalized.startswith("docs/") or normalized.startswith("dashboard/dist/"):
        return False
    if re.match(r"^scripts/verify_.*\.ps1$", normalized):
        return False
    return normalized not in EXCLUDED_FILES


def _run(command: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def export_distribution(
    output_directory: Path,
    *,
    expected_version: str = "",
    repo_root: Path | None = None,
) -> Path:
    script_dir = Path(__file__).resolve().parent
    repo_root = (repo_root or script_dir.parents[3]).resolve(strict=True)
    plugin_root = repo_root / PLUGIN_RELATIVE
    output = assert_safe_output_directory(output_directory, repo_root)

    _run([sys.executable, str(plugin_root / "scripts/build_desktop_bundle.py")], cwd=repo_root)

    plugin_text = (plugin_root / "plugin.yaml").read_text(encoding="utf-8-sig")
    version_match = re.search(r"(?m)^version:\s*([^\s]+)\s*$", plugin_text)
    if not version_match:
        raise RuntimeError("plugin.yaml has no version")
    version = version_match.group(1)
    dashboard = json.loads((plugin_root / "dashboard/manifest.json").read_text(encoding="utf-8-sig"))
    if dashboard.get("version") != version:
        raise RuntimeError("Plugin and dashboard versions differ")
    if expected_version and expected_version != version:
        raise RuntimeError(f"Release version {expected_version} does not match plugin version {version}")

    source_rows = _run(["git", "-C", str(repo_root), *GIT_SOURCE_ARGS], cwd=repo_root).splitlines()
    source_entries = sorted({row.strip() for row in source_rows if row.strip()})

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    prefix = f"{PLUGIN_RELATIVE.as_posix()}/"
    for entry in source_entries:
        normalized = entry.replace("\\", "/")
        if not normalized.startswith(prefix):
            raise RuntimeError(f"Git returned an unexpected plugin path: {normalized}")
        relative = normalized[len(prefix) :]
        if not _include_source(relative):
            continue
        source = repo_root / Path(normalized)
        if source.is_symlink():
            raise RuntimeError(f"Symlinked plugin source is not allowed: {relative}")
        if not source.is_file():
            raise RuntimeError(f"Plugin source is missing or not a file: {relative}")
        target = output / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    desktop_dist = output / "dashboard/dist"
    desktop_dist.mkdir(parents=True, exist_ok=True)
    for name in ("desktop.js", "backend-only.js"):
        source = plugin_root / "dashboard/dist" / name
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"Generated Desktop bundle is missing or unsafe: {name}")
        shutil.copy2(source, desktop_dist / name)
    shutil.copy2(repo_root / "LICENSE", output / "LICENSE")

    validator = _load_validator(script_dir)
    source_commit = _run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], cwd=repo_root)
    desktop_bundle = desktop_dist / "desktop.js"
    import hashlib

    source_metadata = {
        "source_repository": "cynic12138/hermes-agent",
        "source_commit": source_commit,
        "plugin_version": version,
        "desktop_sdk_version": 1,
        "desktop_bundle_sha256": hashlib.sha256(desktop_bundle.read_bytes()).hexdigest(),
        "payload_sha256": validator.payload_hash(output),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (output / "SOURCE.json").write_text(
        json.dumps(source_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    errors = validator.validate(output, expected_version=version, expected_commit=source_commit)
    if errors:
        raise RuntimeError("Distribution validation failed: " + ", ".join(errors))
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--expected-version", default="")
    args = parser.parse_args()
    try:
        output = export_distribution(
            args.output_directory,
            expected_version=args.expected_version,
        )
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
