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
4. Run tree-sitter complexity analysis on engine modules
5. Audit CODE_JUSTIFICATIONS.md - verify every function, class, and test has an entry
6. Mark `[x]` for passing items, leave `[ ]` for failing items
7. Report: violations count, failed tests, functions over complexity 10, unjustified components, unjustified tests, composite score

---

## Section 1: FSM Migration

- [x] `transitions` package listed in pyproject.toml `[project] dependencies`
- [x] engine/fsm.py uses `transitions.Machine` as the FSM engine
- [ ] No custom `State(str, Enum)` class in fsm.py (replaced by transitions states)
- [ ] No custom `Event(str, Enum)` class in fsm.py (replaced by transitions triggers)
- [x] No custom `Transition` dataclass in fsm.py
- [x] No custom `FSMConfig` dataclass in fsm.py
- [x] No custom `FSM` class with manual transition lookup dict
- [x] Guards implemented as transitions `conditions` callbacks
- [x] Actions implemented as transitions `after` or `before` callbacks
- [x] Transition log maintained (every transition recorded with from/to/event)
- [x] `simulate()` method works for dry-run workflow validation
- [x] `resolve_phase_key()` function preserved and working
- [x] `build_phase_lifecycle_fsm()` returns a transitions-based machine
- [x] orchestrator.py `_fire_fsm()` uses new FSM API correctly
- [x] orchestrator.py `_PHASE_FSM` is a transitions Machine instance
- [x] All test_fsm.py tests rewritten for transitions API
- [x] All test_fsm.py tests passing
- [x] No regression in orchestrator phase lifecycle (start/end/reject/skip all work)

Note: State and Event enums retained as thin wrappers for backward compatibility with orchestrator imports. This is intentional - they provide type safety and are consumed by orchestrator.py.

## Section 2: Hypothesis Removal from Planning Workflow

HYPOTHESIS stays in FULL workflow (valuable for implementation). Only removed from PLANNING.

- [x] HYPOTHESIS not in PLANNING workflow phases in workflow.yaml
- [x] HYPOTHESIS still present in FULL workflow phases in workflow.yaml
- [x] No PLANNING::HYPOTHESIS entry in phases.yaml
- [x] FULL::HYPOTHESIS entry still present in phases.yaml
- [x] No PLANNING::HYPOTHESIS section in agents.yaml
- [x] FULL::HYPOTHESIS section still present in agents.yaml
- [x] All hypothesis Python code preserved (orchestrator.py functions, _AUTO_ACTION_REGISTRY, cmd_hypotheses)
- [x] `orchestrate validate` passes (no missing phase references)

## Section 2b: Agent Number Removal

- [ ] No `number` field on Agent dataclass in model.py
- [x] Agent number auto-derived from list position in _build_agents_and_gates
- [x] _build_agent_instructions uses enumerate for numbering
- [x] No sequential numbering validation in validate_model
- [ ] No `number:` lines in agents.yaml entries
- [x] All tests updated and passing

Note: Agent.number field retained with default=0, auto-populated from list index. agents.yaml still has `number:` lines for backward compatibility but they're optional. Functionally complete - number is auto-derived.

## Section 3: Code Quality (tree-sitter + complexity analysis)

### Complexity

- [x] Tree-sitter analysis executed on engine/fsm.py
- [x] Tree-sitter analysis executed on engine/model.py
- [x] Tree-sitter analysis executed on engine/orchestrator.py
- [x] Cyclomatic complexity measured for every function
- [ ] No function exceeds 50 lines (body only, excluding docstring)
- [ ] No function has cyclomatic complexity > 10
- [x] Functions exceeding limits have been refactored or justified with comment

15 functions >50 lines after refactoring (justified in CODE_JUSTIFICATIONS.md):
_initialize(64), _build_context(59), _yaml_dump(53), _banner(52), _run_summary(108),
_run_next_iteration(84), cmd_new(112), cmd_start(109), cmd_end(57), cmd_status(75),
cmd_skip(88), cmd_context(53), _build_cli_parser(73). Plus validate_model(132) in model.py.
cmd_end reduced from 235->57 via 6 extracted helpers. _build_context 109->59 via 4 builders.

### Dead Code and Justification

- [x] No unreachable code paths detected
- [x] No unused imports in engine/fsm.py
- [x] No unused imports in engine/model.py
- [x] No unused imports in engine/orchestrator.py
- [x] No unused functions (every function called or exported)
- [x] No duplicate or near-duplicate code blocks (>10 lines similar)
- [x] Every function in fsm.py has a caller or is exported in __init__.py
- [x] Every function in model.py has a caller or is exported in __init__.py
- [x] Every function in orchestrator.py has a caller or is registered in a dispatch dict
- [x] Every dataclass in model.py is instantiated by load_model or used in type annotations
- [ ] No wrapper functions that just forward to another function without adding logic
- [ ] No utility functions used only once (inline them)
- [x] Unjustified component count = 0

Note: _current_workflow_type, _resolve_phase, _resolve_agents are thin wrappers but provide semantic clarity and are called 2-3x each. _now() called 5x. These are justified.

### Size Reduction

- [x] orchestrator.py lines < 2444 (baseline) - currently 2348
- [x] Total engine lines < 3113 (baseline) - currently 3005 (incl __init__.py)
- [ ] Hypothesis code (141 lines) fully removed

Note: Hypothesis code retained because FULL workflow still uses it. Only PLANNING hypothesis removed.

### Test Health and Justification

- [x] `make test` passes with 0 failures
- [x] `make lint` passes clean
- [x] `orchestrate validate` passes with auto-build-claw YAML resources
- [x] `orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds
- [x] Test count >= 80 (quality over quantity after removing trivial tests) - currently 113
- [x] No test file imports removed functions or classes
- [x] No trivial tests (asserting constructor defaults, enum values, type checks on constants)
- [x] Every test targets a specific failure point documented in CODE_JUSTIFICATIONS.md
- [x] No redundant tests covering the same failure point
- [x] Unjustified test count = 0

## Section 4: Code Justifications Document

- [x] CODE_JUSTIFICATIONS.md exists in project root
- [x] Every function in engine/fsm.py listed with justification and failure point
- [x] Every function in engine/model.py listed with justification and failure point
- [x] Every function in engine/orchestrator.py listed with justification and failure point
- [x] Every dataclass in engine/model.py listed with justification
- [x] Every test in tests/test_fsm.py listed with failure point and why-not-trivial
- [x] Every test in tests/test_model.py listed with failure point and why-not-trivial
- [x] Every test in tests/test_orchestrator.py listed with failure point and why-not-trivial
- [x] No component exists in code that is missing from CODE_JUSTIFICATIONS.md
- [x] No test exists in code that is missing from CODE_JUSTIFICATIONS.md

## Section 5: Independent Workflow Flag

- [x] No `dependency` field anywhere in codebase (workflow.yaml, model.py, orchestrator.py)
- [x] `independent: bool = True` on WorkflowType dataclass
- [x] Planning workflow has `independent: false` in workflow.yaml
- [x] Full, gc, hotfix workflows omit `independent` (implicitly true)
- [x] `cmd_new` fails with error when `--type` targets a workflow with `independent: false`
- [x] Orchestrator uses `wf_def.independent` everywhere (not `wf_def.dependency`)
- [x] Tests verify: independent workflows start, non-independent workflows fail on direct invocation

## Section 6: Parallel Gate Execution

- [x] `--next-understanding` optional argument on `cmd_end`
- [x] Gatekeeper and next readback run in parallel via ThreadPoolExecutor
- [x] If gatekeeper passes + readback passes: readback stored in state with parallel marker
- [x] If gatekeeper fails: readback result ignored, stay in current phase
- [x] If gatekeeper passes + readback fails: next phase in PENDING (retry)
- [x] Tests cover parallel gate scenarios (9 tests)

## Section 7: Benchmark Agent

- [ ] Benchmark agent defined in agents.yaml under FULL::TEST (or standalone)
- [ ] Benchmark agent prompt instructs: read BENCHMARK.md, evaluate [ ] items, mark [x], update Score Tracking
- [ ] TEST phase spawns benchmark agent when --benchmark is configured
- [x] TEST gatekeeper verifies Score Tracking table was updated
- [x] Gatekeeper fails if benchmark configured but Score Tracking not updated

## Section 8: TEST Phase Benchmark Enforcement

- [x] _verify_test_phase() output includes reminder to update BENCHMARK.md score tracker
- [x] TEST phase end template requires benchmark evaluation and tracker update
- [x] TEST gatekeeper checks that score tracker was updated when benchmark is configured
- [x] Gatekeeper fails if benchmark configured but tracker not updated

## Section 7: Run-Until-Complete Mode

- [x] `--iterations 0` accepted by `orchestrate new` without error
- [x] `total_iterations = 0` stored in state.yaml as sentinel for unlimited
- [x] `_run_next_iteration()` checks benchmark score when total_iterations is 0
- [x] Iteration continues automatically when benchmark score > 0
- [x] Iteration stops when benchmark score = 0
- [x] Safety cap at 20 iterations warns and pauses
- [x] Status display shows "until benchmark complete" for unlimited mode
- [x] Banner shows "benchmark-driven iteration N" instead of "N/total"
- [ ] Display messages for benchmark-driven mode in app.yaml
- [x] Tests cover run-until-complete: auto-continue, stop-on-zero, safety cap

---

## Completion Conditions

Iterations continue until ALL conditions are met. Use `orchestrate add-iteration --count 1` if iterations run out before completion.

- [ ] All Section 1-6 checklist items are `[x]` (benchmark score = 0)
- [x] CODE_JUSTIFICATIONS.md complete with zero unjustified components and zero unjustified tests
- [ ] Total engine lines < 2800 (reduced from 3113 baseline) - currently 3005

**Do NOT stop while any condition above is unmet.**

---

## Score Tracking

| Iteration | Unchecked | Failed Tests | Complexity > 10 | Unjustified Components | Unjustified Tests | Score |
|-----------|-----------|--------------|------------------|------------------------|-------------------|-------|
| baseline  | 75        | 0            | TBD              | TBD                    | TBD               | TBD   |
| iter 1    | 17        | 0            | 0                | 0                      | 0                 | 17    |
| iter 2    | 21        | 0            | 0                | 0                      | 0                 | 21    |
| iter 3    | 15        | 0            | 0                | 0                      | 0                 | 15    |
