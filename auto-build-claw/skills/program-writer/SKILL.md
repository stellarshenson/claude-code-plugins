---
name: program-writer
description: Write a PROGRAM.md file defining objectives, work items, acceptance criteria, and exit conditions for auto-build-claw iterations. Use when user wants to define a structured improvement program before running the orchestrator. Invoked before workflow execution.
---

# Program Writer

Write a `PROGRAM.md` that drives auto-build-claw iterations. The program defines WHAT to achieve, not HOW to break it into iterations - the orchestrator handles iteration planning.

## When to Use

Before running `orchestrate new`. The user describes what they want to improve, and this skill produces a structured PROGRAM.md that the orchestrator consumes via `--objective "Implement the program defined in PROGRAM.md (read PROGRAM.md)"`.

## Structure

PROGRAM.md has these sections:

### 1. Objective (1-3 sentences)

What the program aims to achieve. Concise, measurable, grounded.

**Good**: "Migrate the custom FSM implementation to the transitions Python package while preserving the existing public API."
**Bad**: "Make the code better and more modern."

### 2. Baseline Metrics

Current state numbers the benchmark will measure against. Table format:

```markdown
| Metric | Current | Target |
|--------|---------|--------|
| engine lines | 3113 | <2800 |
| test count | 115 | >=100 |
| functions >50L | 14 | 0 |
```

### 3. Work Items

A flat list of concrete work items with acceptance criteria. NOT iterations - the orchestrator decides how to group work into iterations.

Each work item has:
- **Title** - what to do
- **Scope** - files to modify, functions to change
- **Acceptance criteria** - measurable conditions for done
- **Priority** - high/medium/low

```markdown
- **Migrate FSM to transitions package** (high)
  - Scope: engine/fsm.py, tests/test_fsm.py, pyproject.toml
  - Acceptance: transitions.Machine wraps FSM, all tests pass, no orchestrator changes needed

- **Remove hypothesis from planning workflow** (medium)
  - Scope: workflow.yaml, phases.yaml, agents.yaml
  - Acceptance: PLANNING workflow has no HYPOTHESIS phase, FULL still has it, validate passes
```

### 4. Exit Conditions

**MANDATORY section.** Every program MUST define when to stop. Required for `--iterations 0` (run until done), recommended even for fixed iteration counts.

Default exit condition (use unless the program has a better one):

```markdown
## Exit Conditions

Iterations stop when ANY of these is true:
1. Benchmark score = 0 (all checklist items met)
2. No score improvement for 2 consecutive iterations (plateau - no further optimisation possible)
3. All work items have acceptance criteria met

Additionally, ALL of these must hold:
- make test passes with 0 failures
- make lint passes clean
```

The **plateau condition** (no score improvement for 2 iterations) is the default safety valve. If the score stops improving, further iterations are wasted effort. The orchestrator should stop and report what remains unresolved.

For programs with a programmatic score (loss, accuracy), the exit condition should reference the metric directly:

```markdown
## Exit Conditions

Iterations stop when ANY of these is true:
1. val_bpb < 0.95 (target reached)
2. No val_bpb improvement > 0.001 for 3 consecutive iterations (plateau)
3. 20 iterations completed (safety cap)
```

### 5. Constraints (optional)

What NOT to change. Files that are off-limits. Behaviors to preserve.

## Best Practices (from Karpathy autoresearch)

- **Single metric to optimize** - the benchmark produces ONE number. Lower or higher is better. No ambiguity
- **Fixed evaluation** - the metric computation doesn't change between iterations. Only the code under test changes
- **Simplicity criterion** - all else being equal, simpler is better. Removing code for same results = win
- **Fair comparison** - every iteration runs the same evaluation, making results directly comparable
- **Concise program** - the program fits on one screen. Dense, specific, no fluff
- **Scope boundaries** - explicitly state what CAN and CANNOT be modified

## What NOT to Include

- Iteration breakdown (orchestrator handles this in PLANNING phase)
- Implementation details (RESEARCH and PLAN phases handle this)
- Timeline estimates
- Agent assignments
