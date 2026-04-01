# Program: Engine Modernization and Simplification

## Objective

Modernize the orchestration engine by replacing the custom FSM with the standard `transitions` Python package, removing the hypothesis workflow stage, and using tree-sitter code analysis to eliminate dead and redundant code while maintaining full test coverage.

## Baseline Metrics

| Module | Lines | Classes | Functions |
|--------|-------|---------|-----------|
| engine/fsm.py | 258 | 5 | 2 |
| engine/model.py | 376 | 10 | 8 |
| engine/orchestrator.py | 2444 | 0 | 66 |
| **Total engine** | **3113** | **15** | **76** |
| tests/ (3 files) | 1038 | 29 | 115 tests |

## Workstream A - FSM Migration to `transitions` Package

Replace the custom FSM implementation in `stellars_claude_code_plugins/engine/fsm.py` with the `transitions` Python package.

### Current Implementation

The custom FSM has 5 classes (`State`, `Event`, `Transition`, `FSMConfig`, `FSM`) with 14 methods, manual transition lookup via `(from_state, event) -> list[Transition]` dict, and explicit guard/action registration. The `build_phase_lifecycle_fsm()` factory creates the standard phase lifecycle with 11 transitions across 7 states triggered by 9 events.

### Target

- Use `transitions.Machine` as the FSM engine
- Define states and transitions via Machine constructor
- Guards become `conditions` callbacks on transitions
- Actions become `after` callbacks on transitions
- Preserve the `simulate()` method for dry-run validation
- Preserve `resolve_phase_key()` (namespace resolution helper, not FSM-related)
- Keep the transition log for audit trail

### Files to Modify

- `stellars_claude_code_plugins/engine/fsm.py` - rewrite to use transitions.Machine
- `stellars_claude_code_plugins/engine/orchestrator.py` - update `_fire_fsm()`, `_PHASE_FSM`, `FSMState`, `FSMEvent` references
- `tests/test_fsm.py` - rewrite tests for transitions-based API
- `pyproject.toml` - add `transitions` to dependencies

### Phase Lifecycle to Preserve

```
pending -> readback -> in_progress -> gatekeeper -> complete
                                                         |
Branches:                                                v
  readback_fail: readback -> pending (retry)        advance -> pending
  gate_fail: gatekeeper -> in_progress (retry)
  reject: in_progress -> rejected -> advance -> pending
  skip: pending -> skipped -> advance -> pending
```

States: pending, readback, in_progress, gatekeeper, complete, skipped, rejected

Events: start, readback_pass, readback_fail, end, gate_pass, gate_fail, reject, skip, advance

## Workstream B - Remove Hypothesis Stage

Remove the HYPOTHESIS phase from all workflows, along with all supporting code.

### YAML Changes

- `workflow.yaml` - remove HYPOTHESIS from FULL workflow phases (RESEARCH -> ~~HYPOTHESIS~~ -> PLAN -> ...) and PLANNING workflow phases
- `phases.yaml` - remove FULL::HYPOTHESIS and PLANNING::HYPOTHESIS entries
- `agents.yaml` - remove FULL::HYPOTHESIS and PLANNING::HYPOTHESIS agent definitions (4 agents each: contrarian, optimist, pessimist, scientist) and their readback/gatekeeper gates

### Orchestrator Code to Remove (141 lines across 8 functions)

| Function | Lines | Purpose |
|----------|-------|---------|
| `_action_hypothesis_autowrite` | 4 | Auto-action trigger |
| `_action_hypothesis_gc` | 4 | Auto-action trigger |
| `_append_hypothesis` | 8 | Write hypothesis entry |
| `_auto_write_hypotheses` | 54 | Parse structured output |
| `_load_prior_hypotheses` | 2 | Load catalogue |
| `_hypothesis_catalogue_summary` | 12 | Format for context |
| `_run_hypothesis_gc` | 37 | Archive completed hypotheses |
| `cmd_hypotheses` | 20 | CLI display command |

### Additional Cleanup

- Remove `hypothesis_autowrite` and `hypothesis_gc` from `_AUTO_ACTION_REGISTRY`
- Remove `cmd_hypotheses` from CLI subcommand registration in `main()`
- Remove `prior_hyp` variable from `_build_context()`
- Remove `HYPOTHESES_FILE` global and all references
- Update `_clean_artifacts_dir()` to stop preserving `hypotheses*.yaml`
- Remove `_KNOWN_AUTO_ACTIONS` hypothesis entries from `validate_model()` in model.py
- Update tests to remove hypothesis-related assertions

## Workstream C - Code Analysis and Dead Code Removal

Use tree-sitter to analyze the engine codebase and remove unnecessary code.

### Analysis Targets

Run tree-sitter-python parsing on all engine modules:
- `stellars_claude_code_plugins/engine/fsm.py`
- `stellars_claude_code_plugins/engine/model.py`
- `stellars_claude_code_plugins/engine/orchestrator.py`

### Metrics to Collect

- **Cyclomatic complexity** per function (target: no function > 10)
- **Function length** in lines (target: no function > 50 lines)
- **Unreachable code** - dead branches, unused return paths
- **Unused imports** - imports not referenced in the module
- **Duplicate code** - near-identical blocks that could be consolidated
- **Unjustified components** - functions or classes that have no caller, serve no distinct purpose, or duplicate another component's responsibility

### Justification Audit

Every function and class must defend its existence. Use tree-sitter to enumerate all functions and classes across engine modules, then for each one verify:

1. **It has a caller** - another function calls it, or it's exported in `__init__.py`, or it's registered in a dispatch dict (CLI commands, auto-actions)
2. **It serves a distinct purpose** - it does something no other function does
3. **It earns its weight** - wrapper functions that just forward to another function without adding logic should be inlined. Utility functions used only once should be inlined at the call site

Components that fail any test are **unjustified** and must be removed or merged. Unjustified components carry 3x weight in the benchmark score because dead code compounds as technical debt.

### Quality Targets

- No function exceeds 50 lines
- No function has cyclomatic complexity > 10
- No unreachable code detected
- No unused imports
- Zero unjustified components
- Total engine lines reduced from 3113 baseline
- All tests still passing after removals

## Workstream D - Run-Until-Complete Mode

Add a new execution mode to the orchestrator that runs iterations indefinitely until the benchmark score reaches 0 (all conditions met).

### Behavior

When `--iterations 0` is passed to `orchestrate new`, the orchestrator enters run-until-complete mode:
- `total_iterations` is set to 0 (sentinel for unlimited)
- `_run_next_iteration()` checks the benchmark score instead of a fixed iteration count
- If benchmark score > 0: automatically start the next iteration
- If benchmark score = 0: stop and report completion
- The NEXT phase displays "benchmark-driven iteration N" instead of "N/total"
- Status display shows "until benchmark complete" instead of iteration count
- Safety cap: after 20 iterations without reaching score 0, warn and pause for user confirmation

### Implementation

The benchmark score is already tracked in `state["benchmark_scores"]` when `--benchmark` is provided. The change is in `_run_next_iteration()`:

```python
# Current: stops when remaining <= 0
remaining = total - current
if remaining <= 0:
    print("All iterations complete")
    return

# New: when total == 0, check last benchmark score instead
if total == 0:
    scores = state.get("benchmark_scores", [])
    last_score = scores[-1]["score"] if scores else None
    if last_score is not None and last_score == 0:
        print("Benchmark conditions met - all iterations complete")
        return
    # Safety cap
    if current >= 20:
        print("WARNING: 20 iterations without benchmark completion")
        return
```

### Files to Modify

- `stellars_claude_code_plugins/engine/orchestrator.py` - modify `_run_next_iteration()`, `cmd_new()`, `cmd_status()`, `_banner()`
- `auto-build-claw/skills/auto-build-claw/resources/app.yaml` - add display messages for benchmark-driven mode
- `tests/test_orchestrator.py` - add tests for run-until-complete mode

### Usage

```bash
orchestrate new --type full \
  --objective "Implement the program defined in PROGRAM.md (read PROGRAM.md)" \
  --iterations 0 \
  --benchmark "Read BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report remaining [ ] count as violation score."
```

`--iterations 0` means: keep iterating until the benchmark score reaches 0.

## Workstream E - Code Justifications Document

Create and maintain `CODE_JUSTIFICATIONS.md` in the project root. Every function, class, and test must have an entry defending its existence.

### Format

Three sections - one per engine module, one per test file. Each entry has: component name, type, justification (why it exists), and the failure point it addresses (what breaks if removed).

Tests additionally require a "why not trivial" column explaining why the test is not simply asserting an obvious truth.

### Process

1. Use tree-sitter to enumerate all functions/classes in engine modules
2. Use tree-sitter to enumerate all test functions in test files
3. For each component, write a one-line justification and identify the failure point
4. Remove components that cannot be justified - they are dead code
5. Remove tests that are trivial or redundant - they waste CI time and obscure real gaps
6. Components or tests missing from CODE_JUSTIFICATIONS.md are automatically unjustified and inflate the benchmark score at 3x weight

## Execution Order

1. **Workstream B first** (hypothesis removal) - simplest, reduces code surface before other work
2. **Workstream A second** (FSM migration) - independent from hypothesis removal
3. **Workstream D third** (run-until-complete) - builds on existing benchmark infrastructure
4. **Workstream E fourth** (justifications) - audit all remaining code and tests
5. **Workstream C last** (tree-sitter analysis) - final complexity and dead code sweep on cleaned codebase

## Completion Conditions

Iterations continue until ALL of the following are met:

1. **Benchmark score = 0** - every checklist item in BENCHMARK.md is `[x]`, zero test failures, zero complexity violations, zero unjustified components, zero unjustified tests
2. **`make test` passes** with 0 failures and test count >= 80
3. **`make lint` passes** clean
4. **`orchestrate validate` passes** with real auto-build-claw YAML resources
5. **`orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds**
6. **No custom FSM classes remain** - only `transitions.Machine` based implementation
7. **No hypothesis code remains** - zero references in engine, YAML, and tests
8. **Total engine lines < 2800** - meaningful reduction from 3113 baseline
9. **Run-until-complete mode works** - `--iterations 0` runs until benchmark score = 0
10. **CODE_JUSTIFICATIONS.md complete** - every function, class, and test has an entry with justification and failure point
