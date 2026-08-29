---
description: Standardize oversized / mis-marked journal entries via the ACP repair loop. For each offender, the shipped prompt YAML drives a focused `claude -p` subprocess that decides Extended vs Condense vs Drop-marker; the CLI applies the verdict. Triggers - "standardize journal", "fix journal entry tiers", "repair journal".
allowed-tools: [Read, Write, Edit, Bash, Glob, Skill]
argument-hint: "(optional) <journal-path>  -- default .claude/JOURNAL.md"
---

# Standardize Journal Entries

Invoke the `journal:standardize` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
