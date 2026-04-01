---
name: benchmark-writer
description: Write a BENCHMARK.md file with evaluation checklist, score formula, and iteration tracking table for auto-build-claw iterations. Use when user needs a benchmark to measure progress against PROGRAM.md work items. Invoked before workflow execution.
---

# Benchmark Writer

Write a `BENCHMARK.md` that measures progress for auto-build-claw iterations. The benchmark defines HOW to evaluate, producing a single composite score. The orchestrator consumes it via `--benchmark "Read BENCHMARK.md and evaluate each [ ] item..."`.

## When to Use

After PROGRAM.md exists. The benchmark is derived from the program's work items and acceptance criteria. Each work item generates checklist items, and the score formula combines them into one number.

## Structure

BENCHMARK.md has these sections in order:

### 1. Score Formula and Direction

The benchmark MUST produce a single composite number and state whether to MINIMIZE or MAXIMIZE.

```markdown
## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + failed_tests + (complexity_violations * 2)
```
```

Three benchmark types:

- **Generative** - Claude reads the checklist and evaluates each item against the codebase. Marks [x] or [ ]. Score = count of unchecked items
- **Programmatic** - a command produces a number (e.g., `make test` failure count, loss function, accuracy). Score = command output
- **Hybrid** - combines generative checklist with programmatic metrics. Score = weighted sum

### 2. Evaluation Instructions

How the evaluator (Claude or script) should execute the benchmark. Step by step.

```markdown
## Evaluation

1. Run `make test` - count failed tests
2. Run `make lint` - must be clean (0 or 1 penalty)
3. Read each [ ] item below and verify against codebase
4. Mark [x] for passing, leave [ ] for failing
5. EDIT this file with updated marks
6. UPDATE the Iteration Log below with this iteration's results
7. Report composite score
```

**CRITICAL**: For generative and hybrid benchmarks, the evaluator MUST EDIT the benchmark file. Reporting scores without updating the file is a violation.

### 3. Checklist Sections

Derived from PROGRAM.md work items. Each work item becomes a section with specific, verifiable checklist items.

Rules for good checklist items:
- **Verifiable** - can be checked by reading code or running a command
- **Specific** - names exact files, functions, fields
- **Binary** - passes or fails, no gray area
- **Independent** - each item stands alone

```markdown
## Section 1: FSM Migration

- [ ] transitions package in pyproject.toml dependencies
- [ ] engine/fsm.py uses transitions.Machine
- [ ] No custom FSMConfig dataclass
- [ ] All test_fsm.py tests passing
```

### 4. Completion Conditions

When to stop iterating. Links back to PROGRAM.md exit conditions.

```markdown
## Completion Conditions

Iterations stop when ALL conditions are met:
- [ ] All checklist items above are [x] (score = 0)
- [ ] make test passes with 0 failures
- [ ] make lint passes clean

**Do NOT stop while any condition above is unmet.**
```

### 5. Iteration Log

**MANDATORY section.** Tracks every evaluation across iterations. Updated by the evaluator during each TEST phase. Shows score trajectory so you can see if iterations are improving.

```markdown
## Iteration Log

| Iteration | Date | Score | Failed Tests | Unchecked Items | Notes |
|-----------|------|-------|--------------|-----------------|-------|
| baseline  | -    | TBD   | 0            | (all)           | before any work |
```

After each evaluation, the evaluator appends a new row:

```markdown
| iter 1    | 2026-04-01 | 12 | 0 | 12 | FSM migration complete, hypothesis removal done |
| iter 2    | 2026-04-01 | 5  | 0 | 5  | complexity refactoring, benchmark enforcement |
| iter 3    | 2026-04-02 | 0  | 0 | 0  | all conditions met |
```

The iteration log serves three purposes:
1. **Progress tracking** - score should decrease (for MINIMIZE) or increase (for MAXIMIZE) over iterations
2. **Regression detection** - if score goes up, something broke
3. **Completion proof** - final row shows target reached

## Benchmark Types Guide

### When to use Generative (checklist only)
- Code quality improvements (refactoring, dead code removal)
- Feature implementation (migration, new capabilities)
- Documentation completeness

### When to use Programmatic (command output)
- Model training (loss, accuracy, perplexity)
- Performance optimization (latency, throughput)
- Test coverage (percentage)
- Code metrics (complexity score from tool)

### When to use Hybrid
- Code modernization with measurable quality targets
- Research with both qualitative and quantitative goals

## Best Practices (from Karpathy autoresearch)

- **One number** - the benchmark produces exactly ONE score. Not a dashboard, not a report. One number
- **Direction is explicit** - MINIMIZE or MAXIMIZE, stated at the top
- **Fixed evaluation** - the evaluation method doesn't change between iterations. Add checklist items if discovered, but don't change the formula
- **Fair comparison** - every iteration evaluated the same way
- **Iteration log tracks progress** - the table shows if iterations are actually improving. Score going up = regression
- **Programmatic when possible** - `val_bpb` in autoresearch is computed by code, not by Claude judging quality. Use commands and tools when you can measure, generative when you can't
- **Simplicity bonus** - if the benchmark can reward code simplification (fewer lines, lower complexity), include it

## What NOT to Include

- Implementation guidance (that's PROGRAM.md)
- Iteration plans (orchestrator handles this)
- Vague items ("code quality improved" - how would you check?)
- Items that require subjective judgment ("code is clean")
