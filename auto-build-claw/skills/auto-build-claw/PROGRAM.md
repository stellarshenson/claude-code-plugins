# Auto Build Claw v3 - State Machine + Planning Workflow Program

## Objective

Refactor the orchestrator from imperative phase-stepping to a finite state machine (FSM) architecture, introduce a first-class `planning` workflow as a dependency chain (replacing hardcoded iteration 0 logic), add a `--dry-run` mode for configuration validation, and eliminate all remaining app-specific text from `orchestrate.py`.

## What needs to happen

### 1. Phase-declared transitions + FSM engine

Create `resources/fsm.py` as a lightweight state machine that drives phase lifecycle. Currently `orchestrate.py` uses imperative `_next_phase()` calls, `if phase == "HYPOTHESIS"` auto-action branches, and scattered `state["phase_status"]` mutations.

Phase transitions are **declared on each phase in phases.yaml** (not in a separate transitions file) because the workflow is deterministic - each phase knows exactly where it goes:

```yaml
FULL::RESEARCH:
  auto_actions:
    on_complete: []
  start: |
    ...

FULL::HYPOTHESIS:
  auto_actions:
    on_complete: [hypothesis_autowrite, hypothesis_gc]
  start: |
    ...

FULL::REVIEW:
  reject_to:
    phase: IMPLEMENT
    condition: "reviewer or test failure rejects work back to implementation"
  auto_actions:
    on_complete: []
  start: |
    ...
```

Forward transitions (complete, skip) are **implicit** - they follow the phase sequence in workflow.yaml. No need to declare them since the workflow is deterministic.

Backward transitions (reject) are **explicit** - declared via `reject_to` with a generative condition explaining when rejection happens. Only phases that can reject need this field.

The FSM in `resources/fsm.py`:
- **States**: `pending`, `readback`, `in_progress`, `gatekeeper`, `complete`, `skipped`, `rejected`
- **Events**: `start`, `end`, `reject`, `skip` (maps to CLI commands)
- **Lifecycle** is universal (same for every phase): `pending -> readback -> in_progress -> gatekeeper -> complete`
- **Phase-to-phase routing** comes from the `transitions` field on each phase in phases.yaml
- **Auto-actions** (hypothesis-gc, summary) come from `auto_actions.on_complete` on each phase
- Logs every transition to the audit trail
- Supports `--dry-run` mode (simulate without executing)

### 2. Planning as a dependency workflow

Currently iteration 0 is hardcoded: `cmd_new` checks `if total_iterations > 1 and itype == "full"` and forces `iteration = 0`. The PLAN phase has a special `start_planning` template selected via `is_planning = iteration == 0`. This must become a first-class workflow.

Define a `planning` workflow type in `workflow.yaml`:
```yaml
planning:
  description: "Planning iteration: research, hypothesise, break down work into implementation iterations"
  dependency: true   # cannot be invoked directly via --type, auto-chains before dependent workflows
  phases:
    - name: RESEARCH
    - name: HYPOTHESIS
    - name: PLAN_BREAKDOWN   # new phase, distinct from PLAN - breaks objective into N iterations
    - name: RECORD
    - name: NEXT
      skippable: true
```

Workflow dependency rules:
- `full` workflow declares `depends_on: planning` - the planning workflow auto-runs before the first implementation iteration
- `gc` and `hotfix` do NOT depend on planning (they're self-contained)
- The `planning` workflow has its own phases and agents in `phases.yaml` and `agents.yaml`
- `PLAN_BREAKDOWN` is a new phase (distinct from `PLAN`) that uses `EnterPlanMode` and produces a multi-iteration work breakdown
- The existing `PLAN` phase (in `full` workflow) becomes implementation planning only - scoped to the current iteration, informed by the iteration plan from `PLAN_BREAKDOWN`

This eliminates:
- All `if iteration == 0` checks in `orchestrate.py`
- The `start_planning` conditional template in `phases.yaml`
- The hardcoded planning detection in `cmd_new`
- The `iteration_0_purpose` / `iteration_0_banner` special messages in `app.yaml`

### 3. Dry-run mode

Add `--dry-run` flag to `orchestrate.py new` that simulates the entire workflow without executing any actions:

```bash
orchestrate.py new --type full --objective "..." --iterations 3 --dry-run
```

In dry-run mode:
- The FSM walks through all states and transitions for the selected workflow (including dependency workflows)
- Each phase prints: phase name, expected agents, gate types, auto-actions
- No state files are created, no agents are spawned, no gates are invoked
- Validates that all referenced phases exist in `phases.yaml`, all agents exist in `agents.yaml`, all template variables resolve
- Reports any configuration errors (missing phases, unresolvable templates, invalid transitions)
- Exits with code 0 if valid, code 1 if errors found

This serves as a configuration smoke test before committing to a multi-hour iteration cycle.

### 4. Add-iteration command

Add `add-iteration` command that extends a completed (or in-progress) iteration cycle with additional iterations:

```bash
orchestrate.py add-iteration --count 2 --objective "updated objective text"
```

This enables:
- Continuing work after all planned iterations are complete without `new --clean`
- Updating the objective mid-flight (e.g., scope discovered during work)
- Adding iterations without losing context, hypotheses, or failure logs

Behaviour:
- If all iterations are complete: resets to RESEARCH phase of the next iteration, increments total_iterations
- If iterations are in progress: adds to the remaining count
- `--objective` is optional - if provided, updates the objective in state; if omitted, keeps the current one
- The planning workflow does NOT re-run (it only runs before the first implementation iteration)
- State, hypotheses, context, and failure logs are all preserved

### 5. Zero app-specific text in orchestrate.py

The orchestrator must be a pure generic engine. Currently `orchestrate.py` still contains:
- Hardcoded `"Auto Build Claw v2"` in the docstring
- Hardcoded `".auto-build-claw"` as the artifacts directory name
- Any `if phase == "X"` branches that encode domain knowledge
- Print statements with literal text instead of `_msg()` lookups

Audit `orchestrate.py` for remaining hardcoded strings. Every user-facing string must come from `app.yaml`. Every phase-specific behaviour must come from YAML configuration (FSM transitions, auto-actions, guards).

### 6. Workflow-namespaced phases and agents via `::` notation

Phase and agent keys must be namespaced by workflow type using `::` separator. This allows each workflow to have dedicated prompts, agents, and exit criteria instead of sharing a single set across all workflow types.

Key format: `WORKFLOW::PHASE` (e.g., `FULL::RESEARCH`, `PLANNING::HYPOTHESIS`)

In `phases.yaml`:
- `FULL::RESEARCH` - research template for implementation iterations
- `PLANNING::RESEARCH` - research template for the planning iteration (different goal: problem decomposition not code investigation)
- `FULL::PLAN` - implementation planning (scope to this iteration)
- `PLANNING::PLAN` - work breakdown (scope across N iterations, replaces `start_planning`)
- `RECORD`, `NEXT` - shared phases with no prefix (fallback for any workflow)

In `agents.yaml`:
- `FULL::RESEARCH` - researcher, architect, product_manager (code-focused)
- `PLANNING::RESEARCH` - researcher, architect, product_manager (decomposition-focused prompts)
- `FULL::PLAN_REVIEW` - replaces the hardcoded `PLAN -> PLAN_REVIEW` remapping in Python
- `FULL::HYPOTHESIS`, `PLANNING::HYPOTHESIS` - same agents, different prompts

In `workflow.yaml`:
- Phase names stay bare (`RESEARCH`, `PLAN`) - the engine resolves `WORKFLOW::PHASE` at runtime
- Resolution: try `WORKFLOW::PHASE` first, fall back to bare `PHASE`

This eliminates:
- The `PLAN_REVIEW` agent key remapping (hardcoded in 3 places in orchestrate.py)
- The `start_planning` conditional template (becomes `PLANNING::PLAN` naturally)
- All `if phase == "PLAN" and event == "end"` branches

Resolution function in Python:
```python
def resolve_phase_key(workflow_type: str, phase_name: str, registry: dict) -> str:
    namespaced = f"{workflow_type.upper()}::{phase_name}"
    return namespaced if namespaced in registry else phase_name
```

## Files

| File | Action | Purpose |
|------|--------|---------|
| `resources/fsm.py` | CREATE | FSM engine - states, events, phase lifecycle, resolve_phase_key() |
| `resources/workflow.yaml` | EDIT | Add `planning` workflow with `dependency: true`, `depends_on` on `full` |
| `resources/phases.yaml` | EDIT | Rename keys to `WORKFLOW::PHASE`, add `transitions`/`auto_actions` per phase, add `PLANNING::*` templates |
| `resources/agents.yaml` | EDIT | Rename keys to `WORKFLOW::PHASE`, add `PLANNING::*` agents |
| `resources/app.yaml` | EDIT | Add dry-run messages, remove iteration_0 special messages |
| `resources/model.py` | EDIT | Add FSM dataclasses, `resolve_phase_key()`, handle `::` keys in builders |
| `orchestrate.py` | EDIT | Replace imperative phase-stepping with FSM, use `resolve_phase_key()`, add --dry-run, remove hardcoded text |
| `SKILL.md` | EDIT | Document --dry-run, planning workflow, `::` notation, FSM architecture |

## Benchmark

Read `BENCHMARK.md` and evaluate each `[ ]` item. For each item: verify the condition by reading the relevant code. Mark `[x]` if passing. Add new `[ ]` items if you discover uncovered requirements. Report count of remaining `[ ]` as the violation score.
