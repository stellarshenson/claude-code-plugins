# Increment Plugin Versions

Bump the patch version number for all plugins in this marketplace.

## Files to update

1. `auto-build-claw/.claude-plugin/plugin.json` - `"version"` field
2. `devils-advocate/.claude-plugin/plugin.json` - `"version"` field
3. `datascience/.claude-plugin/plugin.json` - `"version"` field
4. `journal/.claude-plugin/plugin.json` - `"version"` field
5. `.claude-plugin/marketplace.json` - `"version"` field in ALL plugin entries AND the marketplace `metadata.version`

## Steps

1. Read the current version from `.claude-plugin/marketplace.json` metadata.version
2. Parse as semver (MAJOR.MINOR.PATCH)
3. Increment PATCH by 1
4. Update ALL version strings (4 plugin.json + 4 marketplace entries + 1 metadata) to the new version
5. Report: `Plugin versions bumped: X.Y.Z -> X.Y.(Z+1)`

## Rules

- ALL plugin versions MUST stay in sync (same version across all files)
- Only bump PATCH unless the user explicitly asks for MINOR or MAJOR
- Do NOT commit - just update the files and report
