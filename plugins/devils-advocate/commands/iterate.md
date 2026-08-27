---
description: One improvement cycle - decide approach, apply changes, version, re-score, rename with residual - step 3 of the workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
argument-hint: "(optional) how to improve, or let it ask"
---

# Devil's Advocate - Iterate

Read `devils-advocate/skills/iterate/SKILL.md` and follow it - it is the single source of truth for the four-step cycle (improve, version, score, rename) and the stop conditions. Do NOT duplicate it here; this command is only the explicit entry point into that step.

Step 3 of the workflow, run repeatedly until residual is acceptable, stagnation, or the user accepts. Requires `/devils-advocate:evaluate` to have produced a baseline. Re-scores in place when the user edited the document outside Claude. Run `/devils-advocate:run` instead to drive the whole setup → evaluate → iterate loop.
