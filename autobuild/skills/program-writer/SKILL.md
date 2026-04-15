---
name: program-writer
description: Write a PROGRAM.md file through iterative dialogue with the user. Asks clarifying questions, proposes work items, refines based on feedback until the user approves. Invoked before workflow execution.
---

# Program Writer

Write `PROGRAM.md` through back-and-forth dialogue. NEVER produce full document on first attempt. Build incrementally via questions and proposals until user confirms solid.

## Process

### Round 1: Extract the intention

Read user's seed prompt (text after `/autobuild`). Goal: understand INTENTION - what they want and why - not HOW. ASK these questions - all in ONE message, not one at a time:

1. **End state?** What does "done" look like? Paint picture of success - outcome, not implementation steps
2. **What exists today?** Current state - working code, broken code, nothing yet? Gap between now and end state?
3. **Why does this matter?** Problem solved? Cost of not doing it? Shapes priority
4. **Off-limits?** Files, behaviors, APIs that MUST NOT change
5. **How will we know it works?** Test suite, benchmark, manual check? What's measurable?
6. **Biggest risk?** What could go wrong or waste iterations?

Listen carefully. Users often know WHAT but describe it as HOW. Separate intention from implementation. Ask follow-ups when intention unclear. "You mentioned refactoring X - goal = reduce complexity, improve testability, or enable a new feature?"

Do NOT proceed until intention crystal clear.

### Round 2: Propose the program

From answers, write first draft of PROGRAM.md with:
- **Objective** (1-3 sentences, measurable)
- **Current State** (what exists, what's broken, baseline numbers)
- **Work Items** (flat list with scope, acceptance criteria, priority)
- **Exit Conditions** (when to stop - see below)
- **Constraints** (what not to change)

ASK user about exit conditions: "When should orchestrator stop iterating? Default options:
1. **Score stagnation** (recommended) - stop when benchmark score doesn't improve for 2 consecutive iterations despite implementation effort
2. **Score target** - stop when benchmark score hits specific value (e.g. score < 5)
3. **Scope completion** - stop when all work items meet acceptance, nothing left to implement
4. **Combined** - stop on whichever first: target reached OR stagnation OR scope complete

Specific exit conditions, or default (stagnation + scope completion)?"

Present full program, ASK: "Review. What's missing, wrong, or over-scoped?"

### Round 3+: Refine

Iterate on feedback. User may:
- Add forgotten work items
- Remove out-of-scope items
- Change priorities
- Tighten acceptance criteria
- Add constraints

Each round: update PROGRAM.md, show diff, ask if ready.

### Final: User approval

Done ONLY on explicit user approval. Approval phrases:
- "looks good", "approved", "let's go", "run it", "start", "yes"

Do NOT proceed to benchmark-writer or orchestrator without explicit approval.

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

- **Comprehensive** - program can be as long as needed to capture intention fully. Never compress at cost of clarity
- **Intention over implementation** - work items describe WHAT and WHY, not HOW. "Migrate FSM to transitions package" = intention. "Replace FSMConfig with transitions.Machine, update 15 call sites in orchestrator.py" = implementation detail, belongs in PLAN phase
- **Capture expert knowledge** - user-provided architectural constraints, design decisions, technology choices, domain insights MUST land in program. User = domain expert. "Use SimPy resources for connection pools" or "config must compose in 3 layers" = expert guidance orchestrator needs. Architectural direction, not implementation detail
- **Let RESEARCH/PLAN figure out the how** - absent specific user guidance, don't prescribe implementation. RESEARCH phase investigates codebase, PLAN designs implementation
- **Scope boundaries explicit** - what CAN and CANNOT be modified
- **Single metric** - program enables ONE number to optimize
- **Logical grouping, not iteration breakdown** - group by logical category (e.g. "Framework extraction", "Config system", "Testing") when applicable, NOT by iterations. Orchestrator's PLANNING phase sequences iterations per dependencies and scope
- **Exit conditions tied to benchmark, not acceptance criteria** - exit conditions reference benchmark score, not individual work item acceptance. Benchmark IS the objective function. Default: stop on score stagnation (no improvement for 2 iterations) OR scope completion (nothing left to implement) OR score at effective optimum (no further improvement possible). Ask user for specific conditions - target score or hard iteration cap possible
- **Every work item has measurable acceptance** - "improve X" not a work item, "reduce X from 14 to 0" is
- **Predictions and outcomes** - each work item states what changes (predict: from X to Y) and what user gets (outcome: enables Z, unblocks W). Predictions feed HYPOTHESIS phase. Outcomes keep items grounded in user value
- **Dependencies** - work item requiring another first: state explicitly (depends on: X). Feeds PLANNING phase iteration sequencing. No circular dependencies
