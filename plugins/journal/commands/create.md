---
description: Initialise a new `.claude/JOURNAL.md` for a project that doesn't have one yet. Strictly first-time setup — refuses if the file exists. Triggers - "create journal", "init journal", "start journal", "new journal".
allowed-tools: [Read, Write, Bash, Glob, Skill]
argument-hint: "(optional) extra context about what to log from the current conversation"
---

# Create Journal

Invoke the `journal:create` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
