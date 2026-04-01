# Benchmark: Engine Modernization Checklist

## Evaluation Instructions

This benchmark is evaluated generatively. Read each checklist item below, verify it against the current codebase, and mark `[x]` for passing items. Add new `[ ]` items if you discover additional violations during evaluation. The benchmark score is:

```
score = unchecked_items + failed_tests + (functions_over_complexity_10 * 2) + (unjustified_components * 3) + (unjustified_tests * 3)
```

Lower is better. Target: 0. Unjustified components and tests carry heavy weight (3x) because dead code and trivial tests are technical debt that compounds.

### Evaluation Steps

1. Read this file and evaluate each `[ ]` item against the codebase
2. Run `make test` and count failed tests
3. Run `make lint` and verify clean
4. Run tree-sitter complexity analysis: `python -c "import ast, sys; [print(f'{n.name}: {getattr(n, 'col_offset', 0)}') for f in sys.argv[1:] for n in ast.walk(ast.parse(open(f).read())) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]" stellars_claude_code_plugins/engine/*.py` to list all functions, then evaluate complexity
5. Audit CODE_JUSTIFICATIONS.md - verify every function, class, and test has an entry with its justification and the failure point it addresses
6. Mark `[x]` for passing items, leave `[ ]` for failing items
7. Report: violations count, failed tests, functions over complexity 10, unjustified components, unjustified tests, composite score

### CODE_JUSTIFICATIONS.md

As part of the benchmark process, create and maintain `CODE_JUSTIFICATIONS.md` in the project root. This document lists every function, class, and test with its justification. Format:

```markdown
## Engine Modules

### engine/fsm.py

- **build_phase_lifecycle_fsm** (function) - creates the standard phase FSM used by every orchestrator command. Failure point: phase transitions would not work
- **resolve_phase_key** (function) - resolves WORKFLOW::PHASE namespace with fallback chain. Failure point: agents and gates would not resolve for gc/hotfix workflows

### engine/orchestrator.py

- **_fire_fsm** (function) - syncs persisted state with FSM before firing events. Failure point: phase status would desync between state.yaml and FSM
- ...

## Tests

### tests/test_fsm.py

- **test_gate_fail_returns_to_in_progress** - failure point: gate retry loop breaks if transition missing. Not trivial: regression caught real bug in v0.7
- ...
```

Components or tests missing from CODE_JUSTIFICATIONS.md are automatically unjustified.

---

## Section 1: FSM Migration

- [ ] `transitions` package listed in pyproject.toml `[project] dependencies`
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

## Section 2: Hypothesis Removal from Planning Workflow

HYPOTHESIS stays in FULL workflow (valuable for implementation). Only removed from PLANNING.

- [ ] HYPOTHESIS not in PLANNING workflow phases in workflow.yaml
- [ ] HYPOTHESIS still present in FULL workflow phases in workflow.yaml
- [ ] No PLANNING::HYPOTHESIS entry in phases.yaml
- [ ] FULL::HYPOTHESIS entry still present in phases.yaml
- [ ] No PLANNING::HYPOTHESIS section in agents.yaml
- [ ] FULL::HYPOTHESIS section still present in agents.yaml
- [ ] All hypothesis Python code preserved (orchestrator.py functions, _AUTO_ACTION_REGISTRY, cmd_hypotheses)
- [ ] `orchestrate validate` passes (no missing phase references)

## Section 2b: Agent Number Removal

- [ ] No `number` field on Agent dataclass in model.py
- [ ] Agent number auto-derived from list position in _build_agents_and_gates
- [ ] _build_agent_instructions uses enumerate for numbering
- [ ] No sequential numbering validation in validate_model
- [ ] No `number:` lines in agents.yaml entries
- [ ] All tests updated and passing

## Section 3: Code Quality (tree-sitter + complexity analysis)

### Complexity

- [ ] Tree-sitter analysis executed on engine/fsm.py
- [ ] Tree-sitter analysis executed on engine/model.py
- [ ] Tree-sitter analysis executed on engine/orchestrator.py
- [ ] Cyclomatic complexity measured for every function
- [ ] No function exceeds 50 lines (body only, excluding docstring)
- [ ] No function has cyclomatic complexity > 10
- [ ] Functions exceeding limits have been refactored or justified with comment

### Dead Code and Justification

Every function and class must defend its existence. Run tree-sitter to list all functions and classes, then for each one verify it is: (a) called by another function or exported, AND (b) serves a distinct purpose not duplicated elsewhere. Components that fail this test are **unjustified** and must be removed or merged. Count of unjustified components inflates the benchmark score.

- [ ] No unreachable code paths detected
- [ ] No unused imports in engine/fsm.py
- [ ] No unused imports in engine/model.py
- [ ] No unused imports in engine/orchestrator.py
- [ ] No unused functions (every function called or exported)
- [ ] No duplicate or near-duplicate code blocks (>10 lines similar)
- [ ] Every function in fsm.py has a caller or is exported in __init__.py
- [ ] Every function in model.py has a caller or is exported in __init__.py
- [ ] Every function in orchestrator.py has a caller or is registered in a dispatch dict
- [ ] Every dataclass in model.py is instantiated by load_model or used in type annotations
- [ ] No wrapper functions that just forward to another function without adding logic
- [ ] No utility functions used only once (inline them)
- [ ] Unjustified component count = 0

### Size Reduction

- [ ] orchestrator.py lines < 2444 (baseline)
- [ ] Total engine lines < 3113 (baseline)
- [ ] Hypothesis code (141 lines) fully removed

### Test Health and Justification

Every test must defend its existence. Trivial tests that assert obvious truths (e.g., `assert True`, `assert 1 == 1`, checking a constructor sets a field) waste CI time and obscure real coverage gaps. Each test must target a specific failure point - a condition that could realistically break.

For each test, verify:
1. **It targets a failure point** - tests a condition that could actually fail in production or during refactoring
2. **It is not trivial** - removing the code under test would cause the test to fail meaningfully
3. **It is not redundant** - no other test already covers the same failure point

Tests that fail this audit are **unjustified** and count in the benchmark score at 3x weight.

- [ ] `make test` passes with 0 failures
- [ ] `make lint` passes clean
- [ ] `orchestrate validate` passes with auto-build-claw YAML resources
- [ ] `orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds
- [ ] Test count >= 80 (quality over quantity after removing trivial tests)
- [ ] No test file imports removed functions or classes
- [ ] No trivial tests (asserting constructor defaults, enum values, type checks on constants)
- [ ] Every test targets a specific failure point documented in CODE_JUSTIFICATIONS.md
- [ ] No redundant tests covering the same failure point
- [ ] Unjustified test count = 0

## Section 4: Code Justifications Document

- [ ] CODE_JUSTIFICATIONS.md exists in project root
- [ ] Every function in engine/fsm.py listed with justification and failure point
- [ ] Every function in engine/model.py listed with justification and failure point
- [ ] Every function in engine/orchestrator.py listed with justification and failure point
- [ ] Every dataclass in engine/model.py listed with justification
- [ ] Every test in tests/test_fsm.py listed with failure point and why-not-trivial
- [ ] Every test in tests/test_model.py listed with failure point and why-not-trivial
- [ ] Every test in tests/test_orchestrator.py listed with failure point and why-not-trivial
- [ ] No component exists in code that is missing from CODE_JUSTIFICATIONS.md
- [ ] No test exists in code that is missing from CODE_JUSTIFICATIONS.md

## Section 5: Independent Workflow Flag

- [ ] No `dependency` field anywhere in codebase (workflow.yaml, model.py, orchestrator.py)
- [ ] `independent: bool = True` on WorkflowType dataclass
- [ ] Planning workflow has `independent: false` in workflow.yaml
- [ ] Full, gc, hotfix workflows omit `independent` (implicitly true)
- [ ] `cmd_new` fails with error when `--type` targets a workflow with `independent: false`
- [ ] Orchestrator uses `wf_def.independent` everywhere (not `wf_def.dependency`)
- [ ] Tests verify: independent workflows start, non-independent workflows fail on direct invocation

## Section 6: Run-Until-Complete Mode

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

- [ ] All Section 1-5 checklist items are `[x]` (benchmark score = 0)
- [ ] CODE_JUSTIFICATIONS.md complete with zero unjustified components and zero unjustified tests
- [ ] Total engine lines < 2800 (reduced from 3113 baseline)

**Do NOT stop while any condition above is unmet.**

---

## Score Tracking

| Iteration | Unchecked | Failed Tests | Complexity > 10 | Unjustified Components | Unjustified Tests | Score |
|-----------|-----------|--------------|------------------|------------------------|-------------------|-------|
| baseline  | (all)     | 0            | TBD              | TBD                    | TBD               | TBD   |
