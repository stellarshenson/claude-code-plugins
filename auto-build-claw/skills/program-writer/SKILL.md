---
name: program-writer
description: Write a PROGRAM.md file through iterative dialogue with the user. Asks clarifying questions, proposes work items, refines based on feedback until the user approves. Invoked before workflow execution.
---

# Program Writer

Write a `PROGRAM.md` through back-and-forth dialogue with the user. Do NOT produce the full document on first attempt. Instead, build it incrementally through questions and proposals until the user says it's solid.

## Process

### Round 1: Understand the objective

Read the user's seed prompt (the text after `/auto-build-claw`). Then ASK these questions - all in ONE message, not one at a time:

1. **What's the end state?** What does "done" look like? A specific metric, a working feature, a refactored codebase?
2. **What exists today?** What's the current state - working code, broken code, nothing yet?
3. **What's off-limits?** Files, behaviors, or APIs that must NOT change
4. **How will we know it works?** Is there a test suite, a benchmark, a manual check?
5. **What's the biggest risk?** What could go wrong or waste iterations?

Do NOT proceed until the user answers. Their answers shape every work item.

### Round 2: Propose the program

Based on the answers, write the first draft of PROGRAM.md with:
- **Objective** (1-3 sentences, measurable)
- **Current State** (what exists, what's broken, baseline numbers)
- **Work Items** (flat list with scope, acceptance criteria, priority)
- **Exit Conditions** (when to stop)
- **Constraints** (what not to change)

Present it to the user and ASK: "Review this program. What's missing, wrong, or over-scoped?"

### Round 3+: Refine

Iterate based on feedback. The user may:
- Add work items they forgot
- Remove items that are out of scope
- Change priorities
- Tighten acceptance criteria
- Add constraints

Each round: update PROGRAM.md, show the diff, ask if it's ready.

### Final: User approval

The program is done ONLY when the user explicitly approves it. Phrases that count as approval:
- "looks good", "approved", "let's go", "run it", "start", "yes"

Do NOT proceed to benchmark-writer or the orchestrator without explicit approval.

## PROGRAM.md Structure

```markdown
# Program: <short title>

## Objective
<1-3 sentences, measurable, grounded>

## Current State
<what exists, baseline metrics, what's broken>

## Work Items

- **<title>** (high/medium/low)
  - Scope: <files, functions>
  - Acceptance: <measurable conditions>

## Exit Conditions
<when to stop iterating>

## Constraints
<what not to change>
```

## Rules

- **Dense, not verbose** - program fits on one screen. No fluff
- **Scope boundaries explicit** - what CAN and CANNOT be modified
- **Single metric** - the program should enable ONE number to optimize
- **No iteration breakdown** - the orchestrator handles iteration planning
- **No implementation details** - RESEARCH and PLAN phases handle this
- **Every work item has acceptance criteria** - "improve X" is not a work item, "reduce X from 14 to 0" is
