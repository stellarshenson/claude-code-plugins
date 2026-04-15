---
name: benchmark-writer
description: Write a BENCHMARK.md with measurable evaluation criteria through iterative dialogue. Pushes for programmatic metrics over subjective checklists. Invoked after program-writer, before workflow execution.
---

# Benchmark Writer

## What is the benchmark?

Benchmark = **scalar evaluation function**. Takes codebase state, produces ONE number. Tells orchestrator how far from done.

NOT a plan. NOT exit conditions. NOT a to-do list. MEASUREMENT INSTRUMENT - thermometer, loss function. Same benchmark runs every iteration against codebase, produces comparable score. Score trajectory (down for MINIMIZE, up for MAXIMIZE) reveals iteration progress.

**Belongs in benchmark**: score formula, programmatic checks (commands producing numbers), data science metrics (MSE, F1, correlation), binary checklist items (does X exist in file Y), fuzzy scales (0-10 with rubrics), iteration log tracking trajectory.

**Does NOT belong (MOST COMMON MISTAKE)**: exit conditions ("stop when..."), completion conditions ("iterations stop when ALL..."), convergence criteria ("stop if delta < X"). ALWAYS PROGRAM.md, NEVER BENCHMARK.md. Catch yourself writing "stop", "exit", "completion", "converge" in benchmark - STOP, move to program.

## Prerequisites

PROGRAM.md exists, user-approved.

## Process

### Round 1: Identify measurable signals

Read PROGRAM.md. For each work item, ASK user - all in ONE message:

1. **What can we measure programmatically?** For each work item, propose concrete metrics:
   - Line counts (`wc -l`), function counts (`grep -c "def "`)
   - Test counts (`pytest --co -q | tail -1`), test pass rate
   - Lint violations (`ruff check --statistics`)
   - Complexity scores (`radon cc -s -a`)
   - File existence checks (`test -f path`)
   - grep pattern counts (occurrences of a pattern that should increase/decrease)
   - Custom script output (a small Python one-liner that computes a metric)
   - **Data science metrics** (when objective involves models, simulations, statistical behavior):
     - Error metrics: MSE, RMSE, MAE, MAPE
     - Distribution metrics: KL divergence, Wasserstein distance, Kolmogorov-Smirnov statistic
     - Classification: F1, precision, recall, accuracy, ROC-AUC
     - Correlation: Pearson r, Spearman rho, R-squared
     - Statistical tests: p-values, chi-squared, t-test results
     - Custom: any domain-specific metric computable from simulation output or model predictions

2. **Target per metric?** Current value -> target value

3. **What can't be measured programmatically?** Becomes fuzzy scale (0-10) with explicit rubric - last resort only. Every fuzzy scale justifies why programmatic metric impossible.

4. **How to execute each check?** For every metric, define exact execution recipe - command, script, procedure producing the number. Repeatable, comparable across iterations:
   - **Shell commands**: `make test`, `pytest --co -q | tail -1`, `ruff check --statistics | tail -1`
   - **Python scripts**: inline one-liners or dedicated test scripts outputting a number
   - **Scenario tests**: for complex behaviors (UI, API, simulation), define test procedure:
     - Playwright/browser tests: `npx playwright test --reporter=json | jq '.stats.unexpected'`
     - API tests: `curl -s endpoint | jq '.status'` or pytest fixture hitting the endpoint
     - Simulation runs: `python run_simulation.py --config test.yaml | grep 'metric:'`
     - Generative scenario tests: prompt template + expected output pattern (e.g. "run `claude -p 'prompt'`, check output contains X")
   - **Comparison baselines**: for before/after metrics, store baseline value in benchmark, compare against current

   Every check needs **Execution** line showing exact reproduction. No ambiguous "verify X works" - show the command.

Present proposed metrics, ask: "Which of these can we actually compute? What am I missing?"

### Round 2: Draft the benchmark

Write BENCHMARK.md with:
- **Score formula** with explicit weights
- **Programmatic checks** (commands producing numbers)
- **Checklist items** (binary pass/fail verified against code)
- **Fuzzy scales** (only for genuinely subjective qualities, detailed rubrics)
- **Iteration log** table

Present to user, ASK: "Measuring the right things? Targets realistic?"

### Round 3+: Refine

Iterate on feedback. Common refinements:
- Adjust targets (too aggressive / too lenient)
- Replace fuzzy scales with user-suggested programmatic metrics
- Add metrics for edge cases user knows about
- Remove redundant items

Each round: update BENCHMARK.md, show changes, ask if ready.

### Final: User approval

Done ONLY on explicit user approval. Same approval phrases as program-writer.

## Metric Hierarchy (prefer top, avoid bottom)

1. **Programmatic command output** - `make test` failure count, `wc -l`, `grep -c`. Best. Reproducible, no LLM judgment
2. **Data science metrics** - MSE, RMSE, F1, KL divergence, correlation coefficients. Computed from data/model output. Objective, iteration-comparable
3. **File/pattern existence checks** - `test -f path`, `grep -q pattern file`. Binary, fast
4. **Computed metrics** - Python one-liner or script outputting a number. Good when standard tools insufficient
5. **Binary checklist items** - "X exists in file Y". Verified by reading code. LLM-evaluated but binary
6. **Fuzzy scales (0-10)** - subjective grades with rubrics. Last resort. Every fuzzy scale needs "why not programmatic?" justification

## Score Formula Design

Combine metrics with appropriate weights:

```markdown
## Score

**Direction**: MINIMIZE (target: 0)

```
score = (failed_tests * 10) + unchecked_items + lint_violations + sum(fuzzy_residuals)
```

**Weights reflect severity**: test failures 10x worse than missing checklist item.
```

**Rules for good formulas**:
- One number, one direction (MINIMIZE or MAXIMIZE)
- **Data science metrics carry most weight** - primary optimisation target (RQI, MSE, F1, correlation). Dominate composite score (>= 50% weight). Checklist items and fuzzy scales = guardrails, not objective
- Weight hierarchy: data science metrics > programmatic checks > binary checklist > fuzzy scales
- Formula fixed between iterations (add items, don't change weights)

## Fuzzy Scale Design (when unavoidable)

Every fuzzy scale MUST have:
- **Rubric**: meaning of 10, 5, 2
- **Justification**: why not programmatic
- **Anchor examples**: concrete descriptions at 3+ scale points

```markdown
### Scale: Design Consistency (0-10)

Current grade: [0] /10. Residual: [10]

Rubric:
- 10 = every module follows identical patterns, no mixed conventions
- 8 = consistent with 1-2 minor deviations
- 5 = some patterns shared, some divergent
- 2 = no consistent patterns

Why not programmatic: consistency cross-cutting, no single grep pattern captures it.
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
- [ ] <binary check - passes or fails, use [ ] for unchecked, [x] for passing>
  Execution: <how to check - command, grep, or read instruction>
  Evidence: <what was found when checked>

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

<!-- NO "Completion Conditions" or "Exit Conditions" section here.
     Those belong in PROGRAM.md. The benchmark ONLY scores. -->
```

## Rules

- **Benchmark ONLY scores** - produces scalar number for current iteration. NO exit/completion/stop criteria. Those go in PROGRAM.md. Benchmark answers "what is the score right now?" - program answers "when do we stop?"
- **ZERO exit/stop/completion conditions** - most commonly violated rule. NEVER generate these patterns in BENCHMARK.md:
  - "Iterations stop when..." - WRONG, PROGRAM.md
  - "Completion Conditions" section - WRONG, PROGRAM.md
  - "Stop when score reaches..." - WRONG, PROGRAM.md
  - "Exit when all items pass" - WRONG, PROGRAM.md
  - Convergence checks like "stop condition met: delta < X" - WRONG, exit condition disguised as checklist item
  Writing ANYTHING about when to stop iterating = PROGRAM item, not BENCHMARK. Move to PROGRAM.md or delete
- **Programmatic over generative** - measurable by command? Use command, not checklist item
- **Data science metrics when applicable** - objective involving models, simulations, statistical behavior, or data pipelines: actively propose MSE/RMSE/MAE/F1/KL-divergence/correlation. Highest-value programmatic measures for quantitative work
- **Every fuzzy scale justifies existence** - "why not programmatic?"
- **Data science metrics dominate score** - when applicable, >= 50% composite weight. Primary optimisation target. Checklists and fuzzy scales = structural guardrails, not the thing being optimised
- **Fixed evaluation** - formula stable across iterations
- **Iteration log mandatory** - tracks score trajectory
- **Targets specific** - "improve" not a target, "reduce from 14 to 0" is
- **Every check has execution recipe** - no ambiguous "verify X works". Exact command, script, or procedure producing the result. Repeatable across iterations for score comparability. Complex checks (browser tests, API calls, simulation runs, generative scenarios): include full execution procedure with expected output pattern
