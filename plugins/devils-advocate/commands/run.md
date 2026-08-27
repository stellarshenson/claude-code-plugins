---
description: Run the full devil's advocate critical analysis workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "describe the document to critique and who the toughest reader is"
---

# Devil's Advocate - Run

Read `devils-advocate/skills/run/SKILL.md` and follow it - it is the single source of truth for the end-to-end workflow, the persona build, the Fibonacci scoring model, the versioned-file naming (`<name>_v<NN>_<residual>.md`), and the stop conditions. Do NOT duplicate it here; this command is only the explicit entry point into that workflow.

Full setup → evaluate → iterate loop in one go. The same three steps are also available as their own thin commands when you want to drive them by hand:

```
/devils-advocate:setup       # 1. build persona, harvest facts
/devils-advocate:evaluate    # 2. concern catalogue + baseline scorecard
/devils-advocate:iterate     # 3. improve, version, re-score (repeat until done)
```
