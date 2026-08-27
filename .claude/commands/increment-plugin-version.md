# Increment Plugin Versions

Bump the patch version of every plugin in this marketplace. Does NOT touch `pyproject.toml` - the PyPI version is managed by `make publish`, and a release syncs the plugins to it. Use this only for a plugin-only bump outside a release; `/release` does its own sync.

## What to update

22 version strings across 15 files, all set to the same number:

- `plugins/*/.claude-plugin/plugin.json` - one `"version"` per plugin
- `plugins/*/kimi.plugin.json` - one `"version"` per plugin, the Kimi manifests
- `.claude-plugin/marketplace.json` - `metadata.version` plus the `"version"` in each plugin entry

Do not hand-count. Derive the set from the tree, so a plugin added later is picked up on its own:

```bash
PREV=<current version>; NEW=<PREV with PATCH incremented>
grep -rl "\"$PREV\"" --include=*.json . | grep -v node_modules | xargs sed -i "s/\"$PREV\"/\"$NEW\"/g"
grep -rn "\"$NEW\"" --include=*.json . | grep -v node_modules | wc -l   # expect 22
grep -rn "\"$PREV\"" --include=*.json . | grep -v node_modules | wc -l  # expect 0
```

Never bump `kimi-marketplace.json`'s top-level `"version": "2"` - that is the Kimi marketplace SCHEMA version, not a plugin version. Matching on `$PREV` rather than on every `"version"` key is what keeps the sweep off it.

## Steps

1. Read the current version from `.claude-plugin/marketplace.json` `metadata.version`
2. Parse as semver and increment PATCH
3. Run the sweep above; confirm the two counts, 22 new and 0 stale
4. Report: `Plugin versions bumped: X.Y.Z -> X.Y.(Z+1)`

## Rules

- All plugin versions stay in sync - one number across every file
- Only bump PATCH unless the user explicitly asks for MINOR or MAJOR
- Do NOT touch `pyproject.toml` - `make publish` owns the library version
- Do NOT commit - update the files and report
