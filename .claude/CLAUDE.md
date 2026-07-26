<!-- Project-specific Claude Code instructions for stellars-claude-code-plugins.
     Inherits from workspace-level config at /home/lab/workspace/.claude/CLAUDE.md
     (no-slop rule, GPU policy, mermaid/markdown standards, project-boundary
     rules, git/release/tagging policy, etc). Only the journal discipline is
     restated here because the project's own JOURNAL.md is the asset most at
     risk of bypassing the canonical plugin. -->

# Project: stellars-claude-code-plugins

This file extends workspace-level configuration with project-specific rules. See `/home/lab/workspace/.claude/CLAUDE.md` for the inherited base.

## MANDATORY - Journal discipline (no inline edits)

**NEVER `Edit` / `Write` on `.claude/JOURNAL.md` (or `JOURNAL_ARCHIVE.md`) directly.** Every append, in-place extension, archive flow → Stellars `journal` plugin only:

- `/journal:create` - first-time scaffold (refuses if file exists)
- `/journal:update` - every append or extension; auto-picks append vs extend
- `/journal:archive` - archive 1..N once file > 40 entries

`journal:journal` skill auto-triggers on any mention of "journal". Enforces format, append-only order, monotonic numbering, Standard/Extended word-count tiers. Inline edits bypass all of it; format drift cascades to the next agent.

**Follow the slash command literally**: read last entry → decide append-vs-extend → write per Standard format (~120 words; condense BEFORE submit, never ship 400+ word draft to "fix later") → `journal-tools check` → fix any error. `Edit` allowed ONLY for the specific append the slash command's procedure prescribes - never a starting point for "let me append a paragraph".

Reaching for `Edit` on `JOURNAL.md` without first invoking `/journal:update` → **stop, invoke slash command first**. No shortcut.

New entry → APPENDED at end of file. New numbers above old numbers = monotonicity break = process bug. Re-read last entry, append after its full body.

**Pre-flight install (MANDATORY, no asking, every plugin CLI)** → before invoking any `stellars-claude-code-plugins` CLI (`journal-tools`, `orchestrate`, `svg-infographics`, `render-png`, `document-processing`), always run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
REPO=$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2)
[ "$LIB" = "$REPO" ] && echo "toolkit $LIB" || echo "STALE: installed $LIB != repo $REPO - the CLI you are testing is not the code in this tree"
```

**The upgrade runs unconditionally.** An `import ... || install` guard never upgrades a version that already imports - that is precisely how this box reached library 1.5.5 while shipping plugins at 1.6.31, and how a session followed current skill docs into `unrecognized arguments: --svg` on a 26-release-old CLI. A green `--help` proves nothing; only the version compare does. In this repo the compare is against `pyproject.toml` (the CLI under test must be the code in this tree); in the shipped plugins it is against `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. Never skip. Never ask. Plugin README at `~/.claude/plugins/cache/stellarshenson-marketplace/journal/<version>/README.md`.

**`journal-tools check .claude/JOURNAL.md` after EVERY write** - exit 0 + no errors is the bar. Warnings (word-count nudges) non-blocking BUT drive a condense-pass when they fire on the just-appended entry.

No manual word-count checks - CLI is deterministic; catches numbering / ordering / format drift manual checks miss.

Same rule for `/release` step 5 - invokes `/journal:update`. Never inline-edit during release; gate exists to keep release journals consistent with day-to-day appends.

## Project context

This repo is the `stellars-claude-code-plugins` marketplace - a multi-plugin distribution that publishes both a PyPI Python package (deterministic CLIs in `src/stellars_claude_code_plugins/`) and six Claude Code plugins (`autobuild/`, `datascience/`, `devils-advocate/`, `document-processing/`, `journal/`, `svg-infographics/`). The library and all plugins share ONE synced version. The library leads: `pyproject.toml` `version` is the source of truth, and the 13 plugin strings (six `plugin.json` files + `marketplace.json` metadata + 6 entries) are set to match it.

When releasing, follow `/release` exactly: lint+format → tests → `make publish` (library leads - bumps `pyproject.toml` PATCH + uploads to PyPI; that number is `vN`) → sync the 13 plugin strings to `vN` (NEVER publish the library by hand with `uv build`/`twine` - always `make publish`) → `/journal:update` → commit specific files (never `git add -A`) → push. The PyPI/library version and the plugin version are the same number. Do NOT run `/increment-plugin-version` during release (it bumps only the plugin strings, leaving the library behind).

## Testing code that spawns `claude -p`

CI cannot run the `claude` binary. Subprocess spawn tests (standardize ACP loop, autobuild gatekeeper/readback gates) replay real recorded responses through a cassette layer at `tests/cassettes/claude_p/<hash>.json`. Re-record via `uv run python tests/record_claude_cassettes.py` (manual, requires `claude` on PATH). Full contract + scenarios in `docs/testing_claude_cassettes.md`. Default replay mode raises on missing cassettes - never silently fall back.
