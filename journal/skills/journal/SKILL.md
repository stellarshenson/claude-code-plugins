---
name: journal
description: Manage `.claude/JOURNAL.md`. **Auto-triggers on ANY mention of "journal"** — questions about the journal, entry format, word-count tiers, archiving, the `/journal:*` commands, or the `journal-tools` CLI. Also triggers on "update journal", "add journal entry", "log this", "journal this", "record this in the journal", "create journal", "init journal", "archive journal", "prune journal", or after finishing substantive work that should be logged. Enforces format, append-only, continuous numbering, word-count tiers, post-write `journal-tools check` validation, archiving.
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Journal

Project audit trail. Every substantive task = one entry. Append at END. Last entry = newest.

## Install (MANDATORY)

```bash
pip install stellars-claude-code-plugins
```

Ships `journal-tools` CLI (`check`, `sort`, `archive`). Verify: `journal-tools --help`. Without install no post-write validation, no deterministic archive, no renumber.

## Commands

| Command | Use |
|---------|-----|
| `/journal:create` | INIT empty journal. Backfill from conversation context. Refuses if file exists. |
| `/journal:update` | DEFAULT. Append new entry. Extend last entry only if same task, pre-release. |
| `/journal:archive` | Move old entries to `JOURNAL_ARCHIVE.md`. Triggered >40 entries. |

No ambiguity. `create` = scaffold once. `update` = every write after.

## Append-only

Never insert between entries. Never renumber. Never reorder. Numbers monotonic.

After write: read last 5 lines. Confirm match.

## Entry format

Standard (default):
```
<N>. **Task - <short depiction>** (v1.2.3): one-line summary<br>
    **Result**: dense paragraph - problem, solution, files/libraries, verification
```

Extended (opt-in via `[Extended]` marker after `Task`):
```
<N>. **Task [Extended] - <short depiction>** (v1.2.3): one-line summary<br>
    **Result**: 250-400 word paragraph
```

Version tag only if project versioned (`package.json` / `pyproject.toml` / `Cargo.toml`).

## Levels

| Level | Marker | Words | When |
|-------|--------|-------|------|
| Standard | none | <= 150 | DEFAULT. Feature, fix, multi-file change, investigation |
| Extended | `[Extended]` | 150-400 | ONLY: architectural decision, platform migration, multi-iteration debug, novel algorithm |

Match the user's own summary length. 5-bullet summary -> not 400 words. "I touched lots of files" = not Extended. "This was hard" = not Extended.

Marker is mandatory for Extended. Without it `journal-tools check` warns over 150 words and tells you to either condense or add `[Extended]`. With it the gate stays silent in the [150, 400] band but warns under 150 (false advertising) or over 400 (too long for any tier).

## Style

Telegram-style terse language by default - drop articles ("the" / "a"), drop copulas ("is" / "are" / "was"), dense paragraphs over multi-bullet structure, file paths and function names in backticks.

**Always keep the WHY.** Future-you (or another agent) reading this entry six months later needs to understand WHY the implementation or work was done, not just WHAT was done. The code itself shows what changed; the journal carries the rationale that does NOT survive in `git log` / `git blame` / the file content. Specifically keep:

- **Trigger** - what prompted the work (a user report, a forensic finding, a CI failure, a benchmark regression)
- **Why this approach over alternatives** - the design decision and its constraint ("picked A over B because of C")
- **Gotchas / non-obvious constraints** - things that surprised you and will surprise the next reader if undocumented
- **Cause-and-effect chains** - "X required Y because Z" - so the reader can reconstruct the reasoning when the code alone is insufficient

Drop ceremonial connective tissue, hedging, restated obvious context, and bullet-list expansions of single ideas. Keep load-bearing reasoning - especially the trigger and the why-this-approach.

Bad (verbose, no reasoning): "I made some changes to the validator and updated some files."

Bad (terse but no WHY): "Validator updated. Tests green."

Good (terse + WHY preserved): "Validator now honours `[Extended]` marker - silent in [150, 400] band when marked, warns otherwise. **Trigger**: agents kept inflating Standard entries to ~200 words to clear word-count warnings instead of either condensing or marking intent; the gate became noise. **Why this design**: the marker makes intent explicit and machine-checkable in one regex; alternative was raising STANDARD_TARGET globally, rejected because it would erode the discipline that pushes Standard entries to the 70-120 sweet spot."

## What to log

Log: document changes, features, investigations with findings, diagram work.

Skip: git commits, file cleanup, version bumps, maintenance. State: "Not logging to journal: <reason>".

## Examples

See `references/examples.md`. Standard + Extended with before/after.

## CLI tools

`journal-tools` - deterministic validation, archive, sort. Pure string parsing. Run BEFORE commit.

### check

```bash
journal-tools check .claude/JOURNAL.md
```

Validates: continuous numbering, ascending order, format, word count tiers. Length over target = warning only (never error). Format violations (duplicate number, out-of-order, missing title) = error. Exit 0 = no errors, 1 = format errors.

MANDATORY after write. Word-count warning → condense if cheap. Format error → fix before commit.

### archive

```bash
journal-tools archive .claude/JOURNAL.md
```

Moves entries to `JOURNAL_ARCHIVE.md` when count exceeds threshold (default 40). Keeps last 20 in main. Appends to existing archive. Maintains continuous numbering.

Flags: `--keep-last N`, `--threshold N`, `--archive-path PATH`.

Prefer over manual edit.

### sort

```bash
journal-tools sort .claude/JOURNAL.md --dry-run
```

Re-numbers sequentially. Fixes gaps (1,2,5 → 1,2,3) and ordering. `--dry-run` previews. Omit to write in-place. Flag: `--start-from N`.

## Archiving

Trigger: >40 entries OR user requests. Prefer `journal-tools archive`.

1. Move older entries to `.claude/JOURNAL_ARCHIVE.md`
2. Keep last 20 in main
3. Add link at top: `**Note**: Entries 1-N archived to JOURNAL_ARCHIVE.md`
4. Maintain continuous numbering. NEVER reset.
