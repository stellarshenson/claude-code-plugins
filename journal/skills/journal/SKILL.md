---
name: journal
description: Manage `.claude/JOURNAL.md`. **Auto-triggers on ANY mention of "journal"** — questions about the journal, entry format, word-count tiers, archiving, the `/journal:*` commands, or the `journal-tools` CLI. Also triggers on "update journal", "add journal entry", "log this", "journal this", "record this in the journal", "create journal", "init journal", "archive journal", "prune journal", or after finishing substantive work that should be logged. Enforces format, append-only, continuous numbering, word-count tiers, post-write `journal-tools check` validation, archiving.
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# Journal

Project audit trail. Every substantive task = one entry. Append at END. Last entry = newest.

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

```
<N>. **Task - <short depiction>** (v1.2.3): one-line summary<br>
    **Result**: dense paragraph - problem, solution, files/libraries, verification
```

Version tag only if project versioned (`package.json` / `pyproject.toml` / `Cargo.toml`).

## Levels

| Level | Words | When |
|-------|-------|------|
| Standard | ~70-120 | DEFAULT. Feature, fix, multi-file change, investigation |
| Extended | ~250-350 | ONLY: architectural decision, platform migration, multi-iteration debug, novel algorithm |

Match user's own summary length. 5-bullet summary → not 400 words. "I touched lots of files" = not Extended. "This was hard" = not Extended.

Length check before save: count words after `**Result**:`. Over 150? Cut unless extra context carries info unavailable from code.

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
