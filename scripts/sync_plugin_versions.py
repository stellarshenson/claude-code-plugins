#!/usr/bin/env python3
"""Keep the package and all plugin descriptors on the same release version."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
VERSION_PATTERN = re.compile(r'^(version\s*=\s*")([^"\n]+)(")$', re.MULTILINE)
JSON_VERSION_PATTERN = re.compile(r'("version"\s*:\s*")[^"]+(")')


def read_package_version() -> str:
    match = VERSION_PATTERN.search(PYPROJECT.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"Could not find project version in {PYPROJECT}")
    return match.group(2)


def bump_patch(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Expected a three-part release version, got {version!r}")
    return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"


def write_package_version(version: str) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    updated, count = VERSION_PATTERN.subn(rf"\g<1>{version}\g<3>", text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not update project version in {PYPROJECT}")
    PYPROJECT.write_text(updated, encoding="utf-8")


def versioned_files() -> list[Path]:
    files = [
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
    ]
    for plugin_dir in sorted((ROOT / "plugins").iterdir()):
        files.extend(
            [
                plugin_dir / ".claude-plugin" / "plugin.json",
                plugin_dir / ".codex-plugin" / "plugin.json",
                plugin_dir / "kimi.plugin.json",
            ]
        )
    return files


def sync_json_versions(version: str) -> int:
    changed = 0
    for path in versioned_files():
        if not path.is_file():
            raise FileNotFoundError(f"Expected plugin descriptor is missing: {path}")
        text = path.read_text(encoding="utf-8")
        updated, count = JSON_VERSION_PATTERN.subn(rf"\g<1>{version}\g<2>", text)
        if count == 0:
            raise RuntimeError(f"No JSON version field found in {path}")
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--bump", action="store_true", help="increment the patch version")
    group.add_argument("--version", help="set an explicit release version")
    args = parser.parse_args()

    current = read_package_version()
    version = args.version or (bump_patch(current) if args.bump else current)
    if args.bump or args.version:
        write_package_version(version)
    changed = sync_json_versions(version)
    print(f"Synchronized plugin descriptors to {version} ({changed} files changed).")


if __name__ == "__main__":
    main()
