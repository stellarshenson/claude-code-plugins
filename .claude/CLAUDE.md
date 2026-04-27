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

**Install `journal-tools` if missing** → `pip install --user stellars-claude-code-plugins` (ships `journal-tools` on `~/.local/bin`). Plugin README at `~/.claude/plugins/cache/stellarshenson-marketplace/journal/<version>/README.md`.

**`journal-tools check .claude/JOURNAL.md` after EVERY write** - exit 0 + no errors is the bar. Warnings (word-count nudges) non-blocking BUT drive a condense-pass when they fire on the just-appended entry.

No manual word-count checks - CLI is deterministic; catches numbering / ordering / format drift manual checks miss.

Same rule for `/release` step 5 - invokes `/journal:update`. Never inline-edit during release; gate exists to keep release journals consistent with day-to-day appends.

## Project context

This repo is the `stellars-claude-code-plugins` marketplace - a multi-plugin distribution that publishes both a PyPI Python package (deterministic CLIs in `src/stellars_claude_code_plugins/`) and six Claude Code plugins (`autobuild/`, `datascience/`, `devils-advocate/`, `document-processing/`, `journal/`, `svg-infographics/`). Plugin versions are kept in lockstep across all six `plugin.json` files plus the seven version strings in `.claude-plugin/marketplace.json` (metadata + 6 entries).

When releasing, follow `/release` exactly: lint+format → tests → `make publish` (auto-bumps `pyproject.toml` patch + uploads wheel) → `/increment-plugin-version` (one PATCH bump across 13 strings) → `/journal:update` → commit specific files (never `git add -A`) → push.
