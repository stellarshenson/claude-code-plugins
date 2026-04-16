---
name: journal
description: Journal entry management and archiving. Auto-triggered after completing substantive work to ensure entries are appended correctly. Enforces entry format, append-only rule, continuous numbering, and archiving.
---

# Journal Management

Manages `.claude/JOURNAL.md`. Journal = project audit trail. Every substantive task gets entry.

## CRITICAL: Append-Only Rule

New entries MUST append at END. NEVER insert between existing entries. Last entry = most recent. After writing, VERIFY by reading last 5 lines.

## Entry Format

```
<number>. **Task - <short 3-5 word depiction>** (v1.2.3): task description<br>
    **Result**: summary of work done
```

Version tag `(v1.2.3)` only for versioned projects.


## Entry Levels

| Level | Words | When |
|-------|-------|------|
| **Standard** | ~70-120 | DEFAULT. Features, bug fixes, multi-file changes, investigations |
| **Extended** | ~250-350 | ONLY when justified: architectural decisions, cross-cutting refactors, multi-system debugging, new subsystems with non-obvious design |

**Default: Standard.** Match user's own summary length. Do NOT inflate a 5-bullet summary into 400 words. Standard entries read like a colleague's coffee recap: what was added, headline numbers, why it matters, one or two file paths. Skip directory listings, per-function commentary, reasoning chains.

**Extended = exception.** Reach for Extended ONLY when the reader needs context the code cannot carry - novel algorithm, platform migration, multi-iteration debugging where dead-ends matter, design decision future readers will second-guess. "I touched a lot of files" = NOT justification. "This was hard" = NOT justification. Writing 400 words for a feature add? Downgrade to Standard.

**Length check before saving**: count words after `**Result**:`. Over 150? Ask: "does extra context carry information the user cannot get from code?". No → cut. Yes → keep.

## What to Log

- **Log**: document changes, features, investigations with findings, diagram work
- **Skip**: git commits, file cleanup, maintenance. State: "Not logging to journal: <reason>"

## Verification After Writing

1. Read last entry in file
2. Confirm matches what was written
3. Confirm number is one higher than previous
4. Confirm no entries displaced or overwritten

## Examples

See `references/examples.md` - Standard and Extended with before/after.

## CLI Tools (deterministic, no LLM)

`journal-tools` validates, archives, sorts. Pure string parsing. Use BEFORE committing to catch drift.

### Check

```bash
journal-tools check .claude/JOURNAL.md
```

Validates: continuous numbering, ascending order, format (title + Result), word count tiers. Over 150 words = warning. Over 400 = error. Exit 0 = clean, 1 = errors.

**MANDATORY**: run `journal-tools check` after writing. Flagged → condense before commit.

### Archive

```bash
journal-tools archive .claude/JOURNAL.md
```

Moves entries to `JOURNAL_ARCHIVE.md` when count exceeds threshold (default 40). Keeps last 20 in main. Appends to existing archive. Maintains continuous numbering. Flags: `--keep-last N`, `--threshold N`, `--archive-path PATH`.

Use instead of manual archive edits.

### Sort

```bash
journal-tools sort .claude/JOURNAL.md --dry-run
```

Re-numbers sequentially. Fixes gaps (1, 2, 5 → 1, 2, 3) and ordering (3 before 2 → 2 before 3). `--dry-run` previews. Omit to write in-place. Flag: `--start-from N`.

## Archiving

**Trigger**: exceeds 40 entries OR user requests. Prefer `journal-tools archive` over manual edit.
1. Move older entries to `.claude/JOURNAL_ARCHIVE.md`
2. Keep last 20 in main
3. Add link at top: `**Note**: Entries 1-N have been archived`
4. Maintain continuous numbering. NEVER reset
