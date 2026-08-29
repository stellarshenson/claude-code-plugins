---
description: Archive older journal entries via `journal-tools archive`. Keeps last 20 in main, appends rest to JOURNAL_ARCHIVE.md. Triggers - "archive journal", "prune journal", "compact journal".
allowed-tools: [Read, Write, Edit, Bash, Glob, Skill]
argument-hint: "(optional) --keep-last N, --threshold N"
---

# Archive Journal

Invoke the `journal:archive` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
