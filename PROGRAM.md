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

### Quality Targets

- No function exceeds 50 lines
- No function has cyclomatic complexity > 10
- No unreachable code detected
- No unused imports
- Total engine lines reduced from 3113 baseline
- All tests still passing after removals

## Execution Order

1. **Workstream B first** (hypothesis removal) - simplest, reduces code surface before other work
2. **Workstream A second** (FSM migration) - independent from hypothesis removal
3. **Workstream C last** (tree-sitter analysis) - runs on the already-cleaned codebase

## Success Criteria

- All `make test` passes (115+ tests)
- All `make lint` passes
- `orchestrate validate` passes with real auto-build-claw YAML resources
- `orchestrate new --type full --objective "test" --iterations 1 --dry-run` succeeds
- Benchmark score of 0 (all checklist items checked, no test failures, no complex functions)
