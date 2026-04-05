---
description: Create a new journal entry for completed work
allowed-tools: [Read, Write, Edit, Glob]
argument-hint: "description of the work completed"
---

# Create Journal Entry

Append a new journal entry to `.claude/JOURNAL.md` for work just completed.

## Steps

1. Read `.claude/JOURNAL.md` to find the last entry number
2. Determine entry level from work complexity:
   - **Short** (~80 words): bug fix, config change, typo
   - **Normal** (~150-200 words): feature, multi-file change (DEFAULT)
   - **Extended** (~350+ words): architectural change, design decisions
3. Compose the entry in format:
   ```
   <N+1>. **Task - <short 3-5 word depiction>** (v1.2.3): task description<br>
       **Result**: summary of work done
   ```
4. APPEND the entry at the END of the file - never insert between existing entries
5. If the project is versioned (has `package.json`, `pyproject.toml`, `Cargo.toml`), include version tag
6. VERIFY: read the last 5 lines of the file to confirm entry was appended correctly

## Rules

- Entry number MUST be one higher than the previous entry
- Version tag only for versioned projects
- Result section must be information-dense with file names, libraries, and specific changes
- Do NOT log: git commits, file cleanup, maintenance tasks
