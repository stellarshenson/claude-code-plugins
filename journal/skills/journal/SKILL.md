---
name: journal
description: Journal entry management and archiving. Auto-triggered after completing substantive work to ensure entries are appended correctly. Enforces entry format, append-only rule, continuous numbering, and archiving.
---

# Journal Management

Manages `.claude/JOURNAL.md` entries. Journal = project audit trail — every substantive task gets entry.

## CRITICAL: Append-Only Rule

New entries MUST append at END of file. NEVER insert between existing entries. Last entry = most recent work. After writing, VERIFY append by reading last 5 lines.

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
| **Extended** | ~250-350 | ONLY when justified: architectural decisions, cross-cutting refactors, multi-system debugging sagas, new subsystems with non-obvious design choices |

**Default is Standard.** Match the user's own summary length when they provide one — do NOT inflate a 5-bullet summary into a 400-word entry. Standard entries read like a colleague's coffee recap: what was added, headline numbers, why it matters, one or two file paths. Skip the directory listing, skip the per-function commentary, skip the reasoning chain.

**Extended entries are the exception, not the rule.** Reach for Extended ONLY when the reader genuinely needs context the code alone cannot carry — a novel algorithm, a platform migration, a multi-iteration debugging story where the dead-ends matter, or a design decision future readers will second-guess without the reasoning. "I touched a lot of files" is NOT a justification. "This was hard" is NOT a justification. If you find yourself writing a 400-word entry for a feature add, downgrade to Standard.

**Length check before saving**: count words in the entry body (after `**Result**:`). Over 150 words? Ask: "does the extra context carry information the user cannot get from the code?". If no, cut ruthlessly. If yes, keep and justify mentally.

## What to Log

**Log**: document changes, features, investigations with findings, diagram work
**Skip**: git commits, file cleanup, maintenance. State: "Not logging to journal: <reason>"

## Verification After Writing

After appending, ALWAYS verify:
1. Read last entry in file
2. Confirm matches what just written
3. Confirm entry number one higher than previous
4. Confirm no entries displaced or overwritten

## Examples

See `references/examples.md` — Standard and Extended entries with before/after examples showing when to downgrade a bloated draft.

## CLI Tools (deterministic, no LLM)

`journal-tools` validates, archives, and sorts journal files. Pure string parsing - no generative AI. Use BEFORE committing to catch format drift, and for archiving/sorting instead of manual edits.

### Check

```bash
journal-tools check .claude/JOURNAL.md
```

Validates: continuous numbering, ascending order, entry format (title + Result body), word count tiers. Entries over 150 words = warning (standard exceeded). Over 400 words = error (extended exceeded). Exit code 0 = clean, 1 = errors found.

**MANDATORY**: run `journal-tools check` after writing entries to catch word-count drift. If the checker flags an entry, condense before committing.

### Archive

```bash
journal-tools archive .claude/JOURNAL.md
```

Moves entries to `JOURNAL_ARCHIVE.md` when count exceeds threshold (default 40). Keeps last 20 in main file. Appends to existing archive. Maintains continuous numbering. Flags: `--keep-last N`, `--threshold N`, `--archive-path PATH`.

Use this instead of manual archive edits - prevents numbering mistakes and header corruption.

### Sort

```bash
journal-tools sort .claude/JOURNAL.md --dry-run
```

Re-numbers entries sequentially. Fixes gaps (e.g. 1, 2, 5 -> 1, 2, 3) and ordering (e.g. 3 before 2 -> 2 before 3). Use `--dry-run` to preview, omit to write in-place. Flag: `--start-from N`.

## Archiving

**Trigger**: exceeds 40 entries OR user requests. Prefer `journal-tools archive` CLI over manual editing.
1. Move older entries to `.claude/JOURNAL_ARCHIVE.md`
2. Keep last 20 entries in main file
3. Add link at top: `**Note**: Entries 1-N have been archived`
4. Maintain continuous numbering — NEVER reset
