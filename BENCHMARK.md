# Benchmark: Engine Modernization Checklist

## Evaluation Instructions

This benchmark is evaluated generatively. Read each checklist item below, verify it against the current codebase, and mark `[x]` for passing items. Add new `[ ]` items if you discover additional violations during evaluation. The benchmark score is:

```
score = unchecked_items + failed_tests + (functions_over_complexity_10 * 2)
```

Lower is better. Target: 0.

### Evaluation Steps

1. Read this file and evaluate each `[ ]` item against the codebase
2. Run `make test` and count failed tests
3. Run `make lint` and verify clean
4. Run tree-sitter complexity analysis: `python -c "import ast, sys; [print(f'{n.name}: {getattr(n, 'col_offset', 0)}') for f in sys.argv[1:] for n in ast.walk(ast.parse(open(f).read())) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]" stellars_claude_code_plugins/engine/*.py` to list all functions, then evaluate complexity
5. Mark `[x]` for passing items, leave `[ ]` for failing items
6. Report: violations count, failed tests, functions over complexity 10, composite score

---

## Section 1: FSM Migration

- [ ] `transitions` package listed in pyproject.toml `[project] dependencies`
- [ ] `transitions` package listed in pyproject.toml `[build-system] requires` if needed
- [ ] engine/fsm.py uses `transitions.Machine` as the FSM engine
- [ ] No custom `State(str, Enum)` class in fsm.py (replaced by transitions states)
- [ ] No custom `Event(str, Enum)` class in fsm.py (replaced by transitions triggers)
- [ ] No custom `Transition` dataclass in fsm.py
- [ ] No custom `FSMConfig` dataclass in fsm.py
- [ ] No custom `FSM` class with manual transition lookup dict
- [ ] Guards implemented as transitions `conditions` callbacks
- [ ] Actions implemented as transitions `after` or `before` callbacks
- [ ] Transition log maintained (every transition recorded with from/to/event)
- [ ] `simulate()` method works for dry-run workflow validation
- [ ] `resolve_phase_key()` function preserved and working
- [ ] `build_phase_lifecycle_fsm()` returns a transitions-based machine
- [ ] orchestrator.py `_fire_fsm()` uses new FSM API correctly
- [ ] orchestrator.py `_PHASE_FSM` is a transitions Machine instance
- [ ] All test_fsm.py tests rewritten for transitions API
- [ ] All test_fsm.py tests passing
- [ ] No regression in orchestrator phase lifecycle (start/end/reject/skip all work)

## Section 2: Hypothesis Removal

- [ ] HYPOTHESIS not in FULL workflow phases in workflow.yaml
- [ ] HYPOTHESIS not in PLANNING workflow phases in workflow.yaml
- [ ] No FULL::HYPOTHESIS entry in phases.yaml
- [ ] No PLANNING::HYPOTHESIS entry in phases.yaml
- [ ] No FULL::HYPOTHESIS section in agents.yaml (agents + gates)
- [ ] No PLANNING::HYPOTHESIS section in agents.yaml (agents + gates)
- [ ] No `_action_hypothesis_autowrite` function in orchestrator.py
- [ ] No `_action_hypothesis_gc` function in orchestrator.py
- [ ] No `_append_hypothesis` function in orchestrator.py
- [ ] No `_auto_write_hypotheses` function in orchestrator.py
- [ ] No `_load_prior_hypotheses` function in orchestrator.py
- [ ] No `_hypothesis_catalogue_summary` function in orchestrator.py
- [ ] No `_run_hypothesis_gc` function in orchestrator.py
- [ ] No `cmd_hypotheses` function in orchestrator.py
- [ ] No `hypothesis_autowrite` in _AUTO_ACTION_REGISTRY
- [ ] No `hypothesis_gc` in _AUTO_ACTION_REGISTRY
- [ ] No `hypotheses` subcommand in CLI argument parser
- [ ] No `HYPOTHESES_FILE` global variable in orchestrator.py
- [ ] No `prior_hyp` variable in `_build_context()`
- [ ] `_clean_artifacts_dir()` does not preserve hypotheses*.yaml files
- [ ] No `hypothesis` entries in `_KNOWN_AUTO_ACTIONS` in model.py
- [ ] No hypothesis-related test assertions in test files
- [ ] `orchestrate validate` passes (no missing phase references)

## Section 3: Code Quality (tree-sitter + complexity analysis)

### Complexity

- [ ] Tree-sitter analysis executed on engine/fsm.py
- [ ] Tree-sitter analysis executed on engine/model.py
- [ ] Tree-sitter analysis executed on engine/orchestrator.py
- [ ] Cyclomatic complexity measured for every function
- [ ] No function exceeds 50 lines (body only, excluding docstring)
- [ ] No function has cyclomatic complexity > 10
- [ ] Functions exceeding limits have been refactored or justified with comment

### Dead Code

- [ ] No unreachable code paths detected
- [ ] No unused imports in engine/fsm.py
- [ ] No unused imports in engine/model.py
- [ ] No unused imports in engine/orchestrator.py
- [ ] No unused functions (every function called or exported)
- [ ] No duplicate or near-duplicate code blocks (>10 lines similar)

### Size Reduction

- [ ] orchestrator.py lines < 2444 (baseline)
- [ ] Total engine lines < 3113 (baseline)
- [ ] Hypothesis code (141 lines) fully removed

### Test Health

- [ ] `make test` passes with 0 failures
- [ ] `make lint` passes clean
- [ ] `orchestrate validate` passes with auto-build-claw YAML resources
- [ ] `orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds
- [ ] Test count >= 100 (maintained coverage after refactoring)
- [ ] No test file imports removed functions or classes

## Section 4: Run-Until-Complete Mode

- [ ] `--iterations 0` accepted by `orchestrate new` without error
- [ ] `total_iterations = 0` stored in state.yaml as sentinel for unlimited
- [ ] `_run_next_iteration()` checks benchmark score when total_iterations is 0
- [ ] Iteration continues automatically when benchmark score > 0
- [ ] Iteration stops when benchmark score = 0
- [ ] Safety cap at 20 iterations warns and pauses
- [ ] Status display shows "until benchmark complete" for unlimited mode
- [ ] Banner shows "benchmark-driven iteration N" instead of "N/total"
- [ ] Display messages for benchmark-driven mode in app.yaml
- [ ] Tests cover run-until-complete: auto-continue, stop-on-zero, safety cap

---

## Completion Conditions

Iterations continue until ALL conditions are met. Use `orchestrate add-iteration --count 1` if iterations run out before completion.

- [ ] Benchmark score = 0 (all items above checked, no failures, no complexity violations)
- [ ] `make test` passes with 0 failures and test count >= 100
- [ ] `make lint` passes clean
- [ ] `orchestrate validate` passes with auto-build-claw YAML resources
- [ ] `orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds
- [ ] No custom FSM classes remain (only transitions.Machine)
- [ ] No hypothesis code remains (zero references in engine, YAML, tests)
- [ ] Total engine lines < 2800 (reduced from 3113 baseline)

**Do NOT stop while any condition above is unmet.**

---

## Score Tracking

| Iteration | Unchecked | Failed Tests | Complexity > 10 | Score |
|-----------|-----------|--------------|------------------|-------|
| baseline  | (all)     | 0            | TBD              | TBD   |
