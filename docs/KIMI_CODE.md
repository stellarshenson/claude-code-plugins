# Kimi Code CLI Integration - Agent Handoff

Note for the agent working on this repository. Written 2026-07-30 by a Kimi Code CLI session at the user's request. Read this before touching any `kimi*.json` file here

## What Was Done and Why

This repo ships Claude Code plugins. Kimi Code CLI can load the same plugins, but only through its own manifest format - it does not read `.claude-plugin/plugin.json`. The plugin *content* (skills, commands, agents) is fully compatible as-is; only the wrapper differs

Files added (all additive, no existing file modified):

- `plugins/journal/kimi.plugin.json`, `plugins/devils-advocate/kimi.plugin.json`, `plugins/datascience/kimi.plugin.json`, `plugins/svg-infographics/kimi.plugin.json`, `plugins/document-processing/kimi.plugin.json`, `plugins/autobuild/kimi.plugin.json` - one Kimi manifest per plugin, mirroring the metadata of the sibling `.claude-plugin/plugin.json`
- `kimi-marketplace.json` at repo root - Kimi marketplace catalog listing all 6 plugins, so the suite installs from one file

Field mapping per manifest:

- `skills: "./skills/"`, `commands: "./commands/"` - same dirs Claude uses, no content changes
- `agents: "./agents/"` - `autobuild` and `devils-advocate` have agents
- `interface.displayName` / `shortDescription` / `developerName` - Kimi `/plugins` panel display metadata
- `version` - static copy of the Claude manifest version at the time of writing (`1.6.37`)

Key format facts:

- Kimi manifest must be `kimi.plugin.json` at plugin root (or `.kimi-plugin/plugin.json`); `kimi.plugin.json` wins if both exist
- `name` must match `[a-z0-9][a-z0-9_-]{0,63}`
- All paths must stay inside the plugin root after symlink resolution - symlinks pointing outside are rejected, so manifests must live in the tree, not link to it
- Commands register as `/<plugin>:<command>` in both CLIs - `/journal:update` works identically in Claude and Kimi
- Skills and commands are picked up recursively from the declared dirs
- Hooks and MCP servers were not declared - no plugin here uses them; Kimi hook schema differs from Claude's `hooks.json`, so port deliberately if ever needed

## How to Install in Kimi

In the Kimi TUI (there is no headless CLI equivalent):

```
/plugins marketplace /home/lab/workspace/private/ai-assistants/claude-code-plugins/kimi-marketplace.json
```

or per plugin: `/plugins install <path-to-plugin-dir>`, then `/reload` or start a new session

Install copies the plugin into `~/.kimi-code/plugins/managed/<id>/` - later edits in this repo do NOT propagate; users must reinstall to pick up changes

## How to Release / Maintain

When cutting a plugin release:

1. Bump `version` in the plugin's `kimi.plugin.json` alongside `.claude-plugin/plugin.json` and `marketplace.json` - or delete the field; it is display-only metadata
2. If `skills/`, `commands/`, or `agents/` dirs are added, removed, or renamed, update the corresponding fields in `kimi.plugin.json`
3. If a plugin is added to or dropped from the suite, update `kimi-marketplace.json` (each entry needs `id`, `displayName`, `source`)
4. Keep `description` / `keywords` roughly in sync with the Claude manifest - the Kimi skill router uses descriptions to auto-invoke skills
5. No Kimi-specific CI needed - the manifests are static JSON; validating them is a `python -m json.tool` parse at most

## Related State Outside This Repo

- `~/.claude/plugins/cache/mwguerra-marketplace/article-writer/1.0.0/kimi.plugin.json` and `~/.claude/plugins/cache/claude-plugins-official/frontend-design/5998047d8ddd/kimi.plugin.json` - same treatment applied to two installed third-party plugins that do not live in this repo; these are local-only files, wiped if the cache is rebuilt
- Kimi-side user skills/commands/AGENTS.md imports from `~/.claude` live under `~/.agents/` - unrelated to this repo, mentioned only so nobody re-does that work
