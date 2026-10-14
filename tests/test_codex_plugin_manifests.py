"""Validate the Codex marketplace and manifests shipped with the repository."""

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"


def test_codex_marketplace_lists_existing_plugins() -> None:
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    listed_plugins = marketplace["plugins"]
    package_version = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )["metadata"]["version"]

    assert listed_plugins
    assert marketplace["version"] == package_version
    for entry in listed_plugins:
        source = ROOT / entry["source"]["path"].removeprefix("./")
        manifest_path = source / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert manifest["name"] == entry["name"]
        assert entry["version"] == package_version
        assert manifest["version"] == package_version
        assert manifest["skills"] == "./skills/"
        assert (source / "skills").is_dir()


def test_every_plugin_has_codex_manifest() -> None:
    plugin_dirs = sorted((ROOT / "plugins").iterdir())
    package_version = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )["metadata"]["version"]

    assert plugin_dirs
    for plugin_dir in plugin_dirs:
        manifests = [
            plugin_dir / ".claude-plugin" / "plugin.json",
            plugin_dir / ".codex-plugin" / "plugin.json",
            plugin_dir / "kimi.plugin.json",
        ]
        for manifest_path in manifests:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            assert manifest["name"] == plugin_dir.name
            assert manifest["version"] == package_version
            assert manifest["description"]
            if manifest_path.name == "plugin.json" and manifest_path.parent.name == ".codex-plugin":
                assert manifest["skills"] == "./skills/"
            elif manifest_path.name == "kimi.plugin.json":
                assert manifest["skills"] == "./skills/"
