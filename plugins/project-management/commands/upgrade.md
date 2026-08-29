---
description: Rebuild a legacy acceptance-criteria or defects document to the tracked schema - assigns permanent ids, puts a code on every category, converts dated notes to authored log lines, drops the hand-kept contents table; dry run first
allowed-tools: [Read, Write, Bash, Skill]
argument-hint: "the document to upgrade, e.g. 'docs/acceptance-criteria.md' or 'the old bug list under docs/'"
---

# Upgrade

Invoke the `project-management:upgrade` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
