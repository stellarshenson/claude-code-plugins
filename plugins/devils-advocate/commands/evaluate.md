---
description: Generate the baseline concern catalogue and scorecard from the devil persona - step 2 of the workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
argument-hint: "(optional) the target document, if not already set up"
---

# Devil's Advocate - Evaluate

Read `devils-advocate/skills/evaluate/SKILL.md` and follow it - it is the single source of truth for producing the concern catalogue with Fibonacci risk scores and the baseline scorecard. Do NOT duplicate it here; this command is only the explicit entry point into that step.

Step 2 of the workflow. Requires `/devils-advocate:setup` to have run first (`devils_advocate.md` and `fact_repository.md` must exist). Its baseline residual is what `/devils-advocate:iterate` drives down. Run `/devils-advocate:run` instead for the full loop in one go.
