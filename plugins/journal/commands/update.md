---
description: Append a new entry to `.claude/JOURNAL.md` OR update the last entry in place when the new work is a small continuation of it. Triggers - "update journal", "add journal entry", "log this", "add entry", "journal this", "record this in the journal".
allowed-tools: [Read, Edit, Write, Bash, Glob, Skill]
argument-hint: "(optional) work description - otherwise infer from context"
---

# Update Journal

Invoke the `journal:update` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
