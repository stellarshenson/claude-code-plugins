---
description: Build the devil's-advocate persona and harvest the fact repository for a target document - step 1 of the workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
argument-hint: "the document to critique and who its toughest reader is"
---

# Devil's Advocate - Setup

Read `devils-advocate/skills/setup/SKILL.md` and follow it - it is the single source of truth for building the devil persona (role, biases, triggers) and harvesting verified facts from source material. Do NOT duplicate it here; this command is only the explicit entry point into that step.

Step 1 of the workflow. It writes `devils_advocate.md` (the persona) and `fact_repository.md` (verified claims with sources), which `/devils-advocate:evaluate` then reads. Run `/devils-advocate:run` instead for the full setup → evaluate → iterate loop in one go.
