# Program: Gate Architecture Refactor and Action Definitions

## Objective

Refactor the gate and auto-action architecture so that YAML configuration fully describes which gates run at which lifecycle points, and auto-actions have explicit definitions in YAML rather than being hardcoded name-to-function mappings. Currently the orchestrator hardcodes that readback runs at start and gatekeeper runs at end - this knowledge should live in the YAML.

## Current State

### Gates

Gates are `claude -p` subprocess calls that validate phase transitions. Currently 4 gate types exist, all hardcoded in orchestrator.py:

| Gate | When | Where hardcoded | Purpose |
|------|------|-----------------|---------|
| readback | cmd_start (phase entry) | `_readback_validate()` called in cmd_start | Validates agent understanding before work begins |
| gatekeeper | cmd_end (phase exit) | `_gatekeeper_validate()` called in cmd_end | Validates phase completion quality |
| gatekeeper_skip | cmd_skip (skip request) | `_gatekeeper_evaluate_skip()` | Decides if optional phase skip is justified |
| gatekeeper_force_skip | cmd_skip --force | `_gatekeeper_evaluate_force_skip()` | Conservative gate for required phase force-skip |

In agents.yaml, gates are nested under each phase:
```yaml
FULL::RESEARCH:
  agents: [...]
  gates:
    readback:
      prompt: "..."
    gatekeeper:
      prompt: "..."
```

The orchestrator knows `readback` = start gate and `gatekeeper` = end gate. This is implicit.

### Auto-Actions

Auto-actions are Python functions triggered after phase completion. Currently 5 registered:

| Action | Definition | Type |
|--------|-----------|------|
| hypothesis_autowrite | _action_hypothesis_autowrite (in orchestrator.py) | Programmatic - parses output, writes YAML |
| hypothesis_gc | _action_hypothesis_gc (in orchestrator.py) | Programmatic - archives done hypotheses |
| plan_save | _action_plan_save (in orchestrator.py) | Programmatic - saves plan to plan.yaml |
| iteration_summary | _action_iteration_summary (in orchestrator.py) | Programmatic - writes iteration_N.md summary |
| iteration_advance | _action_iteration_advance (in orchestrator.py) | Programmatic - advances to next iteration |

All 5 are programmatic (Python code). None are generative (Claude instructions). Action names in phases.yaml map to hardcoded Python functions via _AUTO_ACTION_REGISTRY.

## Work Items

### Split gates into explicit start/end sections in YAML (high)
- Scope: agents.yaml, engine/model.py, engine/orchestrator.py
- Currently gates are `readback` and `gatekeeper` nested under one `gates:` key
- Split into `start_gates:` and `end_gates:` (or similar) so the YAML explicitly says which gate runs when
- Move `gatekeeper_skip` and `gatekeeper_force_skip` from `shared_gates` into a `skip_gates:` section
- Update model.py Gate dataclass and _build_agents_and_gates to load the new structure
- Update orchestrator.py _resolve_gate to use the new key structure
- Acceptance: YAML declares gate-to-lifecycle-point mapping, orchestrator reads it instead of hardcoding

### Add action definitions to YAML (medium)
- Scope: new `actions:` section in workflow.yaml (or separate actions.yaml), engine/model.py, engine/orchestrator.py
- Currently phases.yaml has `auto_actions: {on_complete: [action_name]}` with no definition
- Add an `actions:` section that defines each action with type and description:

```yaml
actions:
  # Programmatic actions - Python handler, documented here
  plan_save:
    type: programmatic
    description: "Save PLAN output to plan.yaml for dependency workflows"
  iteration_summary:
    type: programmatic
    description: "Write iteration_N.md executive summary from phase outputs"
  iteration_advance:
    type: programmatic
    description: "Advance to next iteration, reset phase state"

  # Generative actions - prompt executed via claude -p
  hypothesis_autowrite:
    type: generative
    description: "Extract structured hypotheses from phase output"
    prompt: |
      Read the hypothesis output below and extract structured entries.
      For each hypothesis write: ID, HYPOTHESIS, PREDICT, EVIDENCE, RISK, STARS.
      Write to {artifacts_dir}/hypotheses.yaml in YAML list format.
      OUTPUT: {phase_output}
  hypothesis_gc:
    type: generative
    description: "Archive DONE/REMOVED hypotheses"
    prompt: |
      Read {artifacts_dir}/hypotheses.yaml. Move entries with status
      DONE or REMOVED to {artifacts_dir}/hypotheses_archive.yaml.
      Keep only active hypotheses in the main file.
```

- Programmatic actions keep their Python handlers - the YAML just documents what they do
- Generative actions are executed by the orchestrator via `claude -p` using the YAML prompt template - no Python handler needed
- The orchestrator checks action type: if `programmatic`, call the Python handler; if `generative`, run `_claude_evaluate(prompt)`
- Acceptance: every action has a YAML definition, generative actions work from prompts without Python code

### Remove hypothesis auto-actions from _KNOWN_AUTO_ACTIONS (low)
- Scope: engine/model.py
- hypothesis_autowrite and hypothesis_gc are in _KNOWN_AUTO_ACTIONS with "retained for YAML compat" comment
- If they're still used in FULL::HYPOTHESIS phases.yaml, keep them. If not, remove
- Acceptance: no dead references in _KNOWN_AUTO_ACTIONS

### Remove hardcoded resolution - use YAML identifiers (high)
- Scope: engine/orchestrator.py
- The orchestrator hardcodes gate type names ("readback", "gatekeeper", "gatekeeper_skip", "gatekeeper_force_skip") in _resolve_gate calls and skip evaluation functions
- Instead: the orchestrator should discover gate names from the YAML lifecycle sections (on_start, on_end, on_skip) and resolve by lifecycle point
- Same for agent resolution: don't assume agent names, read them from the model
- Acceptance: grep for hardcoded "readback", "gatekeeper" in orchestrator logic returns 0 results (excluding log event names which are audit trail labels)

### Add overfit scoring to benchmark (medium)
- Scope: BENCHMARK.md
- Every hardcoded value in orchestrator.py that should come from YAML is a benchmark violation
- Score formula should penalize: hardcoded gate names, hardcoded agent names, hardcoded phase names
- Acceptance: benchmark explicitly tracks overfit count

### Update tests (high)
- Scope: tests/test_model.py, tests/test_orchestrator.py
- Tests must verify new YAML gate structure loads correctly
- Tests must verify action definitions are loaded
- Tests must verify orchestrator uses YAML gate mapping not hardcoded names
- Acceptance: all tests pass, new structure covered

### Force auto-progression in prompts (high)
- Scope: phases.yaml, SKILL.md
- Every phase start/end template must include explicit instruction to proceed immediately to the next phase
- No "shall I continue?" or "ready for next?" questions - just proceed
- The autonomous execution instruction in SKILL.md must be reinforced in every phase template
- Acceptance: grep phases.yaml for "proceed immediately" or equivalent in every phase end template

## Constraints

- Do NOT change gate behavior - readback still blocks at start, gatekeeper still blocks at end
- Do NOT remove any existing gates or auto-actions
- Maintain backward compatibility: old YAML format should still work (or migration should be documented)
- Keep `shared_gates` working for skip gates unless moved to a better location

## Exit Conditions

Iterations stop when ALL conditions are met:
1. YAML explicitly declares which gates run at start vs end vs skip
2. Auto-actions have definitions in YAML (type, description, prompt for generative)
3. Orchestrator reads gate mapping from YAML, not hardcoded
4. All tests pass with 0 failures
5. `make lint` passes clean
6. `orchestrate validate` passes
7. Benchmark score = 0 (all checklist items in BENCHMARK.md are [x])
8. No further optimisation possible - code is clean, no dead references, no hardcoded gate names remain
