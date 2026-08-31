---
description: File, triage, log, close or reject a defect in the project's defects document - permanent category-scoped ids (DEF-LNCH-3), mandatory CRITICAL/MAJOR/MEDIUM/MINOR severity, repro line and the append-only attempt trail, all through the pm-tools CLI
allowed-tools: [Read, Write, Bash, Skill]
argument-hint: "the defect work, e.g. 'file: auth token empty on the first turn after a fork' or 'log on DEF-LNCH-3: the 200ms delay did not fix it'"
---

# Defect

Invoke the `project-management:defect` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
