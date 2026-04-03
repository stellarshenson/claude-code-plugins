---
name: benchmark-writer
description: Write a BENCHMARK.md with measurable evaluation criteria through iterative dialogue. Pushes for programmatic metrics over subjective checklists. Invoked after program-writer, before workflow execution.
---

# Benchmark Writer

Write a `BENCHMARK.md` that produces a single number to optimize. Push hard for programmatic, measurable metrics. Subjective checklists are a last resort.

## Prerequisites

PROGRAM.md must exist and be approved by the user.

## Process

### Round 1: Identify measurable signals

Read PROGRAM.md. For each work item, ASK the user - all in ONE message:

1. **What can we measure programmatically?** For each work item, propose concrete metrics:
   - Line counts (`wc -l`), function counts (`grep -c "def "`)
   - Test counts (`pytest --co -q | tail -1`), test pass rate
   - Lint violations (`ruff check --statistics`)
   - Complexity scores (`radon cc -s -a`)
   - File existence checks (`test -f path`)
   - grep pattern counts (occurrences of a pattern that should increase/decrease)
   - Custom script output (a small Python one-liner that computes a metric)

2. **What's the target for each metric?** Current value -> target value

3. **What can't be measured programmatically?** These become fuzzy scales (0-10) with explicit rubrics - but only as a last resort. Every fuzzy scale must justify why a programmatic metric isn't possible.

Present proposed metrics and ask: "Which of these can we actually compute? What am I missing?"

### Round 2: Draft the benchmark

Write BENCHMARK.md with:
- **Score formula** with explicit weights
- **Programmatic checks** (commands that produce numbers)
- **Checklist items** (binary pass/fail verified against code)
- **Fuzzy scales** (only for genuinely subjective qualities, with detailed rubrics)
- **Iteration log** table

Present to user and ASK: "Is this measuring the right things? Are the targets realistic?"

### Round 3+: Refine

Iterate based on feedback. Common refinements:
- Adjust targets (too aggressive / too lenient)
- Replace fuzzy scales with programmatic metrics the user suggests
- Add metrics for edge cases the user knows about
- Remove items that are redundant

Each round: update BENCHMARK.md, show changes, ask if ready.

### Final: User approval

Done ONLY when user explicitly approves. Same approval phrases as program-writer.

## Metric Hierarchy (prefer top, avoid bottom)

1. **Programmatic command output** - `make test` failure count, `wc -l`, `grep -c`. Best. Reproducible, no LLM judgment
2. **File/pattern existence checks** - `test -f path`, `grep -q pattern file`. Binary, fast
3. **Computed metrics** - small Python one-liner or script that outputs a number. Good when standard tools don't cover it
4. **Binary checklist items** - "X exists in file Y". Verified by reading code. LLM-evaluated but binary
5. **Fuzzy scales (0-10)** - subjective grades with rubrics. Last resort. Every fuzzy scale should have a "why not programmatic?" justification

## Score Formula Design

The score formula should combine metrics with appropriate weights:

```markdown
## Score

**Direction**: MINIMIZE (target: 0)

```
score = (failed_tests * 10) + unchecked_items + lint_violations + sum(fuzzy_residuals)
```

**Weights reflect severity**: test failures are 10x worse than a missing checklist item.
```

**Rules for good formulas**:
- One number, one direction (MINIMIZE or MAXIMIZE)
- Weights reflect actual severity (test failure > lint warning > style nit)
- Programmatic components have higher weight than generative ones
- Formula doesn't change between iterations (add items, don't change weights)

## Fuzzy Scale Design (when unavoidable)

Every fuzzy scale MUST have:
- **Rubric**: what does 10 mean? What does 5 mean? What does 2 mean?
- **Justification**: why can't this be measured programmatically?
- **Anchor examples**: concrete descriptions at 3+ points on the scale

```markdown
### Scale: Design Consistency (0-10)

Current grade: [0] /10. Residual: [10]

Rubric:
- 10 = every module follows identical patterns, no mixed conventions
- 8 = consistent with 1-2 minor deviations
- 5 = some patterns shared, some divergent
- 2 = no consistent patterns

Why not programmatic: consistency is cross-cutting, no single grep pattern captures it.
```

## BENCHMARK.md Structure

```markdown
# Benchmark: <title matching PROGRAM.md>

## Score

**Direction**: MINIMIZE (target: 0)

```
score = <formula>
```

## Evaluation

**Programmatic checks** (run these commands):
1. `make test` - count failures (weight: 10x)
2. `make lint` - must be clean
3. <custom metric command>

**Generative checks**:
4. For each [ ] item, verify against code. Mark [x] with evidence
5. Grade fuzzy scales using rubrics
6. EDIT this file, UPDATE Iteration Log

---

## Section 1: <work item group>
- [ ] <specific, verifiable item>
  Evidence required: <what to check>

## Fuzzy Scales (if any)
### Scale: <name> (0-10)
Current grade: [0] /10. Residual: [10]
Rubric: <what each score means>
Why not programmatic: <justification>

---

## Iteration Log
| Iter | Score | Tests | Notes |
|------|-------|-------|-------|
| base | TBD   | N     | before any work |
```

## Rules

- **Programmatic over generative** - if you can measure it with a command, do that instead of a checklist item
- **Every fuzzy scale justifies its existence** - "why not programmatic?"
- **Weights reflect reality** - test failures matter more than style
- **Fixed evaluation** - the formula doesn't change between iterations
- **Iteration log is mandatory** - tracks score trajectory
- **Targets are specific** - "improve" is not a target, "reduce from 14 to 0" is
