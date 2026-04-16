---
name: benchmark-writer
description: Write a BENCHMARK.md with measurable evaluation criteria through iterative dialogue. Pushes for programmatic metrics over subjective checklists. Invoked after program-writer, before workflow execution.
---

# Benchmark Writer

## What is the benchmark?

Benchmark = **scalar evaluation function**. Takes codebase state, outputs ONE number. Tells orchestrator how far from done.

NOT a plan. NOT exit conditions. NOT a to-do list. MEASUREMENT INSTRUMENT. Same benchmark runs every iteration, produces comparable score. Trajectory (down for MINIMIZE, up for MAXIMIZE) reveals progress.

**Belongs in benchmark**: score formula, programmatic checks, data science metrics (MSE, F1, correlation), binary checklist items, fuzzy scales (0-10 with rubrics), iteration log.

**Does NOT belong (MOST COMMON MISTAKE)**: exit conditions, completion conditions, convergence criteria. ALWAYS PROGRAM.md, NEVER BENCHMARK.md. Writing "stop", "exit", "completion", "converge" in benchmark - STOP, move to program.

## Prerequisites

PROGRAM.md exists, user-approved.

## Process

### Round 1: Identify measurable signals

Read PROGRAM.md. ASK user - all in ONE message:

1. **What can we measure programmatically?** Propose concrete metrics per work item:
   - Line counts (`wc -l`), function counts (`grep -c "def "`)
   - Test counts (`pytest --co -q | tail -1`), test pass rate
   - Lint violations (`ruff check --statistics`)
   - Complexity scores (`radon cc -s -a`)
   - File existence (`test -f path`)
   - grep pattern counts
   - Custom script output (one-liner computing a metric)
   - **Data science metrics** (for models, simulations, statistical behavior):
     - Error: MSE, RMSE, MAE, MAPE
     - Distribution: KL divergence, Wasserstein, Kolmogorov-Smirnov
     - Classification: F1, precision, recall, accuracy, ROC-AUC
     - Correlation: Pearson r, Spearman rho, R-squared
     - Statistical: p-values, chi-squared, t-test
     - Custom: any domain metric from simulation/model output

2. **Target per metric?** Current → target.

3. **What can't be measured programmatically?** Becomes fuzzy scale (0-10) with rubric. Last resort. Every fuzzy scale justifies why.

4. **Execution recipe per check?** Exact command, script, procedure. Repeatable:
   - **Shell**: `make test`, `pytest --co -q | tail -1`, `ruff check --statistics | tail -1`
   - **Python**: one-liners or dedicated scripts outputting a number
   - **Scenario tests**:
     - Playwright: `npx playwright test --reporter=json | jq '.stats.unexpected'`
     - API: `curl -s endpoint | jq '.status'` or pytest fixture
     - Simulation: `python run_simulation.py --config test.yaml | grep 'metric:'`
     - Generative: prompt template + expected output pattern (e.g. "run `claude -p 'prompt'`, check output contains X")
   - **Baselines**: store baseline for before/after comparisons

   Every check needs **Execution** line. No ambiguous "verify X works".

Ask: "Which can we compute? What am I missing?"

### Round 2: Draft BENCHMARK.md

Includes:
- **Score formula** with weights
- **Programmatic checks** (commands → numbers)
- **Checklist items** (binary pass/fail)
- **Fuzzy scales** (subjective only, with rubrics)
- **Iteration log** table

Ask: "Measuring the right things? Targets realistic?"

### Round 3+: Refine

Common refinements:
- Adjust targets
- Replace fuzzy scales with programmatic metrics
- Add edge-case metrics
- Remove redundant items

Each round: update, show changes, ask if ready.

### Final: User approval

Explicit approval only. Same phrases as program-writer.

## Metric Hierarchy (prefer top)

1. **Programmatic command output** - `make test` fails, `wc -l`, `grep -c`. Best. Reproducible, no LLM judgment
2. **Data science metrics** - MSE, RMSE, F1, KL divergence, correlation. Objective, iteration-comparable
3. **File/pattern existence** - `test -f path`, `grep -q pattern file`. Binary, fast
4. **Computed metrics** - Python one-liner/script. Good when standard tools insufficient
5. **Binary checklist** - "X exists in file Y". LLM-evaluated, binary
6. **Fuzzy scales (0-10)** - subjective with rubrics. Last resort. Each needs "why not programmatic?"

## Score Formula Design

```markdown
## Score

**Direction**: MINIMIZE (target: 0)

```
score = (failed_tests * 10) + unchecked_items + lint_violations + sum(fuzzy_residuals)
```

**Weights reflect severity**: test failures 10x worse than missing checklist item.
```

Rules:
- One number, one direction (MINIMIZE or MAXIMIZE)
- **Data science metrics dominate** - primary optimisation target (RQI, MSE, F1, correlation). >= 50% weight. Checklists + fuzzy = guardrails
- Weight hierarchy: DS metrics > programmatic checks > binary checklist > fuzzy scales
- Formula fixed between iterations (add items, don't change weights)

## Fuzzy Scale Design (when unavoidable)

Every fuzzy scale MUST have:
- **Rubric**: meaning of 10, 5, 2
- **Justification**: why not programmatic
- **Anchor examples**: concrete descriptions at 3+ points

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

- **Benchmark ONLY scores** - scalar for current iteration. NO exit/completion/stop criteria (→ PROGRAM.md). Benchmark answers "what's the score now?" - program answers "when do we stop?"
- **ZERO exit/stop/completion conditions** - most violated rule. NEVER in BENCHMARK.md:
  - "Iterations stop when..." - WRONG, PROGRAM.md
  - "Completion Conditions" section - WRONG, PROGRAM.md
  - "Stop when score reaches..." - WRONG, PROGRAM.md
  - "Exit when all items pass" - WRONG, PROGRAM.md
  - Convergence "stop condition met: delta < X" - WRONG, exit disguised as checklist
  Anything about when to stop = PROGRAM item. Move or delete
- **Programmatic over generative** - measurable by command? Use command
- **Data science metrics when applicable** - models/simulations/statistical/pipelines: propose MSE/RMSE/MAE/F1/KL-divergence/correlation. Highest value for quantitative work
- **Every fuzzy scale justifies existence** - "why not programmatic?"
- **Data science metrics dominate score** - >= 50% composite weight. Primary target. Checklists + fuzzy = guardrails
- **Fixed evaluation** - formula stable across iterations
- **Iteration log mandatory** - tracks trajectory
- **Targets specific** - "improve" is not a target, "reduce from 14 to 0" is
- **Every check has execution recipe** - exact command/script/procedure. Repeatable. Complex checks (browser, API, simulation, generative): full procedure + expected output pattern
