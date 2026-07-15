"""Validate an exported Product Creative distribution without exposing matches."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FORBIDDEN_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".env",
    "artifacts",
    "cookies",
    "products",
    "prompts",
    "raw",
    "runtime_data",
    "secrets",
}
FORBIDDEN_SUFFIXES = {
    ".db", ".gif", ".jpeg", ".jpg", ".log", ".mov", ".mp4", ".png",
    ".pyc", ".shm", ".sqlite", ".sqlite3", ".wal", ".webp",
}
CONTENT_RULES = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider-key": re.compile(r"\b(?:sk|ak)-[A-Za-z0-9_-]{16,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "literal-secret": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|cookie|password|secret)\b\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"
    ),
    "personal-home": re.compile(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/(?:Users|home)/[^/\s]+)"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "cn-id": re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
}


def payload_hash(root: Path) -> str:
    rows = []
    paths = [item for item in root.rglob("*") if item.is_file() and item.name != "SOURCE.json"]
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest} {relative}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def validate(root: Path, *, expected_version: str = "", expected_commit: str = "") -> list[str]:
    errors: list[str] = []
    root = root.resolve(strict=True)
    required = ["plugin.yaml", "dashboard/manifest.json", "dashboard/dist/desktop.js", "SOURCE.json"]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"required:{relative}")

    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        parts = {part.lower() for part in path.relative_to(root).parts}
        if parts & FORBIDDEN_PARTS or path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.lower().endswith(("-wal", "-shm")):
            errors.append(f"forbidden-path:{relative}")
            continue
        if path.stat().st_size > 8 * 1024 * 1024:
            errors.append(f"oversize-file:{relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            errors.append(f"binary-file:{relative}")
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for rule, pattern in CONTENT_RULES.items():
                if pattern.search(line):
                    errors.append(f"{rule}:{relative}:{line_number}")

    if errors:
        return errors

    source = json.loads((root / "SOURCE.json").read_text(encoding="utf-8-sig"))
    dashboard = json.loads((root / "dashboard/manifest.json").read_text(encoding="utf-8-sig"))
    plugin_text = (root / "plugin.yaml").read_text(encoding="utf-8-sig")
    match = re.search(r"(?m)^version:\s*([^\s]+)\s*$", plugin_text)
    plugin_version = match.group(1) if match else ""
    versions = {plugin_version, str(dashboard.get("version", "")), str(source.get("plugin_version", ""))}
    if len(versions) != 1 or "" in versions:
        errors.append("metadata:version-mismatch")
    if expected_version and plugin_version != expected_version:
        errors.append("metadata:unexpected-version")
    if expected_commit and source.get("source_commit") != expected_commit:
        errors.append("metadata:unexpected-commit")

    bundle = (root / "dashboard/dist/desktop.js").read_bytes()
    if len(bundle) > 2 * 1024 * 1024:
        errors.append("metadata:desktop-bundle-oversize")
    if hashlib.sha256(bundle).hexdigest() != source.get("desktop_bundle_sha256"):
        errors.append("metadata:desktop-bundle-hash")
    if payload_hash(root) != source.get("payload_sha256"):
        errors.append("metadata:payload-hash")
    if source.get("desktop_sdk_version") != 1:
        errors.append("metadata:desktop-sdk-version")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-version", default="")
    parser.add_argument("--expected-commit", default="")
    args = parser.parse_args()
    errors = validate(args.directory, expected_version=args.expected_version, expected_commit=args.expected_commit)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("distribution validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
