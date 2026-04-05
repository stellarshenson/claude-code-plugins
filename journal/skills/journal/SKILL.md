---
name: journal
description: Journal entry management and archiving. Auto-triggered after completing substantive work to ensure entries are appended correctly. Enforces entry format, append-only rule, continuous numbering, and archiving.
---

# Journal Management

Manages `.claude/JOURNAL.md` entries. The journal is the project's audit trail - every substantive task gets an entry.

## CRITICAL: Append-Only Rule

New entries MUST be appended at the END of the file. NEVER insert between existing entries. The last entry in the file is always the most recent work. After writing an entry, VERIFY it was appended correctly by reading the last 5 lines of the file.

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

## What to Log

**Log**: document changes, features, investigations with findings, diagram work
**Skip**: git commits, file cleanup, maintenance. State: "Not logging to journal: <reason>"

## Verification After Writing

After appending an entry, ALWAYS verify:
1. Read the last entry in the file
2. Confirm it matches what you just wrote
3. Confirm the entry number is one higher than the previous entry
4. Confirm no entries were displaced or overwritten

## Examples

See `references/examples.md` for entries at each level (short ~80w, normal ~150w, extended ~350w).

## Archiving

**Trigger**: exceeds 40 entries OR user requests
1. Move older entries to `.claude/JOURNAL_ARCHIVE.md`
2. Keep last 20 entries in main file
3. Add link at top: `**Note**: Entries 1-N have been archived`
4. Maintain continuous numbering - NEVER reset
