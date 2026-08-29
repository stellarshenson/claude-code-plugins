---
description: Extract an oversized journal entry's depth into a standalone article in `docs/` and condense the entry to a Standard-tier summary that links to the article. Use when `journal-tools check` warns that an entry is over the Extended max (400 words) - even Extended caps there, and the rationale belongs in a dedicated doc. Triggers - "create article from entry", "extract journal entry to article", "make article from journal".
allowed-tools: [Read, Write, Edit, Bash, Glob, AskUserQuestion, Skill]
argument-hint: "<entry-number>  -- entry to extract into an article"
---

# Extract a journal entry into a `docs/` article

Invoke the `journal:article` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
