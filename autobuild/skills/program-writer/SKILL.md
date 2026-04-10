---
name: program-writer
description: Write a PROGRAM.md file through iterative dialogue with the user. Asks clarifying questions, proposes work items, refines based on feedback until the user approves. Invoked before workflow execution.
---

# Program Writer

Write a `PROGRAM.md` through back-and-forth dialogue with the user. Do NOT produce the full document on first attempt. Instead, build it incrementally through questions and proposals until the user says it's solid.

## Process

### Round 1: Extract the intention

Read the user's seed prompt (the text after `/autobuild`). Your job is to understand their INTENTION - what they want to achieve and why - not to prescribe how to do it. ASK these questions - all in ONE message, not one at a time:

1. **What's the end state?** What does "done" look like? Paint the picture of success - not implementation steps, but the outcome
2. **What exists today?** What's the current state - working code, broken code, nothing yet? What's the gap between now and the end state?
3. **Why does this matter?** What problem does this solve? What's the cost of not doing it? This shapes priority
4. **What's off-limits?** Files, behaviors, or APIs that must NOT change
5. **How will we know it works?** Is there a test suite, a benchmark, a manual check? What's measurable?
6. **What's the biggest risk?** What could go wrong or waste iterations?

Listen carefully to the answers. The user often knows WHAT they want but may describe it in terms of HOW. Your job is to separate intention from implementation. Ask follow-up questions if the intention is unclear. "You mentioned refactoring X - is the goal to reduce complexity, improve testability, or enable a new feature?"

Do NOT proceed until the user's intention is crystal clear.

### Round 2: Propose the program

Based on the answers, write the first draft of PROGRAM.md with:
- **Objective** (1-3 sentences, measurable)
- **Current State** (what exists, what's broken, baseline numbers)
- **Work Items** (flat list with scope, acceptance criteria, priority)
- **Exit Conditions** (when to stop - see below)
- **Constraints** (what not to change)

ASK the user specifically about exit conditions: "When should the orchestrator stop iterating? Default options:
1. **Score stagnation** (recommended) - stop when benchmark score doesn't improve for 2 consecutive iterations despite implementation effort
2. **Score target** - stop when benchmark score reaches a specific value (e.g. score < 5)
3. **Scope completion** - stop when all work items have acceptance criteria met and nothing remains to implement
4. **Combined** - stop on whichever comes first: target reached OR stagnation OR scope complete

Do you have specific exit conditions, or should I use the default (score stagnation + scope completion)?"

Present the full program to the user and ASK: "Review this program. What's missing, wrong, or over-scoped?"

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

- **Comprehensive** - the program can be as long as needed to fully capture the intention. Don't compress for brevity at the cost of clarity
- **Intention over implementation** - work items describe WHAT to achieve and WHY, not HOW to do it. "Migrate FSM to transitions package" is intention. "Replace FSMConfig with transitions.Machine, update 15 call sites in orchestrator.py" is implementation detail that belongs in PLAN phase
- **Capture expert knowledge** - if the user provides architectural constraints, design decisions, technology choices, or domain insights, these MUST be captured in the program. The user is the domain expert. "Use SimPy resources for connection pools" or "the config must compose in 3 layers" is expert guidance that the orchestrator needs. This is not implementation detail - it's architectural direction
- **Let RESEARCH/PLAN figure out the how** - unless the user provides specific guidance, don't prescribe implementation approach. The orchestrator's RESEARCH phase investigates the codebase and PLAN designs the implementation
- **Scope boundaries explicit** - what CAN and CANNOT be modified
- **Single metric** - the program should enable ONE number to optimize
- **Logical grouping, not iteration breakdown** - work items should be grouped by logical category (e.g. "Framework extraction", "Config system", "Testing") when applicable, but NOT divided into iterations. The orchestrator's PLANNING phase decides iteration sequencing based on dependencies and scope
- **Exit conditions tied to benchmark, not acceptance criteria** - exit conditions must reference the benchmark score, not individual work item acceptance. The benchmark IS the objective function. Default: stop on score stagnation (no improvement for 2 iterations) OR scope completion (nothing left to implement) OR score reaches effective optimum (further improvement not possible). Ask the user for specific conditions - they may have a target score or a hard iteration cap
- **Every work item has measurable acceptance** - "improve X" is not a work item, "reduce X from 14 to 0" is
- **Predictions and outcomes** - each work item states what will change (predict: from X to Y) and what the user gets (outcome: enables Z, unblocks W). Predictions feed into the HYPOTHESIS phase. Outcomes keep work items grounded in user value
- **Dependencies** - if a work item requires another to be done first, state it explicitly (depends on: X). This feeds into the PLANNING phase which sequences iterations based on dependency order. No circular dependencies
