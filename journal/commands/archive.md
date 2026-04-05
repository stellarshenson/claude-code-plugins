---
description: Archive older journal entries, keeping last 20 in main file
allowed-tools: [Read, Write, Edit, Glob]
argument-hint: ""
---

# Archive Journal Entries

Archive older journal entries from `.claude/JOURNAL.md` to `.claude/JOURNAL_ARCHIVE.md`, keeping only the last 20 entries in the main journal.

## Steps

1. Read `.claude/JOURNAL.md`
2. Count total entries
3. If more than 20:
   - Move all except last 20 to `.claude/JOURNAL_ARCHIVE.md` (create or append)
   - Update main journal to keep only last 20
   - Add link at top: `**Note**: Entries 1-N have been archived to [JOURNAL_ARCHIVE.md](JOURNAL_ARCHIVE.md).`
4. Maintain continuous numbering - NEVER reset
5. VERIFY: read both files after archiving to confirm no entries lost

## Rules

- Entry numbers are continuous across archive and main file
- Archive file accumulates - never overwrite, always append
- After archiving, the main journal starts at entry N+1 (not 1)
