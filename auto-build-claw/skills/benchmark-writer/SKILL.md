---
name: benchmark-writer
description: Write a BENCHMARK.md with measurable evaluation criteria through iterative dialogue. Pushes for programmatic metrics over subjective checklists. Invoked after program-writer, before workflow execution.
---

# Benchmark Writer

## What is the benchmark?

The benchmark is a **scalar evaluation function**. It takes the current state of the codebase and produces ONE number. That number tells the orchestrator how far from done the iteration is.

It is NOT a plan. It is NOT exit conditions. It is NOT a to-do list. It is a MEASUREMENT INSTRUMENT - like a thermometer or a loss function. Every iteration, the same benchmark runs against the codebase and produces a comparable score. The score trajectory (going down for MINIMIZE, up for MAXIMIZE) shows whether iterations are making progress.

**What belongs in the benchmark**: score formula, programmatic checks (commands that produce numbers), data science metrics (MSE, F1, correlation), binary checklist items (does X exist in file Y), fuzzy scales (0-10 with rubrics), iteration log tracking score trajectory.

**What does NOT belong**: exit conditions ("stop when..."), completion conditions, iteration planning, implementation guidance. Those belong in PROGRAM.md.

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
   - **Data science metrics** (when the objective involves models, simulations, or statistical behavior):
     - Error metrics: MSE, RMSE, MAE, MAPE
     - Distribution metrics: KL divergence, Wasserstein distance, Kolmogorov-Smirnov statistic
     - Classification: F1, precision, recall, accuracy, ROC-AUC
     - Correlation: Pearson r, Spearman rho, R-squared
     - Statistical tests: p-values, chi-squared, t-test results
     - Custom: any domain-specific metric computable from simulation output or model predictions

2. **What's the target for each metric?** Current value -> target value

3. **What can't be measured programmatically?** These become fuzzy scales (0-10) with explicit rubrics - but only as a last resort. Every fuzzy scale must justify why a programmatic metric isn't possible.

4. **How do we execute each check?** For every metric, define the exact execution recipe - the command, script, or procedure that produces the number. This must be repeatable and comparable across iterations:
   - **Shell commands**: `make test`, `pytest --co -q | tail -1`, `ruff check --statistics | tail -1`
   - **Python scripts**: inline one-liners or dedicated test scripts that output a number
   - **Scenario tests**: for complex behaviors (UI, API, simulation), define the test procedure:
     - Playwright/browser tests: `npx playwright test --reporter=json | jq '.stats.unexpected'`
     - API tests: `curl -s endpoint | jq '.status'` or a pytest fixture that hits the endpoint
     - Simulation runs: `python run_simulation.py --config test.yaml | grep 'metric:'`
     - Generative scenario tests: a prompt template + expected output pattern (e.g. "run `claude -p 'prompt'` and check output contains X")
   - **Comparison baselines**: for before/after metrics, store the baseline value in the benchmark and compare against current

   Every check in the benchmark must have an **Execution** line showing exactly how to reproduce it. No ambiguous "verify X works" - show the command.

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
2. **Data science metrics** - MSE, RMSE, F1, KL divergence, correlation coefficients. Computed from data/model output. Objective, comparable across iterations
3. **File/pattern existence checks** - `test -f path`, `grep -q pattern file`. Binary, fast
4. **Computed metrics** - small Python one-liner or script that outputs a number. Good when standard tools don't cover it
5. **Binary checklist items** - "X exists in file Y". Verified by reading code. LLM-evaluated but binary
6. **Fuzzy scales (0-10)** - subjective grades with rubrics. Last resort. Every fuzzy scale should have a "why not programmatic?" justification

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
   Execution: `.venv/bin/pytest tests/ -q --tb=no | tail -1`
2. `make lint` - must be clean
   Execution: `uvx ruff check --statistics | tail -1`
3. <custom metric>
   Execution: <exact command that outputs the number>

**Scenario tests** (if applicable):
- <test name>
  Execution: <exact command or script>
  Expected: <what passing looks like>
  Metric: <what number to extract>

**Generative checks**:
4. For each [ ] item, verify against code. Mark [x] with evidence
5. Grade fuzzy scales using rubrics
6. EDIT this file, UPDATE Iteration Log

---

## Section 1: <work item group>
- [ ] <specific, verifiable item>
  Execution: <how to check - command, grep, or read instruction>
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

- **Benchmark is ONLY scoring** - it produces a scalar number evaluating the current iteration. It does NOT contain exit conditions, completion conditions, or stop criteria. Those belong in PROGRAM.md. The benchmark answers "what is the score right now?" - the program answers "when do we stop?"
- **No completion conditions section** - do NOT generate "Iterations stop when..." or "Completion Conditions" sections in BENCHMARK.md. If the user asks about exit conditions, direct them to PROGRAM.md
- **Programmatic over generative** - if you can measure it with a command, do that instead of a checklist item
- **Data science metrics when applicable** - if the objective involves models, simulations, statistical behavior, or data pipelines, actively propose MSE/RMSE/MAE/F1/KL-divergence/correlation metrics. These are the highest-value programmatic measures for quantitative work
- **Every fuzzy scale justifies its existence** - "why not programmatic?"
- **Weights reflect reality** - test failures matter more than style
- **Fixed evaluation** - the formula doesn't change between iterations
- **Iteration log is mandatory** - tracks score trajectory
- **Targets are specific** - "improve" is not a target, "reduce from 14 to 0" is
- **Every check has an execution recipe** - no ambiguous "verify X works". Show the exact command, script, or procedure that produces the result. Must be repeatable across iterations so scores are comparable. For complex checks (browser tests, API calls, simulation runs, generative scenarios), include the full execution procedure with expected output pattern
