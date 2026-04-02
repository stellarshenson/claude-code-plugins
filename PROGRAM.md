# Program: Agent Lifecycle Architecture - Phase-Level Agents

## Objective

Restructure the phase lifecycle in YAML from `gates: { on_start, on_end }` to three clear sections: `start` (entry gate), `execution` (agents), `end` (exit gate). This reverses journal entry #16's decision to put agents inside `on_end` and also flattens the `gates` wrapper which added indirection without value. The standard FSM lifecycle is start/execution/end - the YAML should mirror this directly.

No backward compatibility fallback. One structure. Commit fully.

## Why This Reverses Entry #16

Entry #16 moved agents into `gates.on_end` to co-locate them with the gatekeeper. The reasoning was lifecycle binding - agents and gatekeeper both relate to phase completion. This was wrong because:

1. Agent instructions are injected into the START template via `{agents_instructions}` - they describe what to do DURING the phase
2. The gatekeeper evaluates AFTER agents complete - it's the exit gate, not the execution context
3. In the standard FSM lifecycle (on_start / execution / on_end), agents are execution, not on_end
4. Co-locating execution agents with the exit gate made the YAML lie about when agents run

## Target Architecture

```yaml
FULL::RESEARCH:
  start:
    agents:
      - name: readback
        prompt: "..."                   # Entry agent: comprehension check
  execution:
    agents:
      - name: researcher
      - name: architect
      - name: product_manager           # Work agents: do the phase's work
  end:
    agents:
      - name: gatekeeper
        prompt: "..."                   # Exit agent: completion validation
```

Three lifecycle sections per phase, all using the same `agents` schema:
- `start` -> entry agents (readback validates understanding)
- `execution` -> work agents (instructions from `{agents_instructions}`)
- `end` -> exit agents (gatekeeper validates completion, predicates transition)

Harmonious schema: every lifecycle point has `agents` with `name` and `prompt`. Readback is an agent. Gatekeeper is an agent. The distinction is which lifecycle point they belong to, not their data structure.

## Baseline Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Agents under gates.on_end | 7 phases (19 agents total) | 0 |
| Agents at phase level | 0 | 7 phases (19 agents total) |
| `if gate_type == "agents": continue` dead code in model.py | 1 | 0 (removed) |
| Validation warning for on_end agents | none | warning emitted |
| Tests | 142 | >= 142 |

## Work Items

- **Restructure phases.yaml to start/execution/end** (high)
  - Scope: `stellars_claude_code_plugins/engine/resources/phases.yaml`
  - Replace `gates: { on_start: { readback }, on_end: { agents, gatekeeper } }` with:
    - `start: { readback: { prompt } }` - entry gate
    - `execution: { agents: [...] }` - work agents (only for 7 phases that have them)
    - `end: { gatekeeper: { prompt } }` - exit gate
  - Remove the `gates` wrapper entirely - `start`/`execution`/`end` are top-level under each phase
  - Phases with agents: FULL::RESEARCH (3), FULL::HYPOTHESIS (4), PLAN (3), TEST (1), REVIEW (4), PLANNING::RESEARCH (3), PLANNING::PLAN (1)
  - Phases without agents: IMPLEMENT, RECORD, NEXT, GC::PLAN - have `start` and `end` only, no `execution`
  - shared_gates: rename `on_skip` to just `skip` for consistency
  - GC::PLAN borrows agents from bare PLAN via `_resolve_agents` - verify this still works
  - Guardian YAML anchor `&guardian_checklist` / `*guardian_checklist` must survive
  - Acceptance: every phase uses start/execution/end, zero `gates:` wrappers, validate passes

- **Update model.py for unified agent schema** (high)
  - Scope: `stellars_claude_code_plugins/engine/model.py` lines 173-237
  - All three lifecycle sections now have the same `agents` schema
  - `start.agents` -> readback agent(s) -> stored as gates with mode standalone_session
  - `execution.agents` -> work agents -> stored in Model.agents dict
  - `end.agents` -> gatekeeper agent(s) -> stored as gates with mode standalone_session
  - The lifecycle map simplifies: no need for `on_start`/`on_end` -> `start`/`end` mapping
  - Remove: `gates` wrapper navigation, on_end agents override, `if gate_type == "agents": continue`
  - Start/end agents (readback, gatekeeper) are still stored as Gate objects (they're subprocess gates)
  - Execution agents are still stored as Agent objects (they're spawned by the orchestrating session)
  - The distinction is lifecycle point, not data structure of the YAML - but model storage differs because readback/gatekeeper run as `claude -p` (Gate) while execution agents run via Agent tool (Agent)
  - Add validation warning: if phase still has `gates` key, warn about old structure
  - Preserve: `_resolve_agents(phase)` -> `_build_agent_instructions(key)` -> `{agents_instructions}` chain
  - Acceptance: model loads from start/execution/end, unified schema in YAML, correct model types

- **Update validate_model in model.py** (medium)
  - Scope: `stellars_claude_code_plugins/engine/model.py` validate_model function
  - Add check: if any phase section has `gates.on_end.agents`, emit warning "agents should be at phase level, not under gates.on_end"
  - Error messages reference "phases.yaml phase-level agents" not "gates.on_end"
  - Acceptance: validate warns on stale on_end agents, error messages correct

- **Update _build_phases exclusion** (low)
  - Scope: `stellars_claude_code_plugins/engine/model.py` _build_phases function
  - Note: `_build_phases` filters by `Phase.__dataclass_fields__` intersection, so phase-level `agents` key is already silently ignored - no change needed
  - Verify this is the case and document it
  - Acceptance: _build_phases works without modification

- **Update all test fixtures** (high)
  - Scope: `tests/conftest.py`, `tests/test_model.py`, `tests/test_orchestrator.py`
  - Move agents from `gates.on_end.agents` to phase-level in ALL inline YAML:
    - conftest.py minimal_resources: ALPHA, BETA, GAMMA
    - test_model.py: test_missing_workflow_description, test_validate_fqn_workflow_format, test_validate_cli_name_uniqueness, test_validate_catches_missing_action_definition
    - test_orchestrator.py: TestGenerativeActionDispatch
  - Verification step: temporarily REMOVE the old on_end extraction code, run tests, confirm all pass from phase-level only. Then the dead code stays dead.
  - Add test: validate_model warns when agents found under on_end
  - Acceptance: all 142+ tests pass with phase-level agents, no silent fallback

## Invariants to Preserve

- `_resolve_agents(phase)` resolves phase key in `_MODEL.agents` dict - keys unchanged (still phase names like "FULL::RESEARCH")
- `_build_agent_instructions(key)` renders agent prompts into `{agents_instructions}` - input unchanged (still reads from `_MODEL.agents`)
- `PHASE_AGENTS` stores flat name lists per phase - source unchanged (`_MODEL.agents`)
- `_validate_end_inputs` checks `--agents` against `PHASE_AGENTS` - unchanged
- GC::PLAN borrows agents from bare PLAN via `_resolve_agents` resolution chain - must still work
- Guardian YAML anchor `&guardian_checklist` / `*guardian_checklist` - must survive the move

## Exit Conditions

Iterations stop when ANY of these is true:
1. All work items have acceptance criteria met
2. No improvement for 2 consecutive iterations (plateau)

Additionally ALL must hold:
- make test passes with 0 failures (>= 142)
- make lint passes clean
- orchestrate validate passes (with new warning for on_end agents)
- All 4 dry-runs pass (full, fast, gc, hotfix)
- GC::PLAN agent resolution still works
- Zero agents under gates.on_end in production YAML

## Constraints

- No backward compatibility fallback - one location only
- Do NOT change agent prompts, names, display_names, or checklist content
- Do NOT change gate prompts
- Do NOT change phase template content (start/end text)
- Do NOT change orchestrator agent injection or validation logic
- Preserve YAML anchor references (&guardian_checklist / *guardian_checklist)
