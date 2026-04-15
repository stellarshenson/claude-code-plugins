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
| **Short** | ~80 | Bug fixes, config changes, typos |
| **Normal** | ~150-200 | Features, multi-file changes (DEFAULT) |
| **Extended** | ~350+ | Architectural changes, design decisions |

**Detail discipline**: full summaries with file paths, line counts, helper-function names, per-class test counts, exhaustive listings — ONLY in **Extended** entries. **Normal** entries = colleague's coffee recap — what added, headline numbers, why — not directory listing. **Short** entries = one fact, one outcome. Default 300-word entry? Downgrade to normal unless work genuinely architectural or design-decision-level.

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

See `references/examples.md` — entries per level (short ~80w, normal ~150w, extended ~350w).

## Archiving

**Trigger**: exceeds 40 entries OR user requests
1. Move older entries to `.claude/JOURNAL_ARCHIVE.md`
2. Keep last 20 entries in main file
3. Add link at top: `**Note**: Entries 1-N have been archived`
4. Maintain continuous numbering — NEVER reset
