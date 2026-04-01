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

## Workstream B - Remove Hypothesis from Planning Workflow

Remove the HYPOTHESIS phase from the PLANNING workflow only. The FULL workflow retains HYPOTHESIS - it is valuable for implementation iterations. All hypothesis Python code stays since FULL still uses it.

### YAML Changes

- `workflow.yaml` - remove HYPOTHESIS from PLANNING workflow phases only (RESEARCH -> ~~HYPOTHESIS~~ -> PLAN -> RECORD -> NEXT)
- `phases.yaml` - remove PLANNING::HYPOTHESIS entry only (keep FULL::HYPOTHESIS)
- `agents.yaml` - remove PLANNING::HYPOTHESIS agent/gate section only (keep FULL::HYPOTHESIS)

## Workstream B2 - Remove Agent Number Attribute

The `number` field on agents in agents.yaml is redundant - it can be derived from list position. Remove it from the YAML schema, the Agent dataclass, and auto-derive from list index.

### Current Usage

- `Agent.number` field in model.py dataclass
- `agent.number` used in orchestrator.py for display: `### Agent {number}: {display_name}`
- Sequential numbering validation in `validate_model()`
- Every agent entry in agents.yaml has `number: N`

### Target

- Remove `number` field from Agent dataclass in model.py
- Auto-derive number from list position (1-indexed) in `_build_agents_and_gates()`
- Update `_build_agent_instructions()` in orchestrator.py to use enumerate
- Remove sequential numbering validation from `validate_model()` (no longer needed)
- Remove `number:` lines from all agent entries in agents.yaml
- Update tests

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

## Workstream D1 - Independent Workflow Flag

Replace the `dependency: true/false` field in workflow.yaml with a clearer `independent: true/false` flag that defines whether a workflow can be started directly via `--type`.

### Behavior

- Remove `dependency: true` field entirely from workflow.yaml and model.py
- Add `independent: false` only on workflows that cannot be started directly (e.g., planning)
- The field is implicit - if not present, the workflow is independent (can be invoked via `--type`)
- If `independent: false` is set and the orchestrator tries to run this workflow directly, it fails with an error
- Only workflows referenced via `depends_on` from another workflow can have `independent: false`

### Files to Modify

- `auto-build-claw/skills/auto-build-claw/resources/workflow.yaml` - remove `dependency: true` from planning, add `independent: false`
- `stellars_claude_code_plugins/engine/model.py` - remove `WorkflowType.dependency` field, add `independent: bool = True`, update `_build_workflow_types` to read `independent` (default True), update `validate_model`
- `stellars_claude_code_plugins/engine/orchestrator.py` - replace all `wf_def.dependency` checks with `not wf_def.independent`
- `tests/` - update tests referencing dependency field

## Workstream D2 - Run-Until-Complete Mode

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

## Workstream G - Parallel Gate Execution

The readback (at start) and gatekeeper (at end) each spawn a `claude -p` subprocess. When advancing between phases, `cmd_end` runs the gatekeeper and then the agent calls `cmd_start` which runs the next readback. These two gates could run in parallel.

### Approach: cmd_end accepts --next-understanding

Add `--next-understanding` optional argument to `cmd_end`. When provided:
1. Fire gatekeeper subprocess for current phase
2. Simultaneously fire readback subprocess for the next phase
3. Both run as `subprocess.Popen` in parallel, then `.wait()` for both
4. If gatekeeper passes AND readback passes: advance to next phase already in IN_PROGRESS
5. If gatekeeper fails: ignore readback result, stay in current phase
6. If gatekeeper passes but readback fails: advance to next phase in PENDING (normal retry)

This saves ~60s per phase transition (one gate's worth of latency eliminated).

### Files to Modify

- `stellars_claude_code_plugins/engine/orchestrator.py` - add --next-understanding to cmd_end argparse, run gatekeeper + readback in parallel via Popen
- `auto-build-claw/skills/auto-build-claw/resources/app.yaml` - add CLI arg help
- `tests/test_orchestrator.py` - test parallel gate execution

## Workstream H - Benchmark Agent

Add an explicit benchmark agent that is responsible for evaluating and updating BENCHMARK.md during the TEST phase. This agent runs as part of the TEST phase's agent panel.

### Behavior

When `--benchmark` is configured:
1. The TEST phase spawns a **benchmark agent** alongside test/lint execution
2. The benchmark agent reads BENCHMARK.md, evaluates every `[ ]` item against the codebase
3. Marks `[x]` for passing items, leaves `[ ]` for failing
4. Updates the Score Tracking table with the current iteration's results
5. Computes the composite score using the formula
6. The gatekeeper verifies the Score Tracking table was updated

### Implementation

- Add a benchmark agent definition to agents.yaml under FULL::TEST (or as a standalone agent)
- The agent's prompt instructs it to read BENCHMARK.md, evaluate items, edit the file, report score
- The TEST gatekeeper checks evidence for "Score Tracking updated" or similar confirmation
- `_verify_test_phase()` returns the benchmark instruction as part of its output so the orchestrating agent knows to spawn the benchmark agent

### Files to Modify

- `auto-build-claw/skills/auto-build-claw/resources/agents.yaml` - add benchmark agent to TEST phase
- `auto-build-claw/skills/auto-build-claw/resources/phases.yaml` - update TEST end criteria to require benchmark update
- `stellars_claude_code_plugins/engine/orchestrator.py` - update _verify_test_phase to include benchmark agent instruction

## Workstream F - TEST Phase Benchmark Enforcement

The TEST phase must ensure that when a benchmark is configured, it is always evaluated and the score tracking table in BENCHMARK.md is updated.

### Behavior

- When `--benchmark` is set, the TEST phase gatekeeper must verify that:
  1. The benchmark was evaluated (checklist items marked [x] or [ ])
  2. The Score Tracking table at the bottom of BENCHMARK.md was updated with the current iteration's results
  3. The composite score was computed using the formula
- The gatekeeper should FAIL if benchmark is configured but tracker was not updated
- `_verify_test_phase()` should remind the orchestrating agent to update the tracker
- The BENCHMARK.md score tracking table must always reflect the latest evaluation

### Files to Modify

- `stellars_claude_code_plugins/engine/orchestrator.py` - update `_verify_test_phase()` to include benchmark tracker update reminder in output
- `auto-build-claw/skills/auto-build-claw/resources/phases.yaml` - update FULL::TEST end template to require benchmark tracker update
- `auto-build-claw/skills/auto-build-claw/resources/agents.yaml` - update TEST gatekeeper to verify tracker was updated

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
3. **Workstream D1 third** (independent flag) - rename dependency to independent
4. **Workstream D2 fourth** (run-until-complete) - builds on existing benchmark infrastructure
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
