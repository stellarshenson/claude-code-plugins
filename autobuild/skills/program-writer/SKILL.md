---
name: program-writer
description: Write a PROGRAM.md file through iterative dialogue with the user. Asks clarifying questions, proposes work items, refines based on feedback until the user approves. Invoked before workflow execution.
---

# Program Writer

Write `PROGRAM.md` via dialogue. NEVER produce full document on first attempt. Build incrementally via questions and proposals.

## Process

### Round 1: Extract the intention

Read seed prompt (text after `/autobuild`). Goal: understand INTENTION (what + why), not HOW. ASK all in ONE message:

1. **End state?** What does "done" look like? Outcome, not implementation
2. **What exists today?** Current state. Gap to end state?
3. **Why does this matter?** Problem solved? Cost of not doing? Shapes priority
4. **Off-limits?** Files, behaviors, APIs that MUST NOT change
5. **How do we know it works?** Test suite, benchmark, manual check?
6. **Biggest risk?** What could waste iterations?

Users know WHAT but describe HOW. Separate intention from implementation. Follow up when unclear: "You mentioned refactoring X - goal = reduce complexity, improve testability, or enable a new feature?"

Do NOT proceed until intention crystal clear.

### Round 2: Propose the program

Write first draft with:
- **Objective** (1-3 sentences, measurable)
- **Current State** (what exists, broken, baseline numbers)
- **Work Items** (flat list: scope, acceptance, priority)
- **Exit Conditions** (see below)
- **Constraints** (what not to change)

ASK about exit conditions: "When should orchestrator stop?
1. **Score stagnation** (recommended) - stop if no improvement 2 consecutive iterations
2. **Score target** - stop when score hits value (e.g. score < 5)
3. **Scope completion** - stop when all work items meet acceptance
4. **Combined** - whichever first: target OR stagnation OR scope complete

Specific, or default (stagnation + scope completion)?"

Present full program. Ask: "What's missing, wrong, over-scoped?"

### Round 3+: Refine

User may:
- Add forgotten work items
- Remove out-of-scope items
- Change priorities
- Tighten acceptance
- Add constraints

Each round: update, show diff, ask if ready.

### Final: User approval

Explicit approval only. Phrases: "looks good", "approved", "let's go", "run it", "start", "yes".

Do NOT proceed without approval.

## PROGRAM.md Structure

```markdown
# Program: <short title>

## Objective
<1-3 sentences, measurable, grounded>

## Current State
<what exists, baseline metrics, what's broken>

## Work Items

### <Logical Category>

- **<title>** (high/medium/low)
  - Scope: <files, functions>
  - Acceptance: <measurable conditions>
  - Predict: <what changes - from X to Y>
  - Outcome: <what the user gets when this is done>
  - Depends on: <other work items that must be done first, if any>

## Exit Conditions
Iterations stop when ANY of these is true:
1. <primary condition - tied to benchmark score>
2. No benchmark score improvement for 2 consecutive iterations (stagnation)
3. All work items complete and nothing remains to implement (scope done)

## Constraints
<what not to change>
```

## Rules

- **Comprehensive** - as long as needed. Never compress at cost of clarity
- **Intention over implementation** - work items = WHAT + WHY, not HOW. "Migrate FSM to transitions package" = intention. "Replace FSMConfig with transitions.Machine, update 15 call sites" = implementation (belongs in PLAN)
- **Capture expert knowledge** - user architectural constraints, design decisions, tech choices, domain insights MUST land in program. "Use SimPy resources for connection pools" = expert guidance orchestrator needs
- **Let RESEARCH/PLAN figure out the how** - don't prescribe implementation absent user guidance
- **Scope boundaries explicit** - what CAN and CANNOT be modified
- **Single metric** - program enables ONE number to optimize
- **Logical grouping, not iteration breakdown** - group by category ("Framework extraction", "Config system", "Testing"), NOT iterations. PLANNING sequences per dependencies
- **Exit conditions tied to benchmark, not acceptance criteria** - reference score, not work item acceptance. Benchmark IS the objective function. Default: stagnation OR scope completion OR effective optimum. Ask user for specifics
- **Every work item has measurable acceptance** - "improve X" not valid, "reduce X from 14 to 0" is
- **Predictions and outcomes** - each work item states changes (predict: X→Y) and user value (outcome: enables Z). Feeds HYPOTHESIS phase
- **Dependencies** - state explicitly (depends on: X). Feeds PLANNING. No circular deps
