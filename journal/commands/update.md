---
description: Update the most recent journal entry with additional details or corrections
allowed-tools: [Read, Edit, Glob]
argument-hint: "additional details or corrections for the latest entry"
---

# Update Journal Entry

Update the most recent journal entry in `.claude/JOURNAL.md` with additional information or corrections.

## Steps

1. Read `.claude/JOURNAL.md` to find the last entry
2. Determine what needs updating:
   - **Extend**: add more detail to the Result section (new files changed, additional findings)
   - **Correct**: fix inaccurate information (wrong file names, incorrect version numbers)
   - **Upgrade level**: expand a Short entry to Normal or Extended if work grew in scope
3. Edit the last entry in place - do NOT change its number or Task line unless correcting an error
4. VERIFY: read the updated entry to confirm changes are correct

## Rules

- Only update the MOST RECENT entry (last in file)
- To update older entries, specify the entry number explicitly
- Preserve the entry format: `<N>. **Task - ...**` with `**Result**:` section
- Never change entry numbers
- Never reorder entries
